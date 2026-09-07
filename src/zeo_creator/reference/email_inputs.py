"""Sanitized caller inputs for three isolated publications; no private brand strategy."""

from datetime import UTC, datetime, timedelta
from typing import Literal

from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.email_marketing import (
    AudienceIntent,
    AudienceSnapshotSummary,
    EmailArtifactRef,
    EmailCampaignPlan,
    EmailCompliance,
    EmailCTA,
    EmailLink,
    EmailMessageDraft,
    EmailMessagePlan,
    EmailProofReceipt,
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
    checks: tuple[EmailReviewCheck, ...] = ("publication_voice", "subject_body", "links", "claims")
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
            receipt_ref=f"{item.publication_id}/simulated-evidence/{check}",
            valid_until=LATER,
        )
        for check in checks
    )


def proofs(item: EmailMessageDraft) -> tuple[EmailProofReceipt, ...]:
    kinds: tuple[Literal["preview", "test_send"], ...] = ("preview", "test_send")
    return tuple(
        EmailProofReceipt(
            artifact_id=f"{item.publication_id}/simulated-proof/{kind}",
            created_at=NOW,
            organization_id=item.organization_id,
            publication_id=item.publication_id,
            draft=item.binding(),
            kind=kind,
            receipt_ref=f"{item.publication_id}/simulated-{kind}",
            audience_snapshot=snapshot(item.publication_id, "test")
            if kind == "test_send"
            else None,
            personalization_resolved=True,
            successful=True,
            valid_until=LATER,
        )
        for kind in kinds
    )
