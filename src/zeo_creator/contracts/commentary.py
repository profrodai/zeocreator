"""Provider-neutral social conversation and commentary contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact, UtcDatetime
from zeo_creator.contracts.evidence import EvidenceClaim
from zeo_creator.contracts.newsroom import GenerationTrace, RiskLevel
from zeo_creator.contracts.production import ContentDocument


class EngagementDisposition(StrEnum):
    IGNORE = "IGNORE"
    MONITOR = "MONITOR"
    LIKE = "LIKE"
    REPOST = "REPOST"
    QUOTE = "QUOTE"
    REPLY = "REPLY"
    ORIGINAL_POST = "ORIGINAL_POST"
    ESCALATE = "ESCALATE"


class ConversationObservation(DurableArtifact):
    conversation_id: str = Field(min_length=1)
    provider_kind: str = Field(min_length=1)
    original_post_ref: str = Field(min_length=1)
    thread_ref: str | None = None
    author_ref: str = Field(min_length=1)
    author_context: str = Field(min_length=1)
    community_context: str = Field(min_length=1)
    content: ContentDocument
    reply_refs: tuple[str, ...] = ()
    engagement_snapshot: dict[str, int] = Field(default_factory=dict)
    related_story_refs: tuple[str, ...] = ()
    retrieved_at: UtcDatetime
    retrieval_cutoff: UtcDatetime
    complete_through_cutoff: bool

    @model_validator(mode="after")
    def cutoff_is_valid(self) -> ConversationObservation:
        if self.retrieval_cutoff > self.retrieved_at:
            raise ValueError("conversation cutoff cannot be after retrieval")
        if any(value < 0 for value in self.engagement_snapshot.values()):
            raise ValueError("engagement values cannot be negative")
        return self


class EngagementOpportunity(DurableArtifact):
    opportunity_id: str = Field(min_length=1)
    conversation_ref: str = Field(min_length=1)
    disposition: EngagementDisposition
    persona_ref: str = Field(min_length=1)
    distinctive_contribution: str = Field(min_length=1)
    expertise_basis_ref: str | None = None
    proposed_stance: str = Field(min_length=1)
    risk_level: RiskLevel
    timeliness_expires_at: UtcDatetime
    evidence_refs: tuple[str, ...] = ()
    participant_relationship_ref: str | None = None
    expected_community_value: str = Field(min_length=1)
    generation: GenerationTrace


class CommentaryDraft(DurableArtifact):
    commentary_id: str = Field(min_length=1)
    persona_ref: str = Field(min_length=1)
    conversation_ref: str = Field(min_length=1)
    response_type: EngagementDisposition
    content: ContentDocument
    evidence_claims: tuple[EvidenceClaim, ...] = ()
    stance_ref: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    authorship_mode: str = Field(min_length=1)
    expires_at: UtcDatetime
    risk_level: RiskLevel
    generation: GenerationTrace


class CommentaryFinding(CreatorModel):
    check_id: str = Field(min_length=1)
    blocking: bool
    passed: bool
    detail: str = Field(min_length=1)


class CommentaryReview(DurableArtifact):
    review_id: str = Field(min_length=1)
    commentary_ref: str = Field(min_length=1)
    findings: tuple[CommentaryFinding, ...] = Field(min_length=1)
    ready_for_human_approval: bool
    approval_policy_ref: str = Field(min_length=1)
    approval_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    generation: GenerationTrace

    @model_validator(mode="after")
    def readiness_matches_findings(self) -> CommentaryReview:
        blocked = any(item.blocking and not item.passed for item in self.findings)
        if self.ready_for_human_approval == blocked:
            raise ValueError("commentary readiness must be false when a blocking check fails")
        return self
