"""Sanitized caller inputs for three isolated publications; no private brand strategy."""

from datetime import UTC, datetime, timedelta
from typing import Literal

from zeo_core.contracts import CapabilityId

from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.email_marketing import (
    AudienceIntent,
    AudienceSnapshotSummary,
    EmailArtifactRef,
    EmailCampaignPlan,
    EmailCampaignRelease,
    EmailCompliance,
    EmailCTA,
    EmailEffectIntent,
    EmailExecutionContext,
    EmailLink,
    EmailLoweringEvidence,
    EmailMessageDraft,
    EmailMessagePlan,
    EmailProofReceipt,
    EmailRemoteReceipt,
    EmailReviewCheck,
    EmailReviewEvidence,
)
from zeo_creator.contracts.evidence import ResearchWindow
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.services.email_marketing import (
    EmailCampaignBrief,
    EmailMessageDirections,
    EmailSequencePolicies,
    EmailSourceSection,
    compose_message,
    finalize_campaign,
    plan_campaign,
    plan_message,
)

NOW = datetime(2026, 9, 7, 12, tzinfo=UTC)
LATER = NOW + timedelta(days=1)


def profile(publication: str = "publication-a") -> PublicationProfile:
    return PublicationProfile(
        profile_id=f"{publication}/profile",
        created_at=NOW,
        organization_id="example-org",
        publication_id=publication,
        display_name=f"Example {publication}",
        audience_definition="Consented learners",
        editorial_pillars=("Practical education",),
        voice_rules=("Evidence before claims",),
        style_ref=f"{publication}/style",
        default_channels=("email",),
        cta_policy="One explicit primary action",
        approval_policy_ref=f"{publication}/approval",
    )


def ref(name: str, publication: str = "publication-a") -> EmailArtifactRef:
    return EmailArtifactRef(
        organization_id="example-org",
        publication_id=publication,
        ref=f"{publication}/{name}",
        revision=1,
        digest=canonical_digest([publication, name, 1]),
    )


def audience(publication: str = "publication-a") -> AudienceIntent:
    return AudienceIntent(
        organization_id="example-org",
        publication_id=publication,
        segment_refs=(f"{publication}/consented-learners",),
        consent_policy=ref("consent", publication),
        suppression_policy=ref("suppression", publication),
        frequency_cap_policy=ref("frequency", publication),
        purpose_of_contact="Requested education",
        cross_publication_use_policy=ref("no-audience-sharing", publication),
    )


def ctas() -> tuple[EmailCTA, ...]:
    return (
        EmailCTA(
            cta_id="learn",
            link_id="guide",
            label="Read the guide",
            desired_action="Read",
            primary=True,
        ),
    )


def brief(publication: str = "publication-a") -> EmailCampaignBrief:
    return EmailCampaignBrief(
        organization_id="example-org",
        publication_id=publication,
        campaign_id=f"{publication}/education-campaign",
        objective="Help learners apply one capability",
        audience=audience(publication),
        window=ResearchWindow(starts_at=NOW, ends_at=NOW + timedelta(days=30)),
        calls_to_action=ctas(),
        conversion_objectives=(ref("learning-conversion", publication),),
        attribution_policy=ref("attribution", publication),
        tracking_policy=ref("tracking", publication),
        stopping_conditions=("Stop on withdrawn consent or the declared campaign end.",),
    )


def campaign(publication: str = "publication-a") -> EmailCampaignPlan:
    return plan_campaign(profile(publication), brief(publication), NOW)


def directions(
    publication: str = "publication-a", message: str = "newsletter"
) -> EmailMessageDirections:
    return EmailMessageDirections(
        organization_id="example-org",
        publication_id=publication,
        message_id=f"{publication}/{message}",
        purpose="Explain one useful capability",
        objective="Support learning",
        lifecycle_stage="consented-learner",
        subject="A practical capability",
        preheader="Try the example",
        sections=("The capability",),
        links=(
            EmailLink(
                link_id="guide",
                url="https://example.org/guide",
                purpose="cta",
                tracking_required=True,
            ),
            EmailLink(
                link_id="unsubscribe",
                url="https://example.org/preferences",
                purpose="unsubscribe",
                tracking_required=False,
            ),
        ),
        calls_to_action=ctas(),
        sender=ref("sender", publication),
        reply_to=ref("reply-to", publication),
        compliance=EmailCompliance(
            organization_id="example-org",
            publication_id=publication,
            footer_policy=ref("footer", publication),
            unsubscribe_policy=ref("unsubscribe", publication),
            consent_policy=ref("consent", publication),
            suppression_policy=ref("suppression", publication),
            footer_text="Example publication. You requested this educational update.",
            unsubscribe_link_id="unsubscribe",
        ),
        sources=(ref("source-one", publication),),
        brand_policy=ref("brand", publication),
        voice_policy=ref("voice", publication),
        accessibility=("Readable text and descriptive links",),
    )


def plan(publication: str = "publication-a", message: str = "newsletter") -> EmailMessagePlan:
    return plan_message(
        profile(publication), campaign(publication), directions(publication, message), NOW
    )


def sections(publication: str = "publication-a") -> tuple[EmailSourceSection, ...]:
    return (
        EmailSourceSection(
            organization_id="example-org",
            publication_id=publication,
            heading="The capability",
            text="Use explicit inputs and inspect the result before approving an action.",
            evidence=(ref("source-one", publication),),
        ),
    )


def draft(publication: str = "publication-a") -> EmailMessageDraft:
    return compose_message(plan(publication), sections(publication), NOW)


def policies(publication: str = "publication-a") -> EmailSequencePolicies:
    return EmailSequencePolicies(
        organization_id="example-org",
        publication_id=publication,
        entry=ref("entry", publication),
        exit=ref("exit", publication),
        conversion=ref("conversion", publication),
        suppression=ref("suppression", publication),
        send_window=ref("send-window", publication),
        quiet_hours=ref("quiet-hours", publication),
        time_zone=ref("time-zone", publication),
        skip=ref("skip", publication),
        freshness_max_age_seconds=86400,
    )


def snapshot(
    publication: str = "publication-a", purpose: Literal["production", "test"] = "production"
) -> AudienceSnapshotSummary:
    return AudienceSnapshotSummary(
        organization_id="example-org",
        publication_id=publication,
        snapshot_ref=f"{publication}/{purpose}-snapshot",
        snapshot_digest=canonical_digest([publication, purpose, "snapshot"]),
        provider_kind="hubspot-marketing" if publication == "publication-a" else "kit",
        connection_ref=f"{publication}/connection",
        audience_intent_digest=canonical_digest(audience(publication)),
        eligible_count=10 if purpose == "production" else 1,
        suppressed_count=2,
        resolved_at=NOW,
        expires_at=LATER,
        segment_definition_digest=canonical_digest([publication, "segment"]),
        consent_policy_digest=ref("consent", publication).digest,
        suppression_policy_digest=ref("suppression", publication).digest,
        drift_status="unchanged",
        purpose=purpose,
    )


def evidence(item: EmailMessageDraft) -> tuple[EmailReviewEvidence, ...]:
    checks: tuple[EmailReviewCheck, ...] = (
        "publication_voice",
        "subject_body",
        "links",
        "claims",
        "accessibility",
    )
    return tuple(
        EmailReviewEvidence(
            artifact_id=f"{item.publication_id}/simulated-review/{check}",
            created_at=NOW,
            organization_id=item.organization_id,
            publication_id=item.publication_id,
            draft=item.binding(),
            check=check,
            passed=True,
            policy=ref(f"review-{check}", item.publication_id),
            receipt=ref(f"simulated-evidence/{check}", item.publication_id),
            issuer=ref("simulated-reviewer", item.publication_id),
            valid_until=LATER,
        )
        for check in checks
    )


def proofs(
    item: EmailMessageDraft, purpose: Literal["production", "test"] = "production"
) -> tuple[EmailProofReceipt, ...]:
    kinds: tuple[Literal["preview", "test_send"], ...] = ("preview", "test_send")
    return tuple(
        EmailProofReceipt(
            artifact_id=f"{item.publication_id}/simulated-proof/{kind}",
            created_at=NOW,
            organization_id=item.organization_id,
            publication_id=item.publication_id,
            draft=item.binding(),
            kind=kind,
            lowering=lowering_evidence(item, "test" if kind == "test_send" else purpose),
            audience_snapshot=snapshot(item.publication_id, "test")
            if kind == "test_send"
            else None,
            personalization_resolved=True,
            successful=True,
            valid_until=LATER,
        )
        for kind in kinds
    )


def execution(publication: str = "publication-a") -> EmailExecutionContext:
    snap = snapshot(publication)
    return EmailExecutionContext(
        organization_id="example-org",
        publication_id=publication,
        provider_kind=snap.provider_kind,
        connection_ref=snap.connection_ref,
        account_ref=f"{publication}/account",
        connector_revision="simulation-2",
        lowering_profile=ref("simulated-lowering-profile", publication),
    )


def mapping_digest(publication: str = "publication-a") -> str:
    return canonical_digest([publication, "simulated-template-mapping"])


def release(publication: str = "publication-a") -> EmailCampaignRelease:
    return finalize_campaign(campaign(publication), (plan(publication),), (), NOW)


def lowering_evidence(
    item: EmailMessageDraft, purpose: Literal["production", "test"] = "production"
) -> EmailLoweringEvidence:
    # This fixture has no renderer or subscriber values; it cannot certify tokens.
    if item.personalization or "{{" in item.html + item.plain_text + item.subject + item.preheader:
        raise ValueError("simulation cannot render personalization")
    pub = item.publication_id
    payload = canonical_digest((item.html, item.plain_text, item.subject, item.preheader))
    return EmailLoweringEvidence(
        artifact_id=f"{pub}/simulated-lowering/{purpose}",
        created_at=NOW,
        organization_id=item.organization_id,
        publication_id=pub,
        receipt=ref(f"simulated-lowering-receipt/{purpose}", pub),
        issuer=ref("simulated-connector", pub),
        receipt_contract=CapabilityId(
            namespace="example.email", name="lowering_receipt", version="2.0.0"
        ),
        receipt_contract_digest=canonical_digest("simulated-lowering-receipt-v2"),
        execution=execution(pub),
        draft=item.binding(),
        sender_identity=item.sender_identity,
        template_mapping_digest=mapping_digest(pub),
        submitted_payload_digest=payload,
        observed_payload_digest=payload,
        rendered_preview_digest=canonical_digest(item.html),
        covered_snapshot_digest=snapshot(pub, purpose).snapshot_digest,
        outcome="verified",
    )


def remote_receipt(
    operation: EmailArtifactRef,
    campaign_release: EmailArtifactRef,
    *,
    kind: Literal[
        "draft",
        "scheduled_broadcast",
        "sequence_revision",
        "broadcast",
        "test_send",
        "cancelled_broadcast",
    ] = "broadcast",
    sequence: EmailArtifactRef | None = None,
    intent: EmailEffectIntent | None = None,
    audience: AudienceSnapshotSummary | None = None,
) -> EmailRemoteReceipt:
    """Supplied synthetic evidence only; production normalization uses actual proposals."""
    pub = operation.publication_id
    intent = (
        intent
        or {
            "draft": EmailEffectIntent.CREATE_DRAFT,
            "scheduled_broadcast": EmailEffectIntent.SCHEDULE,
            "broadcast": EmailEffectIntent.SEND,
            "test_send": EmailEffectIntent.TEST,
            "cancelled_broadcast": EmailEffectIntent.CANCEL,
            "sequence_revision": EmailEffectIntent.PROVISION,
        }[kind]
    )
    result: dict[str, object] = dict(
        kind=kind, intent=intent, organization_id=operation.organization_id, publication_id=pub
    )
    if kind == "sequence_revision":
        result.update(
            sequence=sequence,
            lifecycle_state={
                EmailEffectIntent.PROVISION: "provisioned",
                EmailEffectIntent.ACTIVATE: "active",
                EmailEffectIntent.ENROL: "active",
                EmailEffectIntent.PAUSE: "paused",
                EmailEffectIntent.RETIRE: "retired",
                EmailEffectIntent.MIGRATE: "provisioned",
            }[intent],
            audience=audience,
        )
    else:
        result.update(
            delivery=ref("simulated-delivery", pub),
            message_plan=plan(pub).binding(),
            audience=audience or snapshot(pub, "test" if kind == "test_send" else "production"),
        )
    return EmailRemoteReceipt.model_validate(
        dict(
            artifact_id=f"{pub}/simulated-receipt/{operation.digest[7:23]}",
            created_at=NOW,
            organization_id=operation.organization_id,
            publication_id=pub,
            operation=operation,
            result=result,
            campaign_release=campaign_release,
            execution=execution(pub),
            issuer=ref("simulated-connector", pub),
            receipt_contract=CapabilityId(
                namespace="example.email", name="remote_receipt", version="4.0.0"
            ),
            receipt_contract_digest=canonical_digest("simulated-remote-receipt-v4"),
            remote_ref=f"{pub}/simulated-remote/{operation.digest[7:23]}",
            remote_revision_digest=canonical_digest(operation),
            outcome="confirmed",
        )
    )


def proposal_request() -> dict[str, object]:
    from zeo_creator.contracts.email_marketing import EmailEffectIntent, EmailOperationIntent
    from zeo_creator.reference.email_simulation import operation_contract_digest, operation_identity
    from zeo_creator.services.email_marketing import prepare_delivery, review_message

    item = draft()
    released = release()
    package = prepare_delivery(
        plan(),
        item,
        review_message(profile(), plan(), item, evidence(item), NOW),
        snapshot(),
        proofs(item),
        NOW,
        release=released,
        execution=execution(),
        template_mapping_digest=mapping_digest(),
    )
    intent = EmailEffectIntent.CREATE_DRAFT
    material = EmailOperationIntent(
        organization_id=item.organization_id,
        publication_id=item.publication_id,
        execution=execution(),
        campaign_release=released.binding(),
        intent=intent,
        operation=operation_identity(intent),
        operation_contract_digest=operation_contract_digest(intent),
        delivery=package.binding(),
        delivery_approval_digest=package.approval_digest,
    )
    return dict(
        material=material.model_dump(mode="json"),
        release=released.model_dump(mode="json"),
        package=package.model_dump(mode="json"),
        idempotency_key="example-draft",
        created_at=NOW.isoformat(),
    )
