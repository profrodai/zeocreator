"""Publication-scoped performance observation and assessment contracts."""

from datetime import datetime

from pydantic import Field

from zeo_creator.contracts.common import CreatorModel, DurableArtifact
from zeo_creator.contracts.distribution import ProviderKind
from zeo_creator.contracts.evidence import ResearchWindow


class MetricsQuery(CreatorModel):
    query_id: str = Field(min_length=1)
    publication_id: str = Field(min_length=1)
    provider_kind: ProviderKind
    connection_ref: str = Field(min_length=1)
    destination_account_ref: str = Field(min_length=1)
    observation_window: ResearchWindow
    operation_refs: tuple[str, ...] = ()


class MetricObservation(DurableArtifact):
    observation_id: str = Field(min_length=1)
    provider_kind: ProviderKind
    connection_ref: str = Field(min_length=1)
    destination_account_ref: str = Field(min_length=1)
    observed_at: datetime
    artifact_ref: str = Field(min_length=1)
    publication_operation_ref: str = Field(min_length=1)
    metric_name: str = Field(min_length=1)
    metric_value: float


class DailyPerformanceAssessment(DurableArtifact):
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
