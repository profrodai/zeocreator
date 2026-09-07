"""Additive email marketing v1 artifacts. Intent and evidence confer no effect authority.

All references are opaque, scoped and digest-bound. Subscriber records and provider
payloads have no representation. Runtime owns reference resolution and authorization.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator
from zeo_core.contracts import CapabilityId

from zeo_creator.contracts.common import (
    CreatorModel,
    DurableArtifact,
    UtcDatetime,
    canonical_digest,
)
from zeo_creator.contracts.evidence import ResearchWindow
from zeo_creator.contracts.newsroom import GenerationTrace

Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
OpaqueRef = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:/-]{0,199}$")]
Text = Annotated[str, Field(min_length=1, max_length=20000)]


def _no_addresses(value: object) -> None:
    if isinstance(value, BaseModel):
        _no_addresses(value.model_dump(mode="json"))
    elif isinstance(value, dict):
        for child in value.values():
            _no_addresses(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            _no_addresses(child)
    elif isinstance(value, str) and re.search(r"[^\s<>@]+@[^\s<>@]+\.[a-zA-Z]{2,}", value):
        raise ValueError("email addresses are not accepted in email marketing artifacts")


class EmailModel(CreatorModel):
    model_config = ConfigDict(
        hide_input_in_errors=True, revalidate_instances="always", str_strip_whitespace=False
    )

    @model_validator(mode="after")
    def no_contact_addresses(self) -> Self:
        _no_addresses(self)
        return self


class ScopedEmailModel(EmailModel):
    organization_id: OpaqueRef
    publication_id: OpaqueRef

    @model_validator(mode="after")
    def nested_scope_matches(self) -> Self:
        def walk(item: object) -> None:
            if isinstance(item, BaseModel):
                org = getattr(item, "organization_id", self.organization_id)
                pub = getattr(item, "publication_id", self.publication_id)
                if (org, pub) != (self.organization_id, self.publication_id):
                    raise ValueError("email artifact publication scope mismatch")
                for key in type(item).model_fields:
                    walk(getattr(item, key))
            elif isinstance(item, (tuple, list)):
                for child in item:
                    walk(child)

        for key in type(self).model_fields:
            walk(getattr(self, key))
        return self


class EmailArtifact(ScopedEmailModel, DurableArtifact):
    model_config = ConfigDict(str_strip_whitespace=False)

    schema_version: Literal["1.0.0"] = "1.0.0"
    artifact_id: OpaqueRef

    def binding(self) -> EmailArtifactRef:
        return EmailArtifactRef(
            organization_id=self.organization_id,
            publication_id=self.publication_id,
            ref=self.artifact_id,
            revision=self.revision,
            digest=self.content_digest,
        )


class EmailArtifactRef(ScopedEmailModel):
    ref: OpaqueRef
    revision: int = Field(ge=1)
    digest: Digest


class AudienceIntent(ScopedEmailModel):
    segment_refs: tuple[OpaqueRef, ...] = Field(min_length=1)
    lifecycle_states: tuple[OpaqueRef, ...] = ()
    required_inclusions: tuple[OpaqueRef, ...] = ()
    required_exclusions: tuple[OpaqueRef, ...] = ()
    consent_policy: EmailArtifactRef | None
    suppression_policy: EmailArtifactRef | None
    jurisdiction_policies: tuple[EmailArtifactRef, ...] = ()
    frequency_cap_policy: EmailArtifactRef
    purpose_of_contact: Text
    cross_publication_use_policy: EmailArtifactRef

    @model_validator(mode="after")
    def audience_sets(self) -> Self:
        for items in (self.segment_refs, self.required_inclusions, self.required_exclusions):
            if len(items) != len(set(items)):
                raise ValueError("audience references must be unique")
        if set(self.required_inclusions) & set(self.required_exclusions):
            raise ValueError("audience inclusions and exclusions overlap")
        return self


class AudienceSnapshotSummary(ScopedEmailModel):
    snapshot_ref: OpaqueRef
    snapshot_digest: Digest
    provider_kind: OpaqueRef
    connection_ref: OpaqueRef
    audience_intent_digest: Digest
    eligible_count: int = Field(ge=0)
    suppressed_count: int = Field(ge=0)
    resolved_at: UtcDatetime
    expires_at: UtcDatetime
    segment_definition_digest: Digest
    consent_policy_digest: Digest
    suppression_policy_digest: Digest
    drift_status: Literal["unchanged", "changed", "unknown"]
    purpose: Literal["production", "test"]

    @model_validator(mode="after")
    def valid_window(self) -> Self:
        if self.expires_at <= self.resolved_at:
            raise ValueError("snapshot expiry must follow resolution")
        return self


class EmailCTA(EmailModel):
    cta_id: OpaqueRef
    link_id: OpaqueRef
    label: Text
    desired_action: Text
    primary: bool = False


class EmailLink(EmailModel):
    link_id: OpaqueRef
    url: Annotated[str, Field(min_length=1, max_length=2048)]
    purpose: Literal["content", "cta", "unsubscribe"]
    tracking_required: bool

    @model_validator(mode="after")
    def public_link(self) -> Self:
        parsed = urlsplit(self.url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or "{" in self.url
            or "}" in self.url
        ):
            raise ValueError(
                "links require absolute HTTPS URLs without userinfo or tracking values"
            )
        return self


class PersonalizationDeclaration(EmailModel):
    name: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
    source_policy: OpaqueRef
    required: bool = True
    missing_value_behavior: Literal["refuse"] = "refuse"


class EmailCompliance(ScopedEmailModel):
    footer_policy: EmailArtifactRef
    unsubscribe_policy: EmailArtifactRef
    consent_policy: EmailArtifactRef | None
    suppression_policy: EmailArtifactRef | None
    footer_text: Text
    unsubscribe_link_id: OpaqueRef


class EmailCampaignPlan(EmailArtifact):
    publication_profile: EmailArtifactRef
    business_objective: Text
    audience: AudienceIntent
    campaign_window: ResearchWindow
    message_refs: tuple[EmailArtifactRef, ...] = ()
    sequence_refs: tuple[EmailArtifactRef, ...] = ()
    calls_to_action: tuple[EmailCTA, ...] = Field(min_length=1)
    conversion_objectives: tuple[EmailArtifactRef, ...] = Field(min_length=1)
    attribution_policy: EmailArtifactRef
    tracking_policy: EmailArtifactRef
    required_human_approvals: tuple[OpaqueRef, ...] = Field(min_length=1)
    assumptions: tuple[Text, ...] = ()
    risks: tuple[Text, ...] = ()
    stopping_conditions: tuple[Text, ...] = Field(min_length=1)
    generation: GenerationTrace


class EmailSequenceStepPlan(ScopedEmailModel):
    step_id: OpaqueRef
    ordinal: int = Field(ge=1, le=100)
    message_plan: EmailArtifactRef
    delay_seconds: int = Field(ge=0, le=31536000)
    delay_anchor: Literal["preceding_admitted_event"] = "preceding_admitted_event"
    purpose: Text
    desired_audience_action: Text
    send_window_policy: EmailArtifactRef
    skip_policy: EmailArtifactRef
    exit_policy: EmailArtifactRef
    freshness_max_age_seconds: int = Field(ge=1)
    required_approval_class: OpaqueRef


class EmailSequencePlan(EmailArtifact):
    campaign_or_lifecycle_program: EmailArtifactRef
    entry_policy: EmailArtifactRef
    exit_policy: EmailArtifactRef
    conversion_policy: EmailArtifactRef
    suppression_policy: EmailArtifactRef
    steps: tuple[EmailSequenceStepPlan, ...] = Field(min_length=1, max_length=100)
    send_window_policy: EmailArtifactRef
    quiet_hours_policy: EmailArtifactRef
    time_zone_policy: EmailArtifactRef
    maximum_enrolment_window: ResearchWindow
    required_provider_semantics: tuple[OpaqueRef, ...] = Field(min_length=1)
    existing_enrollee_migration_policy: Literal[
        "retain_existing_revision", "explicit_new_authority"
    ]
    migration_policy: EmailArtifactRef | None = None
    activation_requirements: tuple[OpaqueRef, ...] = Field(min_length=1)
    approval_requirements: tuple[OpaqueRef, ...] = Field(min_length=1)
    previous_revision: EmailArtifactRef | None = None
    generation: GenerationTrace

    @model_validator(mode="after")
    def linear_immutable_revision(self) -> Self:
        if tuple(step.ordinal for step in self.steps) != tuple(range(1, len(self.steps) + 1)):
            raise ValueError("sequence ordinals must be contiguous and ordered from one")
        if len({step.step_id for step in self.steps}) != len(self.steps):
            raise ValueError("sequence step identities must be unique")
        if self.previous_revision:
            if (
                self.previous_revision.ref != self.artifact_id
                or self.revision != self.previous_revision.revision + 1
            ):
                raise ValueError("sequence edits require the next immutable revision")
        elif self.revision != 1:
            raise ValueError("later sequence revisions require a predecessor binding")
        if (
            self.existing_enrollee_migration_policy == "explicit_new_authority"
            and not self.migration_policy
        ):
            raise ValueError(
                "enrollee migration requires an explicit policy and separate runtime authority"
            )
        return self


class EmailMessagePlan(EmailArtifact):
    publication_profile: EmailArtifactRef
    campaign: EmailArtifactRef
    purpose: Text
    objective: Text
    audience: AudienceIntent
    lifecycle_stage: OpaqueRef
    subject_direction: Text
    preheader_direction: Text
    required_sections: tuple[Text, ...] = Field(min_length=1)
    calls_to_action: tuple[EmailCTA, ...] = Field(min_length=1)
    personalization: tuple[PersonalizationDeclaration, ...] = ()
    links: tuple[EmailLink, ...] = Field(min_length=1)
    tracking_policy: EmailArtifactRef
    sender_identity: EmailArtifactRef
    reply_to_identity: EmailArtifactRef
    compliance: EmailCompliance
    source_evidence: tuple[EmailArtifactRef, ...] = Field(min_length=1)
    brand_policy: EmailArtifactRef
    voice_policy: EmailArtifactRef
    accessibility_requirements: tuple[Text, ...] = Field(min_length=1)
    preview_required: bool = True
    test_send_required: bool = True
    newsletter_issue: EmailArtifactRef | None = None
    generation: GenerationTrace


class EmailMessageDraft(EmailArtifact):
    message_plan: EmailArtifactRef
    subject: Annotated[str, Field(min_length=1, max_length=998, pattern=r"^[^\r\n]+$")]
    preheader: Annotated[str, Field(min_length=1, max_length=998, pattern=r"^[^\r\n]+$")]
    html: Annotated[str, Field(min_length=1, max_length=1000000)]
    plain_text: Annotated[str, Field(min_length=1, max_length=1000000)]
    links: tuple[EmailLink, ...] = Field(min_length=1)
    calls_to_action: tuple[EmailCTA, ...] = Field(min_length=1)
    personalization: tuple[PersonalizationDeclaration, ...] = ()
    sender_identity: EmailArtifactRef
    reply_to_identity: EmailArtifactRef
    compliance: EmailCompliance
    source_lineage: tuple[EmailArtifactRef, ...] = Field(min_length=1)
    generation: GenerationTrace

    @model_validator(mode="after")
    def manifest_identity(self) -> Self:
        for values in (
            tuple(link.link_id for link in self.links),
            tuple(cta.cta_id for cta in self.calls_to_action),
            tuple(token.name for token in self.personalization),
        ):
            if len(set(values)) != len(values):
                raise ValueError("manifest identities must be unique")
        links = {link.link_id: link for link in self.links}
        if any(cta.link_id not in links for cta in self.calls_to_action):
            raise ValueError("CTA must resolve to the link manifest")
        unsubscribe = links.get(self.compliance.unsubscribe_link_id)
        if not unsubscribe or unsubscribe.purpose != "unsubscribe":
            raise ValueError("compliance must identify an unsubscribe link")
        if sum(cta.primary for cta in self.calls_to_action) != 1:
            raise ValueError("draft requires exactly one primary CTA")
        return self


EmailReviewCheck = Literal[
    "source_traceability",
    "publication_voice",
    "audience_policy",
    "subject_body",
    "html_plain_text",
    "links",
    "cta",
    "personalization",
    "accessibility",
    "footer_unsubscribe",
    "consent_suppression",
    "claims",
    "preview",
    "test_send",
]
REVIEW_CHECKS: tuple[EmailReviewCheck, ...] = (
    "source_traceability",
    "publication_voice",
    "audience_policy",
    "subject_body",
    "html_plain_text",
    "links",
    "cta",
    "personalization",
    "accessibility",
    "footer_unsubscribe",
    "consent_suppression",
    "claims",
    "preview",
    "test_send",
)


class EmailReviewFinding(EmailModel):
    check: EmailReviewCheck
    status: Literal["pass", "blocked", "human_needed"]
    reason: OpaqueRef


class EmailReviewEvidence(EmailArtifact):
    """Caller-supplied review evidence; authenticity is verified by the controlling runtime."""

    draft: EmailArtifactRef
    check: EmailReviewCheck
    passed: bool
    policy: EmailArtifactRef
    receipt_ref: OpaqueRef
    valid_until: UtcDatetime


class EmailEditorialReview(EmailArtifact):
    plan: EmailArtifactRef
    draft: EmailArtifactRef
    findings: tuple[EmailReviewFinding, ...]
    evidence: tuple[EmailReviewEvidence, ...] = ()
    ready_for_human_approval: bool
    generation: GenerationTrace

    @model_validator(mode="after")
    def no_self_approval(self) -> Self:
        if sorted(row.check for row in self.findings) != sorted(REVIEW_CHECKS):
            raise ValueError("review requires exactly one finding for every check")
        if self.ready_for_human_approval != all(row.status == "pass" for row in self.findings):
            raise ValueError("review readiness must match every finding")
        return self


class EmailProofReceipt(EmailArtifact):
    draft: EmailArtifactRef
    kind: Literal["preview", "test_send"]
    receipt_ref: OpaqueRef
    audience_snapshot: AudienceSnapshotSummary | None = None
    personalization_resolved: bool
    successful: bool
    valid_until: UtcDatetime

    @model_validator(mode="after")
    def test_is_separate(self) -> Self:
        if self.kind == "test_send" and (
            self.audience_snapshot is None or self.audience_snapshot.purpose != "test"
        ):
            raise ValueError("test evidence requires a separate test audience")
        return self


class EmailDeliveryMaterial(ScopedEmailModel):
    draft: EmailMessageDraft
    html_digest: Digest
    plain_text_digest: Digest
    link_manifest_digest: Digest
    audience_snapshot: AudienceSnapshotSummary
    tracking_policy: EmailArtifactRef
    schedule_intent: UtcDatetime | None = None
    campaign: EmailArtifactRef
    sequence_revision: EmailArtifactRef | None = None
    review: EmailEditorialReview
    proofs: tuple[EmailProofReceipt, ...] = ()

    @model_validator(mode="after")
    def exact_material(self) -> Self:
        if (
            self.html_digest != canonical_digest(self.draft.html)
            or self.plain_text_digest != canonical_digest(self.draft.plain_text)
            or self.link_manifest_digest != canonical_digest(self.draft.links)
            or self.review.draft != self.draft.binding()
        ):
            raise ValueError("delivery material does not match the exact draft")
        return self


class EmailDeliveryPackage(EmailArtifact):
    material: EmailDeliveryMaterial
    approval_digest: Digest

    @model_validator(mode="after")
    def exact_approval(self) -> Self:
        if self.approval_digest != canonical_digest(self.material):
            raise ValueError("approval digest does not match delivery material")
        return self


class EmailEffectIntent(StrEnum):
    """Editorial intent only. Zeocore owns the executable operation vocabulary."""

    CREATE_DRAFT = "create_remote_draft"
    UPDATE_DRAFT = "update_remote_draft"
    TEST = "send_test"
    SCHEDULE = "schedule_broadcast"
    SEND = "send_broadcast"
    ACTIVATE = "activate_sequence_revision"
    ENROL = "enrol_audience_snapshot"
    PAUSE = "pause_future_steps"
    CANCEL = "cancel_scheduled_broadcast"
    RETIRE = "retire_sequence_revision"


class EmailOperationIntent(ScopedEmailModel):
    intent: EmailEffectIntent
    operation: CapabilityId
    operation_contract_digest: Digest
    delivery: EmailArtifactRef | None = None
    delivery_approval_digest: Digest | None = None
    sequence: EmailArtifactRef | None = None
    audience: AudienceSnapshotSummary | None = None
    target_remote_ref: OpaqueRef | None = None
    expected_remote_revision_digest: Digest | None = None
    migration_policy: EmailArtifactRef | None = None

    @model_validator(mode="after")
    def distinct_effect_requirements(self) -> Self:
        content_effects = {
            EmailEffectIntent.CREATE_DRAFT,
            EmailEffectIntent.UPDATE_DRAFT,
            EmailEffectIntent.TEST,
            EmailEffectIntent.SCHEDULE,
            EmailEffectIntent.SEND,
        }
        sequence_effects = {
            EmailEffectIntent.ACTIVATE,
            EmailEffectIntent.ENROL,
            EmailEffectIntent.PAUSE,
            EmailEffectIntent.RETIRE,
        }
        if self.intent in content_effects and (
            not self.delivery or not self.delivery_approval_digest
        ):
            raise ValueError("content effects require an exact delivery binding")
        if self.intent in sequence_effects and not self.sequence:
            raise ValueError("sequence effects require an exact sequence revision")
        if self.intent in {
            EmailEffectIntent.TEST,
            EmailEffectIntent.SEND,
            EmailEffectIntent.SCHEDULE,
            EmailEffectIntent.ENROL,
        }:
            if not self.audience:
                raise ValueError("effect requires an exact audience snapshot")
            expected = "test" if self.intent == EmailEffectIntent.TEST else "production"
            if self.audience.purpose != expected:
                raise ValueError("test and production audiences are distinct")
        if self.intent == EmailEffectIntent.ACTIVATE and self.audience:
            raise ValueError("activation cannot authorize audience enrolment")
        if self.intent in {
            EmailEffectIntent.UPDATE_DRAFT,
            EmailEffectIntent.CANCEL,
            EmailEffectIntent.PAUSE,
            EmailEffectIntent.RETIRE,
        }:
            if not self.target_remote_ref or not self.expected_remote_revision_digest:
                raise ValueError("remote mutation requires a target and observed revision digest")
        return self


class ProposedEmailOperation(EmailArtifact):
    material: EmailOperationIntent
    approval_digest: Digest
    idempotency_key: OpaqueRef

    @model_validator(mode="after")
    def exact_effect_approval(self) -> Self:
        if self.approval_digest != canonical_digest(self.material):
            raise ValueError("effect approval digest does not match operation intent")
        return self


EmailMetricName = Literal[
    "attempted",
    "accepted",
    "delivered",
    "deferred",
    "bounced",
    "complained",
    "unsubscribed",
    "opened",
    "unique_link_clicks",
    "cta_conversions",
    "sequence_enrolments",
    "step_completion",
    "step_exit",
    "campaign_conversion",
    "attributed_revenue",
]


class EmailMetricObservation(EmailArtifact):
    campaign: EmailArtifactRef
    operation: EmailArtifactRef
    retrieval_receipt: EmailArtifactRef
    provider_kind: OpaqueRef
    connection_ref: OpaqueRef
    aggregate_segment_ref: OpaqueRef
    observation_window: ResearchWindow
    metric: EmailMetricName
    value: float = Field(ge=0, allow_inf_nan=False)
    unit: OpaqueRef
    numerator: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    denominator: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    provider_definition: Text
    provider_definition_version: OpaqueRef
    completeness: Literal["complete", "partial", "unknown"]
    coverage: float = Field(ge=0, le=1, allow_inf_nan=False)
    reliability: Literal["qualified", "unreliable", "unknown"]
    reliability_notes: tuple[Text, ...] = ()
    attribution_policy: EmailArtifactRef | None = None
    attribution_assumptions: tuple[Text, ...] = ()
    data_gaps: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def qualified_metrics(self) -> Self:
        if (self.numerator is None) != (self.denominator is None):
            raise ValueError("ratios require a numerator and nonzero denominator")
        if self.unit == "rate" and (
            self.numerator is None
            or self.denominator is None
            or abs(self.value - self.numerator / self.denominator) > 1e-12
        ):
            raise ValueError("rate must equal its declared numerator over denominator")
        if self.metric == "attributed_revenue" and not self.attribution_policy:
            raise ValueError("revenue requires an explicit attribution policy")
        if self.metric == "opened" and not self.reliability_notes:
            raise ValueError("opens require reliability qualifications")
        if self.completeness == "complete" and (self.coverage != 1 or self.data_gaps):
            raise ValueError("complete observations must have full coverage and no gaps")
        return self


class EmailProgramAssessment(EmailArtifact):
    campaign: EmailArtifactRef
    observation_window: ResearchWindow
    observations: tuple[EmailMetricObservation, ...]
    completeness: Literal["complete", "partial", "unknown"]
    confidence: Literal["limited", "qualified"]
    conclusions: tuple[Text, ...]
    data_gaps: tuple[Text, ...]
    hypotheses: tuple[Text, ...]
    generation: GenerationTrace

    @model_validator(mode="after")
    def no_overstatement(self) -> Self:
        complete = bool(self.observations) and all(
            item.completeness == "complete" and item.reliability == "qualified"
            for item in self.observations
        )
        if not complete and (self.completeness == "complete" or self.confidence != "limited"):
            raise ValueError(
                "partial or unreliable observations cannot support a complete assessment"
            )
        if any(item.campaign != self.campaign for item in self.observations):
            raise ValueError("assessment observations must bind the same campaign revision")
        return self
