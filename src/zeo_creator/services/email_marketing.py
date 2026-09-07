"""Input-only email transformations and conservative deterministic reference strategy."""

from __future__ import annotations

import re
from datetime import datetime
from html import escape
from html.parser import HTMLParser
from typing import Never, Protocol

from pydantic import BaseModel, Field

from zeo_creator.contracts.common import (
    DurableArtifact,
    canonical_digest,
    digest_is_current,
    stable_id,
)
from zeo_creator.contracts.email_marketing import (
    REVIEW_CHECKS,
    AudienceIntent,
    AudienceSnapshotSummary,
    EmailArtifactRef,
    EmailCampaignPlan,
    EmailCompliance,
    EmailCTA,
    EmailDeliveryMaterial,
    EmailDeliveryPackage,
    EmailEditorialReview,
    EmailLink,
    EmailMessageDraft,
    EmailMessagePlan,
    EmailMetricObservation,
    EmailOperationIntent,
    EmailProgramAssessment,
    EmailProofReceipt,
    EmailReviewEvidence,
    EmailReviewFinding,
    EmailSequencePlan,
    EmailSequenceStepPlan,
    OpaqueRef,
    PersonalizationDeclaration,
    ProposedEmailOperation,
    ScopedEmailModel,
    Text,
)
from zeo_creator.contracts.evidence import ResearchWindow
from zeo_creator.contracts.newsletter import NewsletterIssuePlan
from zeo_creator.contracts.newsroom import GenerationTrace
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError


def refuse(reason: str) -> Never:
    raise CreatorDomainError("ZEO_CREATOR_EMAIL_INVALID", reason)


def current(*items: object) -> None:
    """Reject unsafe copies and nested mutation before trusting any bound digest."""
    for item in items:
        if isinstance(item, DurableArtifact) and not digest_is_current(item):
            refuse("stale_email_artifact")
        if isinstance(item, BaseModel):
            type(item).model_validate_json(item.model_dump_json())
            current(*(getattr(item, name) for name in type(item).model_fields))
        elif isinstance(item, (list, tuple)):
            current(*item)


def scope(anchor: object, *items: object) -> None:
    current(anchor, *items)
    expected = (getattr(anchor, "organization_id"), getattr(anchor, "publication_id"))
    for item in items:
        if (getattr(item, "organization_id"), getattr(item, "publication_id")) != expected:
            refuse("email_publication_scope_mismatch")


def profile_binding(profile: PublicationProfile) -> EmailArtifactRef:
    current(profile)
    return EmailArtifactRef(
        organization_id=profile.organization_id,
        publication_id=profile.publication_id,
        ref=profile.profile_id,
        revision=profile.revision,
        digest=profile.content_digest,
    )


def trace(name: str, *items: object) -> GenerationTrace:
    return GenerationTrace(
        strategy_ref=f"zeo-creator.reference.email.{name}",
        strategy_version="1.0.0",
        policy_version="1.0.0",
        input_digests=tuple(canonical_digest(item) for item in items),
    )


class EmailCampaignBrief(ScopedEmailModel):
    campaign_id: OpaqueRef
    objective: Text
    audience: AudienceIntent
    window: ResearchWindow
    calls_to_action: tuple[EmailCTA, ...] = Field(min_length=1)
    conversion_objectives: tuple[EmailArtifactRef, ...] = Field(min_length=1)
    attribution_policy: EmailArtifactRef
    tracking_policy: EmailArtifactRef
    stopping_conditions: tuple[Text, ...] = Field(min_length=1)
    assumptions: tuple[Text, ...] = ()
    risks: tuple[Text, ...] = ()


class EmailSequencePolicies(ScopedEmailModel):
    entry: EmailArtifactRef
    exit: EmailArtifactRef
    conversion: EmailArtifactRef
    suppression: EmailArtifactRef
    send_window: EmailArtifactRef
    quiet_hours: EmailArtifactRef
    time_zone: EmailArtifactRef
    skip: EmailArtifactRef
    freshness_max_age_seconds: int = Field(ge=1)


class EmailMessageDirections(ScopedEmailModel):
    message_id: OpaqueRef
    purpose: Text
    objective: Text
    lifecycle_stage: OpaqueRef
    subject: Text
    preheader: Text
    sections: tuple[Text, ...] = Field(min_length=1)
    links: tuple[EmailLink, ...] = Field(min_length=1)
    calls_to_action: tuple[EmailCTA, ...] = Field(min_length=1)
    personalization: tuple[PersonalizationDeclaration, ...] = ()
    sender: EmailArtifactRef
    reply_to: EmailArtifactRef
    compliance: EmailCompliance
    sources: tuple[EmailArtifactRef, ...] = Field(min_length=1)
    brand_policy: EmailArtifactRef
    voice_policy: EmailArtifactRef
    accessibility: tuple[Text, ...] = Field(min_length=1)
    preview_required: bool = True
    test_send_required: bool = True


class EmailSourceSection(ScopedEmailModel):
    heading: Text
    text: Text
    evidence: tuple[EmailArtifactRef, ...] = Field(min_length=1)


class EmailCreativeStrategy(Protocol):
    """Injected implementations receive curated inputs, never a context or connector."""

    def compose(
        self, plan: EmailMessagePlan, sections: tuple[EmailSourceSection, ...], created_at: datetime
    ) -> EmailMessageDraft: ...


class DeterministicEmailStrategy:
    def compose(
        self, plan: EmailMessagePlan, sections: tuple[EmailSourceSection, ...], created_at: datetime
    ) -> EmailMessageDraft:
        links = {link.link_id: link for link in plan.links}
        blocks = [(section.heading, section.text) for section in sections]
        plain = "\n\n".join(f"{heading}\n{text}" for heading, text in blocks)
        html = "".join(
            f"<h2>{escape(heading)}</h2><p>{escape(text)}</p>" for heading, text in blocks
        )
        for cta in plan.calls_to_action:
            link = links[cta.link_id]
            plain += f"\n\n{cta.label} {link.url}"
            html += f'<p><a href="{escape(link.url, quote=True)}">{escape(cta.label)}</a> {escape(link.url)}</p>'
        unsubscribe = links[plan.compliance.unsubscribe_link_id]
        footer = f"{plan.compliance.footer_text} Unsubscribe {unsubscribe.url}"
        plain += f"\n\n{footer}"
        html += f'<footer>{escape(plan.compliance.footer_text)} <a href="{escape(unsubscribe.url, quote=True)}">Unsubscribe</a> {escape(unsubscribe.url)}</footer>'
        return EmailMessageDraft(
            artifact_id=stable_id("email_draft", plan.content_digest, canonical_digest(sections)),
            created_at=created_at,
            organization_id=plan.organization_id,
            publication_id=plan.publication_id,
            input_refs=(plan.artifact_id,),
            message_plan=plan.binding(),
            subject=plan.subject_direction,
            preheader=plan.preheader_direction,
            html=html,
            plain_text=plain,
            links=plan.links,
            calls_to_action=plan.calls_to_action,
            personalization=plan.personalization,
            sender_identity=plan.sender_identity,
            reply_to_identity=plan.reply_to_identity,
            compliance=plan.compliance,
            source_lineage=plan.source_evidence,
            generation=trace("compose", plan, sections),
        )


def plan_campaign(
    profile: PublicationProfile, brief: EmailCampaignBrief, created_at: datetime
) -> EmailCampaignPlan:
    scope(profile, brief)
    if sum(cta.primary for cta in brief.calls_to_action) != 1:
        refuse("campaign_requires_one_primary_cta")
    return EmailCampaignPlan(
        artifact_id=brief.campaign_id,
        created_at=created_at,
        organization_id=profile.organization_id,
        publication_id=profile.publication_id,
        input_refs=(profile.profile_id,),
        publication_profile=profile_binding(profile),
        business_objective=brief.objective,
        audience=brief.audience,
        campaign_window=brief.window,
        calls_to_action=brief.calls_to_action,
        conversion_objectives=brief.conversion_objectives,
        attribution_policy=brief.attribution_policy,
        tracking_policy=brief.tracking_policy,
        required_human_approvals=(profile.approval_policy_ref,),
        assumptions=brief.assumptions,
        risks=brief.risks,
        stopping_conditions=brief.stopping_conditions,
        generation=trace("campaign", profile, brief),
    )


def plan_message(
    profile: PublicationProfile,
    campaign: EmailCampaignPlan,
    directions: EmailMessageDirections,
    created_at: datetime,
    newsletter: NewsletterIssuePlan | None = None,
) -> EmailMessagePlan:
    scope(profile, campaign, directions)
    if campaign.publication_profile != profile_binding(profile):
        refuse("campaign_profile_revision_changed")
    newsletter_ref = None
    if newsletter:
        scope(profile, newsletter)
        if (
            newsletter.audience.segment_refs != campaign.audience.segment_refs
            or not campaign.audience.consent_policy
            or newsletter.audience.consent_policy_ref != campaign.audience.consent_policy.ref
            or not campaign.audience.suppression_policy
            or newsletter.audience.suppression_policy_ref
            != campaign.audience.suppression_policy.ref
        ):
            refuse("newsletter_audience_requires_explicit_migration")
        newsletter_ref = EmailArtifactRef(
            organization_id=newsletter.organization_id,
            publication_id=newsletter.publication_id,
            ref=newsletter.issue_plan_id,
            revision=newsletter.revision,
            digest=newsletter.content_digest,
        )
        if (
            directions.subject not in newsletter.subject_variants
            or directions.preheader not in newsletter.preheader_variants
        ):
            refuse("newsletter_directions_must_select_existing_variants")
    if (
        directions.compliance.consent_policy != campaign.audience.consent_policy
        or directions.compliance.suppression_policy != campaign.audience.suppression_policy
    ):
        refuse("message_compliance_must_match_audience")
    return EmailMessagePlan(
        artifact_id=directions.message_id,
        created_at=created_at,
        organization_id=profile.organization_id,
        publication_id=profile.publication_id,
        input_refs=(profile.profile_id, campaign.artifact_id),
        publication_profile=profile_binding(profile),
        campaign=campaign.binding(),
        purpose=directions.purpose,
        objective=directions.objective,
        audience=campaign.audience,
        lifecycle_stage=directions.lifecycle_stage,
        subject_direction=directions.subject,
        preheader_direction=directions.preheader,
        required_sections=directions.sections,
        calls_to_action=directions.calls_to_action,
        personalization=directions.personalization,
        links=directions.links,
        tracking_policy=campaign.tracking_policy,
        sender_identity=directions.sender,
        reply_to_identity=directions.reply_to,
        compliance=directions.compliance,
        source_evidence=directions.sources,
        brand_policy=directions.brand_policy,
        voice_policy=directions.voice_policy,
        accessibility_requirements=directions.accessibility,
        preview_required=directions.preview_required
        or bool(newsletter and newsletter.preview_required),
        test_send_required=directions.test_send_required
        or bool(newsletter and newsletter.test_send_required),
        newsletter_issue=newsletter_ref,
        generation=trace("message", profile, campaign, directions, newsletter),
    )


def plan_sequence(
    campaign: EmailCampaignPlan,
    sequence_id: str,
    messages: tuple[EmailMessagePlan, ...],
    delays: tuple[int, ...],
    policies: EmailSequencePolicies,
    enrolment_window: ResearchWindow,
    required_semantics: tuple[str, ...],
    created_at: datetime,
    previous: EmailSequencePlan | None = None,
    migration_policy: EmailArtifactRef | None = None,
) -> EmailSequencePlan:
    scope(campaign, policies, *messages)
    if not messages or len(messages) != len(delays):
        refuse("sequence_requires_one_delay_per_message")
    if len({message.artifact_id for message in messages}) != len(messages):
        refuse("sequence_requires_unique_message_identities")
    if any(message.campaign != campaign.binding() for message in messages):
        refuse("sequence_messages_must_match_campaign_revision")
    if previous:
        scope(campaign, previous)
        if previous.artifact_id != sequence_id:
            refuse("sequence_predecessor_identity_mismatch")
    if migration_policy:
        scope(campaign, migration_policy)
    steps = tuple(
        EmailSequenceStepPlan(
            organization_id=campaign.organization_id,
            publication_id=campaign.publication_id,
            step_id=stable_id("email_step", sequence_id, message.artifact_id),
            ordinal=index + 1,
            message_plan=message.binding(),
            delay_seconds=delays[index],
            purpose=message.purpose,
            desired_audience_action=message.calls_to_action[0].desired_action,
            send_window_policy=policies.send_window,
            skip_policy=policies.skip,
            exit_policy=policies.exit,
            freshness_max_age_seconds=policies.freshness_max_age_seconds,
            required_approval_class=campaign.required_human_approvals[0],
        )
        for index, message in enumerate(messages)
    )
    return EmailSequencePlan(
        artifact_id=sequence_id,
        created_at=created_at,
        organization_id=campaign.organization_id,
        publication_id=campaign.publication_id,
        input_refs=(campaign.artifact_id, *(message.artifact_id for message in messages)),
        revision=previous.revision + 1 if previous else 1,
        campaign_or_lifecycle_program=campaign.binding(),
        entry_policy=policies.entry,
        exit_policy=policies.exit,
        conversion_policy=policies.conversion,
        suppression_policy=policies.suppression,
        steps=steps,
        send_window_policy=policies.send_window,
        quiet_hours_policy=policies.quiet_hours,
        time_zone_policy=policies.time_zone,
        maximum_enrolment_window=enrolment_window,
        required_provider_semantics=required_semantics,
        existing_enrollee_migration_policy="explicit_new_authority"
        if migration_policy
        else "retain_existing_revision",
        migration_policy=migration_policy,
        activation_requirements=("exact_revision_approval", "provider_semantics_supported"),
        approval_requirements=campaign.required_human_approvals,
        previous_revision=previous.binding() if previous else None,
        generation=trace(
            "sequence",
            campaign,
            messages,
            delays,
            policies,
            enrolment_window,
            required_semantics,
            previous,
            migration_policy,
        ),
    )


def compose_message(
    plan: EmailMessagePlan,
    sections: tuple[EmailSourceSection, ...],
    created_at: datetime,
    strategy: EmailCreativeStrategy | None = None,
) -> EmailMessageDraft:
    scope(plan, *sections)
    if tuple(section.heading for section in sections) != plan.required_sections:
        refuse("source_sections_must_match_plan_order")
    if any(ref not in plan.source_evidence for section in sections for ref in section.evidence):
        refuse("source_section_evidence_not_in_plan")
    draft = (strategy or DeterministicEmailStrategy()).compose(plan, sections, created_at)
    scope(plan, draft)
    if (
        draft.message_plan != plan.binding()
        or draft.generation.input_digests != trace("compose", plan, sections).input_digests
    ):
        refuse("strategy_output_does_not_bind_exact_inputs")
    return draft


class _HTMLInspection(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.links: list[str] = []
        self.unsafe = False
        self.inaccessible = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag not in {
            "p",
            "h1",
            "h2",
            "h3",
            "strong",
            "em",
            "a",
            "ul",
            "ol",
            "li",
            "br",
            "footer",
            "div",
            "span",
        }:
            self.unsafe = True
        if any(key not in {"href", "lang"} for key in attributes):
            self.unsafe = True
        if tag == "a":
            self.links.append(attributes.get("href") or "")
        if tag in {"p", "h1", "h2", "h3", "li", "br", "footer", "div"}:
            self.text.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "h1", "h2", "h3", "li", "footer", "div"}:
            self.text.append(" ")

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def review_message(
    profile: PublicationProfile,
    plan: EmailMessagePlan,
    draft: EmailMessageDraft,
    evidence: tuple[EmailReviewEvidence, ...],
    created_at: datetime,
) -> EmailEditorialReview:
    scope(profile, plan, draft, *evidence)
    if plan.publication_profile != profile_binding(profile) or draft.message_plan != plan.binding():
        refuse("review_plan_or_profile_changed")
    return _review_exact_message(plan, draft, evidence, created_at)


def _review_exact_message(
    plan: EmailMessagePlan,
    draft: EmailMessageDraft,
    evidence: tuple[EmailReviewEvidence, ...],
    created_at: datetime,
) -> EmailEditorialReview:
    scope(plan, draft, *evidence)
    if len({row.check for row in evidence}) != len(evidence):
        refuse("duplicate_review_evidence")
    if any(
        row.draft != draft.binding() or row.created_at > created_at or row.valid_until <= created_at
        for row in evidence
    ):
        refuse("review_evidence_stale_or_wrong_draft")
    parser = _HTMLInspection()
    parser.feed(draft.html)
    parser.close()

    def normalize(value: str) -> str:
        return " ".join(value.split())

    declared = {item.name for item in draft.personalization}
    used = set(
        re.findall(
            r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}",
            draft.html + draft.plain_text + draft.subject + draft.preheader,
        )
    )
    unresolved = (
        "{{" in draft.html + draft.plain_text + draft.subject + draft.preheader
        or "}}" in draft.html + draft.plain_text + draft.subject + draft.preheader
    )
    cta_ok = draft.calls_to_action == plan.calls_to_action and all(
        cta.label in draft.plain_text and cta.label in "".join(parser.text)
        for cta in draft.calls_to_action
    )
    supplied = {item.check: item for item in evidence}
    structural = {
        "source_traceability": draft.source_lineage == plan.source_evidence,
        "audience_policy": draft.compliance == plan.compliance,
        "html_plain_text": normalize("".join(parser.text)) == normalize(draft.plain_text)
        and not parser.unsafe,
        "cta": cta_ok,
        "personalization": draft.personalization == plan.personalization
        and declared == used
        and (
            not unresolved
            or (
                bool(used)
                and re.sub(
                    r"\{\{\s*[a-z][a-z0-9_]*\s*\}\}",
                    "",
                    draft.html + draft.plain_text + draft.subject + draft.preheader,
                ).count("{")
                == 0
                and re.sub(
                    r"\{\{\s*[a-z][a-z0-9_]*\s*\}\}",
                    "",
                    draft.html + draft.plain_text + draft.subject + draft.preheader,
                ).count("}")
                == 0
                and "personalization" in supplied
                and supplied["personalization"].passed
            )
        ),
        "accessibility": not parser.unsafe and not parser.inaccessible,
        "footer_unsubscribe": draft.compliance.footer_text in draft.plain_text
        and draft.compliance.footer_text in "".join(parser.text),
        "consent_suppression": bool(
            plan.audience.consent_policy and plan.audience.suppression_policy
        )
        and draft.compliance.consent_policy == plan.audience.consent_policy
        and draft.compliance.suppression_policy == plan.audience.suppression_policy,
        "preview": plan.preview_required,
        "test_send": plan.test_send_required,
    }
    manifest_urls = {link.url for link in draft.links}
    links_match = (
        draft.links == plan.links
        and set(parser.links) <= manifest_urls
        and all(link.url in draft.plain_text for link in draft.links)
        and any(link.purpose == "unsubscribe" and link.url in parser.links for link in draft.links)
    )
    findings = []
    for check in REVIEW_CHECKS:
        if check == "links" and not links_match:
            status, reason = "blocked", "link_manifest_mismatch"
        elif check in structural:
            status = "pass" if structural[check] else "blocked"
            reason = "structural_check_passed" if structural[check] else "structural_check_failed"
        else:
            row = supplied.get(check)
            status = ("pass" if row.passed else "blocked") if row else "human_needed"
            reason = "supplied_review_evidence" if row else "semantic_or_external_evidence_required"
        # Negative evidence always overrides a structural pass.
        if check in supplied and not supplied[check].passed:
            status, reason = "blocked", "supplied_review_evidence_failed"
        findings.append(EmailReviewFinding(check=check, status=status, reason=reason))  # type: ignore[arg-type]
    return EmailEditorialReview(
        artifact_id=stable_id("email_review", draft.content_digest, canonical_digest(evidence)),
        created_at=created_at,
        organization_id=plan.organization_id,
        publication_id=plan.publication_id,
        input_refs=(plan.artifact_id, draft.artifact_id),
        plan=plan.binding(),
        draft=draft.binding(),
        findings=tuple(findings),
        evidence=evidence,
        ready_for_human_approval=all(row.status == "pass" for row in findings),
        generation=trace("review", plan, draft, evidence),
    )


def validate_snapshot(
    snapshot: AudienceSnapshotSummary, audience: AudienceIntent, at: datetime
) -> None:
    scope(audience, snapshot)
    if not snapshot.resolved_at <= at < snapshot.expires_at:
        refuse("audience_snapshot_expired_or_not_yet_resolved")
    if snapshot.drift_status != "unchanged" or snapshot.eligible_count == 0:
        refuse("audience_snapshot_drift_or_empty")
    if not audience.consent_policy or not audience.suppression_policy:
        refuse("consent_and_suppression_required")
    if (
        snapshot.audience_intent_digest != canonical_digest(audience)
        or snapshot.consent_policy_digest != audience.consent_policy.digest
        or snapshot.suppression_policy_digest != audience.suppression_policy.digest
    ):
        refuse("audience_snapshot_or_policy_changed")


def prepare_delivery(
    plan: EmailMessagePlan,
    draft: EmailMessageDraft,
    review: EmailEditorialReview,
    snapshot: AudienceSnapshotSummary,
    proofs: tuple[EmailProofReceipt, ...],
    created_at: datetime,
    schedule_intent: datetime | None = None,
    sequence: EmailSequencePlan | None = None,
) -> EmailDeliveryPackage:
    scope(plan, draft, review, snapshot, *proofs)
    if (
        draft.message_plan != plan.binding()
        or review.plan != plan.binding()
        or review.draft != draft.binding()
    ):
        refuse("delivery_input_binding_changed")
    validate_snapshot(snapshot, plan.audience, created_at)
    if schedule_intent is not None and not created_at < schedule_intent < snapshot.expires_at:
        refuse("schedule_must_be_future_and_within_snapshot_validity")
    if sequence:
        scope(plan, sequence)
        if sequence.campaign_or_lifecycle_program != plan.campaign or plan.binding() not in tuple(
            step.message_plan for step in sequence.steps
        ):
            refuse("sequence_does_not_bind_message_revision")
    if review.created_at > created_at:
        refuse("editorial_review_from_future")
    verified_review = _review_exact_message(plan, draft, review.evidence, created_at)
    if (
        not review.ready_for_human_approval
        or not verified_review.ready_for_human_approval
        or review.findings != verified_review.findings
    ):
        refuse("editorial_review_not_ready")
    if (
        draft.sender_identity != plan.sender_identity
        or draft.reply_to_identity != plan.reply_to_identity
    ):
        refuse("sender_identity_changed")
    if any(
        row.draft != draft.binding()
        or not row.successful
        or not row.personalization_resolved
        or not row.created_at <= created_at < row.valid_until
        for row in proofs
    ):
        refuse("preview_or_test_proof_invalid")
    if len({row.kind for row in proofs}) != len(proofs):
        refuse("duplicate_preview_or_test_proof")
    kinds = {row.kind for row in proofs}
    if snapshot.purpose == "production":
        if (plan.preview_required and "preview" not in kinds) or (
            plan.test_send_required and "test_send" not in kinds
        ):
            refuse("production_requires_preview_and_test_evidence")
        if any(
            row.audience_snapshot
            and (
                row.audience_snapshot.snapshot_ref == snapshot.snapshot_ref
                or row.audience_snapshot.snapshot_digest == snapshot.snapshot_digest
            )
            for row in proofs
        ):
            refuse("test_audience_must_differ_from_production")
    material = EmailDeliveryMaterial(
        organization_id=plan.organization_id,
        publication_id=plan.publication_id,
        draft=draft,
        html_digest=canonical_digest(draft.html),
        plain_text_digest=canonical_digest(draft.plain_text),
        link_manifest_digest=canonical_digest(draft.links),
        audience_snapshot=snapshot,
        tracking_policy=plan.tracking_policy,
        schedule_intent=schedule_intent,
        campaign=plan.campaign,
        sequence_revision=sequence.binding() if sequence else None,
        review=review,
        proofs=proofs,
    )
    digest = canonical_digest(material)
    return EmailDeliveryPackage(
        artifact_id=stable_id("email_delivery", digest),
        created_at=created_at,
        organization_id=plan.organization_id,
        publication_id=plan.publication_id,
        input_refs=(draft.artifact_id, review.artifact_id),
        material=material,
        approval_digest=digest,
    )


def propose_operation(
    material: EmailOperationIntent, created_at: datetime, idempotency_key: str
) -> ProposedEmailOperation:
    """Freeze editorial intent referencing a caller-selected public Zeocore operation.

    This function does not certify provider support, validate an authorization, or execute.
    The host must resolve the public operation contract and check its semantics before use.
    """
    current(material)
    if material.audience and (
        not material.audience.resolved_at <= created_at < material.audience.expires_at
        or material.audience.drift_status != "unchanged"
        or material.audience.eligible_count == 0
    ):
        refuse("effect_audience_snapshot_not_current")
    digest = canonical_digest(material)
    return ProposedEmailOperation(
        artifact_id=stable_id("email_operation", digest, idempotency_key),
        created_at=created_at,
        organization_id=material.organization_id,
        publication_id=material.publication_id,
        material=material,
        approval_digest=digest,
        idempotency_key=idempotency_key,
    )


def assess_program(
    campaign: EmailCampaignPlan,
    observations: tuple[EmailMetricObservation, ...],
    window: ResearchWindow,
    expected_metrics: tuple[str, ...],
    created_at: datetime,
) -> EmailProgramAssessment:
    scope(campaign, *observations)
    if len({row.artifact_id for row in observations}) != len(observations):
        refuse("duplicate_metric_observation")
    if any(
        row.campaign != campaign.binding() or row.observation_window != window
        for row in observations
    ):
        refuse("metrics_campaign_or_window_mismatch")
    if any(
        row.attribution_policy and row.attribution_policy != campaign.attribution_policy
        for row in observations
    ):
        refuse("metric_attribution_policy_mismatch")
    gaps = tuple(dict.fromkeys(gap for row in observations for gap in row.data_gaps))
    missing = set(expected_metrics) - {row.metric for row in observations}
    gaps += tuple(f"Missing metric: {metric}" for metric in sorted(missing))
    if not observations:
        gaps += ("No observations supplied.",)
    qualified = (
        bool(observations)
        and not gaps
        and all(
            row.completeness == "complete" and row.reliability == "qualified"
            for row in observations
        )
    )
    return EmailProgramAssessment(
        artifact_id=stable_id(
            "email_assessment",
            campaign.content_digest,
            canonical_digest(observations),
            canonical_digest(window),
        ),
        created_at=created_at,
        organization_id=campaign.organization_id,
        publication_id=campaign.publication_id,
        input_refs=(campaign.artifact_id, *(row.artifact_id for row in observations)),
        campaign=campaign.binding(),
        observation_window=window,
        observations=observations,
        completeness="complete" if qualified else "partial" if observations else "unknown",
        confidence="qualified" if qualified else "limited",
        conclusions=(
            "Observed aggregates are descriptive and do not establish causal lift or a winning variant.",
        ),
        data_gaps=gaps,
        hypotheses=(
            "Consider a separately reviewed future experiment after resolving coverage and attribution gaps.",
        ),
        generation=trace("assessment", campaign, observations, window, expected_metrics),
    )
