"""Publication-scoped performance observation and assessment contracts."""

from enum import StrEnum

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact, UtcDatetime
from zeo_creator.contracts.distribution import ProviderKind
from zeo_creator.contracts.evidence import ResearchWindow


class MetricsQuery(CreatorModel):
    query_id: str = Field(min_length=1)
    publication_id: str = Field(min_length=1)
    provider_kind: ProviderKind
    connection_ref: str = Field(min_length=1)
    destination_account_ref: str = Field(min_length=1)
    observation_window: ResearchWindow
    operation_refs: tuple[str, ...] = Field(min_length=1)


class MetricAggregation(StrEnum):
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    RATE = "rate"
    UNIQUE = "unique"


class MetricObservation(DurableArtifact):
    observation_id: str = Field(min_length=1)
    provider_kind: ProviderKind
    connection_ref: str = Field(min_length=1)
    destination_account_ref: str = Field(min_length=1)
    observed_at: UtcDatetime
    artifact_ref: str = Field(min_length=1)
    publication_operation_ref: str = Field(min_length=1)
    metric_name: str = Field(min_length=1)
    metric_value: float
    unit: str = Field(min_length=1)
    aggregation: MetricAggregation
    denominator: str | None = None
    attribution_window: ResearchWindow
    objective_mapping: str = Field(min_length=1)
    baseline: float | None = None
    target: float | None = None
    normalized_rate: float | None = None
    provider_definition: str = Field(min_length=1)
    provider_definition_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def rate_has_denominator(self) -> MetricObservation:
        if self.aggregation == MetricAggregation.RATE and not self.denominator:
            raise ValueError("rate metrics require a denominator")
        return self


class PerformanceAssessment(DurableArtifact):
    assessment_id: str = Field(min_length=1)
    observation_window: ResearchWindow
    metrics: tuple[MetricObservation, ...]
    provider_account_provenance: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    publication_operation_refs: tuple[str, ...]
    performance_relative_to_objective: str = Field(min_length=1)
    confidence: str = Field(min_length=1)
    data_gaps: tuple[str, ...] = ()
    reusable_learnings: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] = ()
    proposed_follow_up_work: tuple[str, ...] = ()
