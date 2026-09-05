"""Performance observations are scoped and comparable by semantics, not magnitude."""

from datetime import timedelta

import pytest

from tests.fixtures.reference import NOW, PERFORMANCE_WINDOW, build_reference_snapshot
from zeo_creator.contracts.performance import MetricObservation, MetricsQuery
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.assessment import assess_publication_performance


class MetricsSource:
    def __init__(self, rows: tuple[MetricObservation, ...]) -> None:
        self.rows = rows

    def retrieve(self, query: MetricsQuery) -> tuple[MetricObservation, ...]:
        del query
        return self.rows


def _query(rows: tuple[MetricObservation, ...]) -> MetricsQuery:
    first = rows[0]
    return MetricsQuery(
        query_id="metrics_integrity",
        publication_id=first.publication_id,
        provider_kind=first.provider_kind,
        connection_ref=first.connection_ref,
        destination_account_ref=first.destination_account_ref,
        observation_window=PERFORMANCE_WINDOW,
        operation_refs=tuple(sorted({row.publication_operation_ref for row in rows})),
    )


def _rebuild(row: MetricObservation, **changes: object) -> MetricObservation:
    data = row.model_dump(mode="python", exclude={"content_digest"})
    data.update(changes)
    return MetricObservation.model_validate(data)


def test_raw_unlike_metrics_are_not_ranked_by_numeric_magnitude() -> None:
    snapshot = build_reference_snapshot()
    rows = tuple(_rebuild(row, normalized_rate=None) for row in snapshot.assessments[0].metrics)
    assessment = assess_publication_performance(
        publication=snapshot.profiles[0],
        queries=(_query(rows),),
        objective="Teach creator operations",
        created_at=NOW,
        revision=1,
        source=MetricsSource(rows),
    )

    assert assessment.reusable_learnings == ()
    assert any("No normalized metric rates" in gap for gap in assessment.data_gaps)


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        (
            {"observed_at": PERFORMANCE_WINDOW.ends_at + timedelta(seconds=1)},
            "ZEO_CREATOR_WINDOW_MISMATCH",
        ),
        (
            {"publication_operation_ref": "operation_not_requested"},
            "ZEO_CREATOR_PROVENANCE_MISMATCH",
        ),
    ],
)
def test_observation_must_match_window_and_operation_scope(
    changes: dict[str, object], code: str
) -> None:
    snapshot = build_reference_snapshot()
    row = _rebuild(snapshot.assessments[0].metrics[0], **changes)

    with pytest.raises(CreatorDomainError) as caught:
        assess_publication_performance(
            publication=snapshot.profiles[0],
            queries=(_query(snapshot.assessments[0].metrics),),
            objective="Teach creator operations",
            created_at=NOW,
            revision=1,
            source=MetricsSource((row,)),
        )
    assert caught.value.code == code


def test_stale_publication_profile_is_rejected() -> None:
    snapshot = build_reference_snapshot()
    profile = snapshot.profiles[0].model_copy(update={"display_name": "Changed"})
    rows = snapshot.assessments[0].metrics

    with pytest.raises(CreatorDomainError) as caught:
        assess_publication_performance(
            publication=profile,
            queries=(_query(rows),),
            objective="Teach creator operations",
            created_at=NOW,
            revision=1,
            source=MetricsSource(rows),
        )
    assert caught.value.code == "ZEO_CREATOR_STALE_INPUT"
