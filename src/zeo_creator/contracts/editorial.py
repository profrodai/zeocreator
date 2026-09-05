"""Daily portfolio and assignment contracts."""

from enum import StrEnum

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact, UtcDatetime


class DeliverableKind(StrEnum):
    ANIMATED_EPISODE = "animated_episode"
    HUD = "hud"
    COMIC_SLIDES = "comic_slides"


REQUIRED_DAILY_KINDS = tuple(DeliverableKind)


class ContentHistoryEntry(DurableArtifact):
    history_id: str = Field(min_length=1)
    deliverable_kind: DeliverableKind
    topic: str = Field(min_length=1)
    published_at: UtcDatetime
    artifact_ref: str = Field(min_length=1)


class PublicationObjective(CreatorModel):
    publication_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    desired_audience_action: str = Field(min_length=1)


class PortfolioConstraints(CreatorModel):
    required_kinds: tuple[DeliverableKind, ...] = REQUIRED_DAILY_KINDS
    assignments_per_publication: int = Field(default=3, ge=1)
    avoid_recent_topics: bool = True

    @model_validator(mode="after")
    def kinds_match_count(self) -> PortfolioConstraints:
        if len(set(self.required_kinds)) != len(self.required_kinds):
            raise ValueError("required deliverable kinds must be unique")
        if len(self.required_kinds) != self.assignments_per_publication:
            raise ValueError("assignment count must match required deliverable kinds")
        return self


class EditorialAssignment(DurableArtifact):
    assignment_id: str = Field(min_length=1)
    deliverable_kind: DeliverableKind
    objective: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    desired_audience_action: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    thesis: str = Field(min_length=1)
    hook: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    novelty_rationale: str = Field(min_length=1)
    relationship_to_other_daily_assignments: str = Field(min_length=1)
    target_channels: tuple[str, ...] = Field(min_length=1)
    brand_profile_ref: str = Field(min_length=1)
    due_at: UtcDatetime


class DailyEditorialPlan(DurableArtifact):
    plan_id: str = Field(min_length=1)
    plan_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    assignments: tuple[EditorialAssignment, ...]

    @model_validator(mode="after")
    def unique_assignment_identity(self) -> DailyEditorialPlan:
        ids = [item.assignment_id for item in self.assignments]
        if len(ids) != len(set(ids)):
            raise ValueError("assignment identifiers must be unique")
        keys = [(item.publication_id, item.deliverable_kind) for item in self.assignments]
        if len(keys) != len(set(keys)):
            raise ValueError("each publication may receive each format only once per plan")
        return self
