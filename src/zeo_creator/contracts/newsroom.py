"""Provider-neutral contracts for continuous editorial operations."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact, UtcDatetime
from zeo_creator.contracts.editorial import ContentKind
from zeo_creator.contracts.evidence import EvidenceClaim, ResearchWindow


class ObservationCompleteness(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class StoryStatus(StrEnum):
    DETECTED = "DETECTED"
    WATCHING = "WATCHING"
    DEVELOPING = "DEVELOPING"
    VERIFIED = "VERIFIED"
    SELECTED = "SELECTED"
    PUBLISHED = "PUBLISHED"
    CORRECTED = "CORRECTED"
    SUPERSEDED = "SUPERSEDED"
    DISMISSED = "DISMISSED"


class SignalType(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    CORRECTION = "CORRECTION"
    CONTRADICTION = "CONTRADICTION"
    COMMUNITY_REACTION = "COMMUNITY_REACTION"
    OPPORTUNITY = "OPPORTUNITY"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SlotUrgency(StrEnum):
    LIVE = "LIVE"
    DAILY = "DAILY"
    PERIODIC = "PERIODIC"
    EVERGREEN = "EVERGREEN"


class GenerationTrace(CreatorModel):
    strategy_ref: str = Field(min_length=1)
    strategy_version: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    input_digests: tuple[str, ...] = Field(min_length=1)
    model_ref: str | None = None
    generation_attempt: int = Field(default=1, ge=1)
    evaluator_findings: tuple[str, ...] = ()


class SourceObservation(DurableArtifact):
    observation_id: str = Field(min_length=1)
    source_identity: str = Field(min_length=1)
    source_kind: str = Field(min_length=1)
    source_published_at: UtcDatetime | None = None
    retrieved_at: UtcDatetime
    canonical_url: str | None = None
    provider_ref: str | None = None
    author_or_origin: str = Field(min_length=1)
    publication_scope: str = Field(min_length=1)
    raw_artifact_ref: str = Field(min_length=1)
    raw_artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    extracted_content_ref: str = Field(min_length=1)
    extracted_content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    extracted_text: str = ""
    completeness: ObservationCompleteness
    availability: str = Field(min_length=1)
    language: str = Field(min_length=2)
    geography: tuple[str, ...] = ()
    parent_observation_ref: str | None = None
    thread_ref: str | None = None
    extraction_method: str = Field(min_length=1)
    extraction_version: str = Field(min_length=1)
    access_policy_ref: str = Field(min_length=1)
    retention_policy_ref: str = Field(min_length=1)

    @model_validator(mode="after")
    def scope_matches_publication(self) -> SourceObservation:
        if self.publication_scope != self.publication_id:
            raise ValueError("observation publication_scope must match publication_id")
        if self.completeness is ObservationCompleteness.COMPLETE and not self.extracted_text:
            raise ValueError("complete observations require extracted text")
        return self


class EditorialSignal(DurableArtifact):
    signal_id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    entities: tuple[str, ...] = ()
    candidate_claims: tuple[EvidenceClaim, ...] = ()
    signal_type: SignalType
    novelty: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)
    geography: tuple[str, ...] = ()
    urgency: SlotUrgency
    confidence: float = Field(ge=0, le=1)
    source_refs: tuple[str, ...] = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    generation: GenerationTrace

    @model_validator(mode="after")
    def claims_use_signal_sources(self) -> EditorialSignal:
        allowed = set(self.source_refs)
        if any(
            ref not in allowed for claim in self.candidate_claims for ref in claim.evidence_refs
        ):
            raise ValueError("signal claims must reference the signal source set")
        return self


class MaterialDevelopment(CreatorModel):
    development_id: str = Field(min_length=1)
    occurred_at: UtcDatetime
    summary: str = Field(min_length=1)
    source_refs: tuple[str, ...] = Field(min_length=1)


class StoryRevision(DurableArtifact):
    story_id: str = Field(min_length=1)
    story_revision_id: str = Field(min_length=1)
    previous_revision_ref: str | None = None
    status: StoryStatus
    title: str = Field(min_length=1)
    verified_claims: tuple[EvidenceClaim, ...] = ()
    disputed_claims: tuple[EvidenceClaim, ...] = ()
    material_developments: tuple[MaterialDevelopment, ...] = ()
    primary_source_refs: tuple[str, ...] = ()
    secondary_source_refs: tuple[str, ...] = ()
    community_reaction_refs: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    geography: tuple[str, ...] = ()
    affected_communities: tuple[str, ...] = ()
    freshness_at: UtcDatetime
    editorial_risk: RiskLevel
    signal_refs: tuple[str, ...] = Field(min_length=1)
    generation: GenerationTrace

    @model_validator(mode="after")
    def revision_chain_is_consistent(self) -> StoryRevision:
        if self.revision > 1 and not self.previous_revision_ref:
            raise ValueError("story revisions after revision one require previous_revision_ref")
        if self.revision == 1 and self.previous_revision_ref:
            raise ValueError("first story revision cannot reference a previous revision")
        verified = {claim.claim_id for claim in self.verified_claims}
        disputed = {claim.claim_id for claim in self.disputed_claims}
        if verified & disputed:
            raise ValueError("a claim cannot be both verified and disputed")
        return self


class StoryTimelineEntry(CreatorModel):
    occurred_at: UtcDatetime
    summary: str = Field(min_length=1)
    source_refs: tuple[str, ...] = Field(min_length=1)


class StoryDossier(DurableArtifact):
    dossier_id: str = Field(min_length=1)
    story_id: str = Field(min_length=1)
    story_revision_ref: str = Field(min_length=1)
    verified_claims: tuple[EvidenceClaim, ...] = ()
    evidence_lineage: tuple[str, ...] = Field(min_length=1)
    contradictions: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    timeline: tuple[StoryTimelineEntry, ...] = ()
    quotation_refs: tuple[str, ...] = ()
    audience_significance: str = Field(min_length=1)
    possible_angles: tuple[str, ...] = ()
    recommended_framing: str = Field(min_length=1)
    rejected_framings: tuple[str, ...] = ()
    risk_level: RiskLevel
    risk_notes: tuple[str, ...] = ()
    visual_opportunities: tuple[str, ...] = ()
    prior_coverage_refs: tuple[str, ...] = ()
    community_conversation_refs: tuple[str, ...] = ()
    suggested_follow_up: tuple[str, ...] = ()
    frozen_at: UtcDatetime
    generation: GenerationTrace

    @model_validator(mode="after")
    def claims_use_dossier_lineage(self) -> StoryDossier:
        allowed = set(self.evidence_lineage)
        if any(ref not in allowed for claim in self.verified_claims for ref in claim.evidence_refs):
            raise ValueError("dossier claims must resolve to evidence_lineage")
        return self


class PublicationSlot(CreatorModel):
    slot_id: str = Field(min_length=1)
    publication_id: str = Field(min_length=1)
    desk_id: str = Field(min_length=1)
    content_kind: ContentKind
    purpose: str = Field(min_length=1)
    due_at: UtcDatetime
    urgency: SlotUrgency
    freshness_max_age_seconds: int | None = Field(default=None, ge=1)
    target_channels: tuple[str, ...] = Field(min_length=1)
    story_dossier_refs: tuple[str, ...] = ()
    desired_audience_action: str = Field(min_length=1)
    risk_policy_ref: str = Field(min_length=1)
    approval_policy_ref: str = Field(min_length=1)


class AgendaSelection(CreatorModel):
    dossier_ref: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class EditorialAgenda(DurableArtifact):
    agenda_id: str = Field(min_length=1)
    desk_id: str = Field(min_length=1)
    coverage_window: ResearchWindow
    lead_stories: tuple[AgendaSelection, ...] = ()
    secondary_stories: tuple[AgendaSelection, ...] = ()
    watch_list: tuple[AgendaSelection, ...] = ()
    commentary_opportunities: tuple[str, ...] = ()
    required_follow_ups: tuple[str, ...] = ()
    publication_slots: tuple[PublicationSlot, ...] = ()
    deferred_stories: tuple[AgendaSelection, ...] = ()
    rejected_stories: tuple[AgendaSelection, ...] = ()
    coverage_gaps: tuple[str, ...] = ()
    generation: GenerationTrace

    @model_validator(mode="after")
    def slots_belong_to_agenda(self) -> EditorialAgenda:
        if any(slot.publication_id != self.publication_id for slot in self.publication_slots):
            raise ValueError("agenda publication slots must match agenda publication")
        return self


class EditionItem(CreatorModel):
    slot_ref: str = Field(min_length=1)
    dossier_refs: tuple[str, ...] = ()
    prominence: int = Field(ge=1)
    required_content_kinds: tuple[ContentKind, ...] = Field(min_length=1)


class EditionPlan(DurableArtifact):
    edition_id: str = Field(min_length=1)
    agenda_ref: str = Field(min_length=1)
    edition_kind: str = Field(min_length=1)
    publication_window: ResearchWindow
    lead_items: tuple[EditionItem, ...] = ()
    supporting_items: tuple[EditionItem, ...] = ()
    shared_relationship_ref: str | None = None
    update_policy_ref: str = Field(min_length=1)
    human_editor_requirements: tuple[str, ...] = ()
    correction_refs: tuple[str, ...] = ()
    generation: GenerationTrace

    @model_validator(mode="after")
    def prominence_is_unique(self) -> EditionPlan:
        values = [item.prominence for item in (*self.lead_items, *self.supporting_items)]
        if len(values) != len(set(values)):
            raise ValueError("edition prominence values must be unique")
        return self
