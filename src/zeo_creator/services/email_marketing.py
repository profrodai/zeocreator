"""Input-only email transformations and conservative deterministic reference strategy."""

from __future__ import annotations

import re
from datetime import datetime
from html import escape
from html.parser import HTMLParser
from typing import Never, Protocol

from pydantic import BaseModel, Field, ValidationError

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
    EmailCampaignRelease,
    EmailCompliance,
    EmailCTA,
    EmailDeliveryMaterial,
    EmailDeliveryPackage,
    EmailEditorialReview,
    EmailEffectIntent,
    EmailExecutionContext,
    EmailLink,
    EmailMeasurementPopulation,
    EmailMessageDraft,
    EmailMessagePlan,
    EmailMetricName,
    EmailMetricObservation,
    EmailOperationIntent,
    EmailProgramAssessment,
    EmailProofReceipt,
    EmailRemoteReceipt,
    EmailReviewEvidence,
    EmailReviewFinding,
    EmailSequencePlan,
    EmailSequenceStepPlan,
    EmailStoppingConditionFinding,
    OpaqueRef,
    PersonalizationDeclaration,
    ProposedEmailOperation,
    ScopedEmailModel,
    Text,
    effect_approval_digest,
    metric_conflicts,
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
        if isinstance(item, BaseModel):
            try:
                payload = item.model_dump_json(warnings="error")
            except Exception:
                refuse("stale_email_artifact")
            if isinstance(item, DurableArtifact) and not digest_is_current(item):
                refuse("stale_email_artifact")
            try:
                validated = type(item).model_validate_json(payload)
            except ValidationError:
                refuse("stale_email_artifact")
            # Pydantic validates the entire nested graph once. Reject silent repairs too.
            if validated.model_dump_json() != payload:
                refuse("stale_email_artifact")
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
            desired_audience_action=next(
                cta.desired_action for cta in message.calls_to_action if cta.primary
            ),
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
        self.anchors: list[tuple[str, str]] = []
        self.active_anchor: tuple[str, list[str]] | None = None

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
            href = attributes.get("href") or ""
            self.links.append(href)
            if self.active_anchor is not None:
                self.unsafe = True
            self.active_anchor = (href, [])
        if tag in {"p", "h1", "h2", "h3", "li", "br", "footer", "div"}:
            self.text.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.active_anchor is not None:
            href, text = self.active_anchor
            label = " ".join("".join(text).split())
            self.anchors.append((label, href))
            if not label:
                self.inaccessible = True
            self.active_anchor = None
        if tag in {"p", "h1", "h2", "h3", "li", "footer", "div"}:
            self.text.append(" ")

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self.active_anchor is not None:
            self.active_anchor[1].append(data)


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
    links = {link.link_id: link for link in draft.links}
    cta_ok = draft.calls_to_action == plan.calls_to_action and all(
        f"{cta.label} {links[cta.link_id].url}" in draft.plain_text
        and (normalize(cta.label), links[cta.link_id].url) in parser.anchors
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
                and supplied["personalization"].lowering is not None
                and supplied["personalization"].lowering.draft == draft.binding()
                and supplied["personalization"].lowering.outcome == "verified"
                and set(supplied["personalization"].lowering.covered_tokens) == declared
            )
        ),
        "footer_unsubscribe": draft.compliance.footer_text in draft.plain_text
        and draft.compliance.footer_text in "".join(parser.text)
        and ("Unsubscribe", links[draft.compliance.unsubscribe_link_id].url) in parser.anchors
        and f"Unsubscribe {links[draft.compliance.unsubscribe_link_id].url}" in draft.plain_text,
        "consent_suppression": bool(
            plan.audience.consent_policy and plan.audience.suppression_policy
        )
        and draft.compliance.consent_policy == plan.audience.consent_policy
        and draft.compliance.suppression_policy == plan.audience.suppression_policy,
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
        elif check == "accessibility" and (parser.unsafe or parser.inaccessible):
            status, reason = "blocked", "accessibility_structure_failed"
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
    *,
    release: EmailCampaignRelease,
    execution: EmailExecutionContext,
    template_mapping_digest: str,
) -> EmailDeliveryPackage:
    scope(plan, draft, review, snapshot, release, execution, *proofs)
    if plan not in release.messages or release.campaign.binding() != plan.campaign:
        refuse("delivery_not_in_campaign_release")
    if sequence and sequence not in release.sequences:
        refuse("sequence_not_in_campaign_release")
    if (snapshot.provider_kind, snapshot.connection_ref) != (
        execution.provider_kind,
        execution.connection_ref,
    ):
        refuse("delivery_execution_snapshot_mismatch")
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
    if plan.preview_required and "preview" not in kinds:
        refuse("production_requires_preview_and_test_evidence")
    if snapshot.purpose == "production":
        if (plan.preview_required and "preview" not in kinds) or (
            plan.test_send_required and "test_send" not in kinds
        ):
            refuse("production_requires_preview_and_test_evidence")
        if any(
            row.kind == "test_send"
            and row.audience_snapshot
            and (
                row.audience_snapshot.snapshot_ref == snapshot.snapshot_ref
                or row.audience_snapshot.snapshot_digest == snapshot.snapshot_digest
            )
            for row in proofs
        ):
            refuse("test_audience_must_differ_from_production")
    for row in review.evidence:
        if row.check == "personalization" and row.lowering is not None:
            lowering = row.lowering
            if (
                lowering.execution != execution
                or lowering.template_mapping_digest != template_mapping_digest
                or lowering.sender_identity != draft.sender_identity
                or lowering.covered_snapshot_digest != snapshot.snapshot_digest
            ):
                refuse("proof_lowering_provenance_mismatch")
    for proof in proofs:
        evidence = proof.lowering
        covered = proof.audience_snapshot or snapshot
        validate_snapshot(covered, plan.audience, created_at)
        if (
            evidence.execution != execution
            or evidence.draft != draft.binding()
            or evidence.sender_identity != draft.sender_identity
            or evidence.template_mapping_digest != template_mapping_digest
            or evidence.covered_snapshot_digest != covered.snapshot_digest
            or set(evidence.covered_tokens) != {token.name for token in draft.personalization}
            or evidence.outcome != "verified"
            or evidence.created_at > created_at
            or (covered.provider_kind, covered.connection_ref)
            != (execution.provider_kind, execution.connection_ref)
        ):
            refuse("proof_lowering_provenance_mismatch")
        if proof.kind == "preview" and covered != snapshot:
            refuse("preview_must_cover_delivery_snapshot")
    material = EmailDeliveryMaterial(
        campaign_release=release.binding(),
        execution=execution,
        template_mapping_digest=template_mapping_digest,
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


def finalize_campaign(
    campaign: EmailCampaignPlan,
    messages: tuple[EmailMessagePlan, ...],
    sequences: tuple[EmailSequencePlan, ...],
    created_at: datetime,
) -> EmailCampaignRelease:
    scope(campaign, *messages, *sequences)
    return EmailCampaignRelease(
        artifact_id=stable_id(
            "email_release", campaign.content_digest, canonical_digest((messages, sequences))
        ),
        created_at=created_at,
        organization_id=campaign.organization_id,
        publication_id=campaign.publication_id,
        campaign=campaign,
        messages=messages,
        sequences=sequences,
        calls_to_action=tuple(
            dict.fromkeys(cta for row in messages for cta in row.calls_to_action)
        ),
        measurement_plan=campaign.conversion_objectives,
        generation=trace("release", campaign, messages, sequences),
    )


def propose_operation(
    material: EmailOperationIntent,
    created_at: datetime,
    idempotency_key: str,
    *,
    release: EmailCampaignRelease,
    package: EmailDeliveryPackage | None = None,
    sequence: EmailSequencePlan | None = None,
    source_sequence: EmailSequencePlan | None = None,
    originating_operation: ProposedEmailOperation | None = None,
) -> ProposedEmailOperation:
    """Validate concrete inputs before freezing intent. Host verifies receipt authenticity."""
    scope(material, release)
    if material.campaign_release != release.binding():
        refuse("effect_campaign_release_mismatch")
    if material.intent in {EmailEffectIntent.CANCEL, EmailEffectIntent.UPDATE_DRAFT}:
        if originating_operation is None:
            refuse("originating_operation_required")
        scope(material, originating_operation)
        original = originating_operation.material
        expected_kinds = (
            {EmailEffectIntent.SCHEDULE}
            if material.intent == EmailEffectIntent.CANCEL
            else {EmailEffectIntent.CREATE_DRAFT, EmailEffectIntent.UPDATE_DRAFT}
        )
        if (
            material.originating_operation != originating_operation.binding()
            or material.prior_receipt is None
            or material.prior_receipt.operation != originating_operation.binding()
            or original.delivery != material.target_delivery
            or original.execution != material.execution
            or original.campaign_release != material.campaign_release
            or original.intent not in expected_kinds
        ):
            refuse("originating_operation_target_mismatch")
        if material.prior_receipt.result.intent != original.intent:
            refuse("originating_operation_effect_mismatch")
        if material.intent == EmailEffectIntent.UPDATE_DRAFT and (
            package is None
            or material.prior_receipt.message_plan is None
            or package.material.draft.message_plan.ref != material.prior_receipt.message_plan.ref
        ):
            refuse("draft_update_message_target_mismatch")
    elif originating_operation is not None:
        refuse("unexpected_originating_operation")
    if material.audience:
        validate_snapshot(material.audience, release.campaign.audience, created_at)
        if (material.audience.provider_kind, material.audience.connection_ref) != (
            material.execution.provider_kind,
            material.execution.connection_ref,
        ):
            refuse("effect_execution_snapshot_mismatch")
    if material.delivery:
        if package is None:
            refuse("effect_delivery_package_required")
        scope(material, package)
        pm = package.material
        if (
            package.binding() != material.delivery
            or package.approval_digest != material.delivery_approval_digest
            or pm.execution != material.execution
            or pm.campaign_release != release.binding()
            or (material.audience is not None and pm.audience_snapshot != material.audience)
        ):
            refuse("effect_delivery_or_audience_changed")
        plans = [row for row in release.messages if row.binding() == pm.draft.message_plan]
        if len(plans) != 1:
            refuse("delivery_not_in_campaign_release")
        package_sequence = next(
            (row for row in release.sequences if row.binding() == pm.sequence_revision), None
        )
        if pm.sequence_revision and package_sequence is None:
            refuse("sequence_not_in_campaign_release")
        if material.intent != EmailEffectIntent.CANCEL:
            # Re-run preparation against actual material; a forged digest is not proof of readiness.
            prepare_delivery(
                plans[0],
                pm.draft,
                pm.review,
                pm.audience_snapshot,
                pm.proofs,
                created_at,
                pm.schedule_intent,
                package_sequence,
                release=release,
                execution=pm.execution,
                template_mapping_digest=pm.template_mapping_digest,
            )
        if material.intent == EmailEffectIntent.TEST and pm.audience_snapshot.purpose != "test":
            refuse("test_requires_test_delivery")
        if (
            material.intent in {EmailEffectIntent.SEND, EmailEffectIntent.SCHEDULE}
            and pm.audience_snapshot.purpose != "production"
        ):
            refuse("production_requires_production_delivery")
        if material.intent == EmailEffectIntent.SCHEDULE and (
            pm.schedule_intent is None or pm.schedule_intent <= created_at
        ):
            refuse("schedule_requires_future_delivery")
        if material.intent == EmailEffectIntent.SEND and pm.schedule_intent is not None:
            refuse("immediate_send_cannot_reuse_schedule")
    elif package is not None:
        refuse("unexpected_effect_delivery")
    if material.sequence:
        if sequence is None:
            refuse("effect_sequence_required")
        scope(material, sequence)
        if sequence.binding() != material.sequence or sequence not in release.sequences:
            refuse("effect_sequence_release_mismatch")
        if material.intent in {EmailEffectIntent.ENROL, EmailEffectIntent.MIGRATE}:
            window = sequence.maximum_enrolment_window
            if not window.starts_at <= created_at < window.ends_at or (
                material.audience is not None
                and not window.starts_at <= material.audience.resolved_at < window.ends_at
            ):
                refuse("sequence_enrolment_window_closed")
            if sequence.suppression_policy != release.campaign.audience.suppression_policy:
                refuse("sequence_audience_policy_mismatch")
    elif sequence is not None:
        refuse("unexpected_effect_sequence")
    if material.intent == EmailEffectIntent.MIGRATE:
        migration = material.migration
        if source_sequence is None or sequence is None or migration is None:
            refuse("migration_requires_both_sequence_revisions")
        scope(material, source_sequence)
        if (
            migration.source_sequence != source_sequence.binding()
            or source_sequence.binding() == sequence.binding()
            or sequence.previous_revision != source_sequence.binding()
            or sequence.migration_policy != migration.policy
            or material.prior_receipt is None
            or material.prior_receipt.sequence != source_sequence.binding()
            or material.prior_receipt.kind != "sequence_revision"
        ):
            refuse("migration_sequence_provenance_mismatch")
        if {step.source_step for step in migration.steps} != {
            step.step_id for step in source_sequence.steps
        } or len(migration.steps) != len(source_sequence.steps):
            refuse("migration_requires_every_source_step_once")
        targets = {step.step_id for step in sequence.steps}
        if any(
            (step.disposition == "skip" and step.target_step is not None)
            or (step.disposition != "skip" and step.target_step not in targets)
            for step in migration.steps
        ):
            refuse("migration_step_target_mismatch")
    elif source_sequence is not None:
        refuse("unexpected_migration_source")
    digest = effect_approval_digest(material, idempotency_key)
    return ProposedEmailOperation(
        artifact_id=stable_id("email_operation", digest),
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
    expected_metrics: tuple[EmailMetricName, ...],
    created_at: datetime,
    *,
    release: EmailCampaignRelease,
    expected_operations: tuple[EmailRemoteReceipt, ...],
) -> EmailProgramAssessment:
    scope(campaign, release, *observations)
    if release.campaign != campaign:
        refuse("assessment_campaign_release_mismatch")
    if len({row.artifact_id for row in observations}) != len(observations):
        refuse("duplicate_metric_observation")
    if any(
        row.campaign != campaign.binding()
        or row.campaign_release != release.binding()
        or row.observation_window != window
        for row in observations
    ):
        refuse("metrics_campaign_or_window_mismatch")
    if any(
        row.attribution_policy and row.attribution_policy != campaign.attribution_policy
        for row in observations
    ):
        refuse("metric_attribution_policy_mismatch")
    population = EmailMeasurementPopulation(
        organization_id=campaign.organization_id,
        publication_id=campaign.publication_id,
        release=release,
        operations=expected_operations,
    )
    if any(row.operation_receipt not in expected_operations for row in observations):
        refuse("observation_not_in_expected_population")
    gaps = tuple(
        dict.fromkeys(gap for row in observations for gap in row.data_gaps)
    ) + population.gaps(observations, expected_metrics)
    missing = set(expected_metrics) - {row.metric for row in observations}
    gaps += tuple(f"Missing metric: {metric}" for metric in sorted(missing))
    if not observations:
        gaps += ("No observations supplied.",)
    if metric_conflicts(observations):
        gaps += ("Conflicting values for the same metric and operation; no aggregation performed.",)
    qualified = (
        bool(observations)
        and not gaps
        and all(
            row.completeness == "complete" and row.reliability == "qualified"
            for row in observations
        )
    )
    return EmailProgramAssessment(
        campaign_release=release.binding(),
        population=population,
        expected_metrics=expected_metrics,
        stopping_conditions=tuple(
            EmailStoppingConditionFinding(condition=condition)
            for condition in campaign.stopping_conditions
        ),
        artifact_id=stable_id(
            "email_assessment",
            campaign.content_digest,
            canonical_digest(observations),
            canonical_digest((window, expected_metrics, population)),
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
            *(
                f"{row.metric}: {row.value:g} {row.unit}; coverage {row.coverage:.0%}; reliability {row.reliability}."
                for row in observations
            ),
            "Observed aggregates are descriptive and do not establish causal lift or a winning variant.",
        ),
        data_gaps=gaps,
        hypotheses=(
            "Consider a separately reviewed future experiment after resolving coverage and attribution gaps.",
        ),
        generation=trace(
            "assessment", campaign, observations, window, expected_metrics, population
        ),
    )


PUBLIC_REFUSAL_REASONS: frozenset[str] = frozenset(
    (
        "originating_operation_required",
        "originating_operation_target_mismatch",
        "originating_operation_effect_mismatch",
        "draft_update_message_target_mismatch",
        "unexpected_originating_operation",
        "observation_not_in_expected_population",
        "assessment_campaign_release_mismatch",
        "audience_snapshot_drift_or_empty",
        "audience_snapshot_expired_or_not_yet_resolved",
        "audience_snapshot_or_policy_changed",
        "campaign_profile_revision_changed",
        "campaign_requires_one_primary_cta",
        "consent_and_suppression_required",
        "delivery_execution_snapshot_mismatch",
        "delivery_input_binding_changed",
        "delivery_not_in_campaign_release",
        "duplicate_metric_observation",
        "duplicate_preview_or_test_proof",
        "duplicate_review_evidence",
        "editorial_review_from_future",
        "editorial_review_not_ready",
        "effect_campaign_release_mismatch",
        "effect_delivery_or_audience_changed",
        "effect_delivery_package_required",
        "effect_execution_snapshot_mismatch",
        "effect_sequence_release_mismatch",
        "effect_sequence_required",
        "email_publication_scope_mismatch",
        "immediate_send_cannot_reuse_schedule",
        "message_compliance_must_match_audience",
        "metric_attribution_policy_mismatch",
        "metrics_campaign_or_window_mismatch",
        "migration_requires_both_sequence_revisions",
        "migration_requires_every_source_step_once",
        "migration_sequence_provenance_mismatch",
        "migration_step_target_mismatch",
        "newsletter_audience_requires_explicit_migration",
        "newsletter_directions_must_select_existing_variants",
        "preview_must_cover_delivery_snapshot",
        "preview_or_test_proof_invalid",
        "production_requires_preview_and_test_evidence",
        "production_requires_production_delivery",
        "proof_lowering_provenance_mismatch",
        "review_evidence_stale_or_wrong_draft",
        "review_plan_or_profile_changed",
        "schedule_must_be_future_and_within_snapshot_validity",
        "schedule_requires_future_delivery",
        "sender_identity_changed",
        "sequence_audience_policy_mismatch",
        "sequence_does_not_bind_message_revision",
        "sequence_enrolment_window_closed",
        "sequence_messages_must_match_campaign_revision",
        "sequence_not_in_campaign_release",
        "sequence_predecessor_identity_mismatch",
        "sequence_requires_one_delay_per_message",
        "sequence_requires_unique_message_identities",
        "source_section_evidence_not_in_plan",
        "source_sections_must_match_plan_order",
        "stale_email_artifact",
        "strategy_output_does_not_bind_exact_inputs",
        "test_audience_must_differ_from_production",
        "test_requires_test_delivery",
        "unexpected_effect_delivery",
        "unexpected_effect_sequence",
        "unexpected_migration_source",
    )
)
