"""News publishing integrity contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact, UtcDatetime
from zeo_creator.contracts.evidence import EvidenceClaim
from zeo_creator.contracts.newsroom import GenerationTrace, RiskLevel
from zeo_creator.contracts.production import ContentDocument


class HighRiskClassification(StrEnum):
    IDENTIFIABLE_PERSON_ALLEGATION = "IDENTIFIABLE_PERSON_ALLEGATION"
    CRIME_OR_VICTIM = "CRIME_OR_VICTIM"
    MINOR = "MINOR"
    ELECTION_OR_POLITICAL_CLAIM = "ELECTION_OR_POLITICAL_CLAIM"
    PUBLIC_SAFETY = "PUBLIC_SAFETY"
    HEALTH = "HEALTH"
    FINANCIAL_CLAIM = "FINANCIAL_CLAIM"
    PRIVATE_PERSONAL_INFORMATION = "PRIVATE_PERSONAL_INFORMATION"
    UNVERIFIED_SOCIAL_REPORT = "UNVERIFIED_SOCIAL_REPORT"


class BylineAssignment(CreatorModel):
    contributor_ref: str = Field(min_length=1)
    role: str = Field(min_length=1)
    disclosure: str | None = None
    accepted: bool = False


class NewsArticlePlan(DurableArtifact):
    article_plan_id: str = Field(min_length=1)
    dossier_refs: tuple[str, ...] = Field(min_length=1)
    headline_direction: str = Field(min_length=1)
    thesis: str = Field(min_length=1)
    required_claim_refs: tuple[str, ...] = Field(min_length=1)
    reporting_gaps: tuple[str, ...] = ()
    bylines: tuple[BylineAssignment, ...] = Field(min_length=1)
    risk_level: RiskLevel
    high_risk_classifications: tuple[HighRiskClassification, ...] = ()
    human_editor_policy_ref: str = Field(min_length=1)
    generation: GenerationTrace


class NewsArticleDraft(DurableArtifact):
    article_draft_id: str = Field(min_length=1)
    article_plan_ref: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    deck: str | None = None
    body: ContentDocument
    claims: tuple[EvidenceClaim, ...] = Field(min_length=1)
    source_refs: tuple[str, ...] = Field(min_length=1)
    bylines: tuple[BylineAssignment, ...] = Field(min_length=1)
    generation: GenerationTrace

    @model_validator(mode="after")
    def claims_use_article_sources(self) -> NewsArticleDraft:
        allowed = set(self.source_refs)
        if any(ref not in allowed for claim in self.claims for ref in claim.evidence_refs):
            raise ValueError("article claims must reference article source_refs")
        return self


class EditorialReview(DurableArtifact):
    review_id: str = Field(min_length=1)
    article_draft_ref: str = Field(min_length=1)
    claim_traceability: bool
    attribution_satisfied: bool
    privacy_satisfied: bool
    risk_policy_satisfied: bool
    qualified_human_required: bool
    qualified_human_review_ref: str | None = None
    blocking_findings: tuple[str, ...] = ()
    advisory_findings: tuple[str, ...] = ()
    ready_for_approval: bool
    approval_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    generation: GenerationTrace

    @model_validator(mode="after")
    def review_fails_closed(self) -> EditorialReview:
        human_ok = not self.qualified_human_required or bool(self.qualified_human_review_ref)
        expected = (
            self.claim_traceability
            and self.attribution_satisfied
            and self.privacy_satisfied
            and self.risk_policy_satisfied
            and human_ok
            and not self.blocking_findings
        )
        if self.ready_for_approval != expected:
            raise ValueError("editorial readiness must match checks and required human review")
        return self


class CorrectionNotice(DurableArtifact):
    correction_id: str = Field(min_length=1)
    publication_artifact_ref: str = Field(min_length=1)
    corrected_claim_refs: tuple[str, ...] = Field(min_length=1)
    correction_text: ContentDocument
    reason: str = Field(min_length=1)
    effective_at: UtcDatetime
    editor_review_ref: str = Field(min_length=1)


class RetractionNotice(DurableArtifact):
    retraction_id: str = Field(min_length=1)
    publication_artifact_ref: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    notice: ContentDocument
    effective_at: UtcDatetime
    editor_review_ref: str = Field(min_length=1)


class PublicationUpdate(DurableArtifact):
    update_id: str = Field(min_length=1)
    publication_artifact_ref: str = Field(min_length=1)
    update_kind: str = Field(min_length=1)
    content: ContentDocument
    effective_at: UtcDatetime
    supersedes_update_ref: str | None = None
