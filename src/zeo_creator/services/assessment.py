"""Deterministic, publication-isolated performance assessment."""

from datetime import datetime

from zeo_creator.contracts.common import digest_is_current, stable_id
from zeo_creator.contracts.performance import (
    DailyPerformanceAssessment,
    MetricObservation,
    MetricsQuery,
)
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError
from zeo_creator.ports.metrics import MetricsSourcePort


def assess_publication_performance(
    *,
    publication: PublicationProfile,
    queries: tuple[MetricsQuery, ...],
    objective: str,
    created_at: datetime,
    revision: int,
    source: MetricsSourcePort,
) -> DailyPerformanceAssessment:
    observations: list[MetricObservation] = []
    for query in queries:
        if query.publication_id != publication.publication_id:
            raise CreatorDomainError(
                "ZEO_CREATOR_PUBLICATION_LEAKAGE", "metrics query crosses property"
            )
        for item in source.retrieve(query):
            if not digest_is_current(item):
                raise CreatorDomainError(
                    "ZEO_CREATOR_STALE_INPUT", "metric observation digest is stale"
                )
            if (
                item.organization_id != publication.organization_id
                or item.publication_id != publication.publication_id
                or item.connection_ref != query.connection_ref
                or item.provider_kind != query.provider_kind
                or item.destination_account_ref != query.destination_account_ref
            ):
                raise CreatorDomainError(
                    "ZEO_CREATOR_PROVENANCE_MISMATCH",
                    "metric observation does not match query scope",
                )
            observations.append(item)

    ordered = tuple(sorted(observations, key=lambda item: item.observation_id))
    if not ordered:
        summary = f"No observations are available for objective: {objective}."
        confidence = "low"
        gaps: tuple[str, ...] = ("No metric observations returned",)
        learnings: tuple[str, ...] = ()
        hypotheses: tuple[str, ...] = ("Hypothesis: provider reporting may not yet be available.",)
    else:
        metric_summary = ", ".join(f"{item.metric_name}={item.metric_value:g}" for item in ordered)
        summary = f"Observed {metric_summary} relative to objective: {objective}."
        confidence = "high" if len(ordered) >= 2 else "medium"
        gaps = () if len(ordered) >= 2 else ("Only one metric observation is available",)
        strongest = max(ordered, key=lambda item: item.metric_value)
        learnings = (f"Strongest observed signal: {strongest.metric_name}.",)
        hypotheses = (
            f"Hypothesis: the {strongest.metric_name} signal may reflect audience-format fit; causal evidence is not available.",
        )

    operation_refs = tuple(sorted({item.publication_operation_ref for item in ordered}))
    artifact_refs = tuple(sorted({item.artifact_ref for item in ordered}))
    provenance = tuple(
        sorted(
            {
                f"{item.provider_kind.value}:{item.connection_ref}:{item.destination_account_ref}"
                for item in ordered
            }
        )
    )
    window = queries[0].observation_window
    return DailyPerformanceAssessment(
        assessment_id=stable_id(
            "assessment",
            publication.publication_id,
            window.starts_at.isoformat(),
            window.ends_at.isoformat(),
            str(revision),
        ),
        created_at=created_at,
        organization_id=publication.organization_id,
        publication_id=publication.publication_id,
        input_refs=(publication.reference, *(query.query_id for query in queries), *operation_refs),
        revision=revision,
        observation_window=window,
        metrics=ordered,
        provider_account_provenance=provenance,
        artifact_refs=artifact_refs,
        publication_operation_refs=operation_refs,
        performance_relative_to_objective=summary,
        confidence=confidence,
        data_gaps=gaps,
        reusable_learnings=learnings,
        hypotheses=hypotheses,
        proposed_follow_up_work=(
            f"Runtime may consider testing another {publication.display_name} format.",
        ),
    )
