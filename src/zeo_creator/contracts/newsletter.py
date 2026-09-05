"""Newsletter specializations over story dossiers and edition plans."""

from __future__ import annotations

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact
from zeo_creator.contracts.newsroom import GenerationTrace
from zeo_creator.contracts.production import ContentDocument


class AudienceSelection(CreatorModel):
    segment_refs: tuple[str, ...] = Field(min_length=1)
    selection_policy_ref: str = Field(min_length=1)
    suppression_policy_ref: str = Field(min_length=1)
    consent_policy_ref: str = Field(min_length=1)


class NewsletterSectionPlan(CreatorModel):
    section_id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    dossier_refs: tuple[str, ...] = Field(min_length=1)
    purpose: str = Field(min_length=1)
    call_to_action: str | None = None


class NewsletterIssuePlan(DurableArtifact):
    issue_plan_id: str = Field(min_length=1)
    edition_plan_ref: str = Field(min_length=1)
    working_title: str = Field(min_length=1)
    subject_variants: tuple[str, ...] = Field(min_length=1)
    preheader_variants: tuple[str, ...] = Field(min_length=1)
    sections: tuple[NewsletterSectionPlan, ...] = Field(min_length=1)
    audience: AudienceSelection
    campaign_ref: str | None = None
    sequence_ref: str | None = None
    link_tracking_plan_ref: str = Field(min_length=1)
    preview_required: bool = True
    test_send_required: bool = True
    generation: GenerationTrace


class NewsletterIssueDraft(DurableArtifact):
    issue_draft_id: str = Field(min_length=1)
    issue_plan_ref: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    preheader: str = Field(min_length=1)
    html_content: ContentDocument
    plain_text_content: ContentDocument
    source_refs: tuple[str, ...] = Field(min_length=1)
    generation: GenerationTrace

    @model_validator(mode="after")
    def media_types_are_correct(self) -> NewsletterIssueDraft:
        if self.html_content.media_type != "text/html":
            raise ValueError("newsletter html_content must use text/html")
        if self.plain_text_content.media_type != "text/plain":
            raise ValueError("newsletter plain_text_content must use text/plain")
        return self


class NewsletterEditorialReview(DurableArtifact):
    review_id: str = Field(min_length=1)
    issue_draft_ref: str = Field(min_length=1)
    section_coverage: bool
    source_traceability: bool
    audience_policy_satisfied: bool
    links_validated: bool
    preview_required: bool
    test_send_required: bool
    blocking_findings: tuple[str, ...] = ()
    advisory_findings: tuple[str, ...] = ()
    ready_for_human_approval: bool
    approval_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    generation: GenerationTrace

    @model_validator(mode="after")
    def review_fails_closed(self) -> NewsletterEditorialReview:
        checks = (
            self.section_coverage,
            self.source_traceability,
            self.audience_policy_satisfied,
            self.links_validated,
        )
        expected = all(checks) and not self.blocking_findings
        if self.ready_for_human_approval != expected:
            raise ValueError("newsletter readiness must match checks and blocking findings")
        return self
