"""Deterministic, cadence-neutral content portfolio planning."""

from datetime import datetime

from zeo_creator.contracts.common import digest_is_current, stable_id
from zeo_creator.contracts.editorial import (
    ContentHistoryEntry,
    ContentPortfolioPlan,
    EditorialAssignment,
    PortfolioConstraints,
    PublicationObjective,
)
from zeo_creator.contracts.evidence import ResearchSynthesis, ResearchWindow
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError


def plan_portfolio(
    *,
    organization_id: str,
    profiles: tuple[PublicationProfile, ...],
    syntheses: tuple[ResearchSynthesis, ...],
    content_history: tuple[ContentHistoryEntry, ...],
    objectives: tuple[PublicationObjective, ...],
    constraints: PortfolioConstraints,
    planning_window: ResearchWindow,
    due_at: datetime,
    created_at: datetime,
    revision: int,
) -> ContentPortfolioPlan:
    profile_by_publication = {item.publication_id: item for item in profiles}
    synthesis_by_publication = {item.publication_id: item for item in syntheses}
    objective_by_publication = {item.publication_id: item for item in objectives}
    if len(profile_by_publication) != len(profiles):
        raise CreatorDomainError("ZEO_CREATOR_DUPLICATE_PUBLICATION", "publication profiles repeat")
    if set(profile_by_publication) != set(synthesis_by_publication):
        raise CreatorDomainError(
            "ZEO_CREATOR_SCOPE_MISMATCH", "profile and synthesis scopes differ"
        )
    if set(profile_by_publication) != set(objective_by_publication):
        raise CreatorDomainError(
            "ZEO_CREATOR_SCOPE_MISMATCH", "profile and objective scopes differ"
        )

    requested_kinds = tuple(
        requirement.content_kind
        for requirement in constraints.requirements
        for _ in range(requirement.quantity)
    )
    assignments: list[EditorialAssignment] = []
    for publication_id in sorted(profile_by_publication):
        profile = profile_by_publication[publication_id]
        synthesis = synthesis_by_publication[publication_id]
        objective = objective_by_publication[publication_id]
        if (
            profile.organization_id != organization_id
            or synthesis.organization_id != organization_id
        ):
            raise CreatorDomainError("ZEO_CREATOR_SCOPE_MISMATCH", "organization scope mismatch")
        if not digest_is_current(profile) or not digest_is_current(synthesis):
            raise CreatorDomainError(
                "ZEO_CREATOR_STALE_INPUT", "profile or synthesis digest is stale"
            )

        recent_topics = {
            item.topic.casefold()
            for item in content_history
            if item.publication_id == publication_id
        }
        candidates = [
            (topic, claim)
            for topic, claim in zip(
                synthesis.opportunities, synthesis.candidate_claims, strict=False
            )
            if not constraints.avoid_recent_topics or topic.casefold() not in recent_topics
        ]
        unique_candidates: list[tuple[str, object]] = []
        seen_topics: set[str] = set()
        for candidate in candidates:
            normalized = candidate[0].casefold()
            if normalized not in seen_topics:
                seen_topics.add(normalized)
                unique_candidates.append(candidate)
        if len(unique_candidates) < len(requested_kinds):
            raise CreatorDomainError(
                "ZEO_CREATOR_INSUFFICIENT_NOVEL_TOPICS",
                f"{publication_id} lacks enough novel, evidence-backed topics",
            )

        selected = unique_candidates[: len(requested_kinds)]
        selected_topics = tuple(topic for topic, _claim in selected)
        for index, content_kind in enumerate(requested_kinds):
            topic, untyped_claim = selected[index]
            claim = next(item for item in synthesis.candidate_claims if item == untyped_claim)
            other_topics = tuple(item for item in selected_topics if item != topic)
            assignments.append(
                EditorialAssignment(
                    assignment_id=stable_id(
                        "assignment",
                        planning_window.starts_at.isoformat(),
                        publication_id,
                        content_kind,
                        str(index),
                    ),
                    created_at=created_at,
                    organization_id=organization_id,
                    publication_id=publication_id,
                    input_refs=(synthesis.synthesis_id, profile.reference, claim.claim_id),
                    revision=revision,
                    content_kind=content_kind,
                    objective=objective.objective,
                    audience=profile.audience_definition,
                    desired_audience_action=objective.desired_audience_action,
                    topic=topic,
                    thesis=claim.text,
                    hook=f"{profile.display_name}: {topic}",
                    evidence_refs=claim.evidence_refs,
                    novelty_rationale="Not present in the supplied publication history.",
                    relationship_to_other_assignments=(
                        f"Complements {', '.join(other_topics)} without duplication."
                    ),
                    target_channels=profile.default_channels,
                    brand_profile_ref=profile.reference,
                    due_at=due_at,
                )
            )

    portfolio_scope = "+".join(sorted(profile_by_publication))
    return ContentPortfolioPlan(
        plan_id=stable_id(
            "plan",
            organization_id,
            planning_window.starts_at.isoformat(),
            planning_window.ends_at.isoformat(),
            portfolio_scope,
            str(revision),
        ),
        created_at=created_at,
        organization_id=organization_id,
        publication_id=f"portfolio:{portfolio_scope}",
        input_refs=tuple(
            [item.synthesis_id for item in syntheses]
            + [item.reference for item in profiles]
            + [item.history_id for item in content_history]
        ),
        revision=revision,
        planning_window=planning_window,
        assignments=tuple(assignments),
    )
