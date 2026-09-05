"""Cadence-neutral content portfolio and assignment contracts."""

from typing import Annotated

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact, UtcDatetime
from zeo_creator.contracts.evidence import ResearchWindow

ContentKind = Annotated[
    str,
    Field(pattern=r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$", min_length=1),
]


class ContentHistoryEntry(DurableArtifact):
    history_id: str = Field(min_length=1)
    content_kind: ContentKind
    topic: str = Field(min_length=1)
    published_at: UtcDatetime
    artifact_ref: str = Field(min_length=1)


class PublicationObjective(CreatorModel):
    publication_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    desired_audience_action: str = Field(min_length=1)


class ContentRequirement(CreatorModel):
    content_kind: ContentKind
    quantity: int = Field(ge=1)


class PortfolioConstraints(CreatorModel):
    requirements: tuple[ContentRequirement, ...] = Field(min_length=1)
    avoid_recent_topics: bool = True

    @model_validator(mode="after")
    def unique_kinds(self) -> PortfolioConstraints:
        kinds = [item.content_kind for item in self.requirements]
        if len(kinds) != len(set(kinds)):
            raise ValueError("content requirements must use unique kinds")
        return self


class EditorialAssignment(DurableArtifact):
    assignment_id: str = Field(min_length=1)
    content_kind: ContentKind
    objective: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    desired_audience_action: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    thesis: str = Field(min_length=1)
    hook: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    novelty_rationale: str = Field(min_length=1)
    relationship_to_other_assignments: str = Field(min_length=1)
    target_channels: tuple[str, ...] = Field(min_length=1)
    brand_profile_ref: str = Field(min_length=1)
    due_at: UtcDatetime


class ContentPortfolioPlan(DurableArtifact):
    plan_id: str = Field(min_length=1)
    planning_window: ResearchWindow
    assignments: tuple[EditorialAssignment, ...]

    @model_validator(mode="after")
    def unique_assignment_identity(self) -> ContentPortfolioPlan:
        ids = [item.assignment_id for item in self.assignments]
        if len(ids) != len(set(ids)):
            raise ValueError("assignment identifiers must be unique")
        return self
