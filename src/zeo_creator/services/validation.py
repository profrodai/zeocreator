"""Deterministic Ducktyper delivery validation and approval binding."""

from datetime import datetime

from zeo_creator.contracts.common import canonical_digest, digest_is_current, stable_id
from zeo_creator.contracts.delivery import (
    DeliveryFinding,
    DeliveryReviewBundle,
    FindingSeverity,
    RenderedArtifact,
    RenderManifest,
)
from zeo_creator.contracts.distribution import ChannelPlan, PublicationPayload
from zeo_creator.contracts.ducktyper import DucktyperBrief, required_render_elements
from zeo_creator.contracts.evidence import ResearchSynthesis
from zeo_creator.contracts.publications import PublicationProfile


def proposed_payload(brief: DucktyperBrief) -> PublicationPayload:
    return PublicationPayload(
        title=brief.hook,
        caption=f"{brief.thesis}\n\n{brief.cta}",
        description=f"{brief.objective} — {brief.topic}",
        alt_text=f"{brief.deliverable_kind.value}: {brief.topic}",
    )


def approval_digest_for(
    *,
    brief: DucktyperBrief,
    artifact: RenderedArtifact,
    manifest: RenderManifest,
    channel_plan: ChannelPlan,
    payload: PublicationPayload,
) -> str:
    return canonical_digest(
        {
            "brief_id": brief.brief_id,
            "brief_content_digest": brief.content_digest,
            "content_revision": brief.content_revision,
            "artifact_ref": artifact.artifact_ref,
            "artifact_digest": artifact.artifact_digest,
            "manifest_id": manifest.manifest_id,
            "manifest_content_digest": manifest.content_digest,
            "channel_plan_content_digest": channel_plan.content_digest,
            "payload": payload.model_dump(mode="json"),
        }
    )


def validate_delivery_bundle(
    *,
    brief: DucktyperBrief,
    artifact: RenderedArtifact,
    manifest: RenderManifest,
    publication: PublicationProfile,
    synthesis: ResearchSynthesis,
    channel_plan: ChannelPlan,
    created_at: datetime,
    revision: int,
) -> DeliveryReviewBundle:
    findings: list[DeliveryFinding] = []

    def blocking(code: str, category: str, message: str) -> None:
        findings.append(
            DeliveryFinding(
                code=code,
                severity=FindingSeverity.BLOCKING,
                category=category,
                message=message,
            )
        )

    artifacts = (brief, artifact, manifest, publication, synthesis, channel_plan)
    if not all(digest_is_current(item) for item in artifacts):
        blocking("ZEO_CREATOR_STALE_DIGEST", "identity", "One or more contract digests are stale")

    scope = (brief.organization_id, brief.publication_id)
    identity_match = all(
        (item.organization_id, item.publication_id) == scope
        for item in (artifact, manifest, publication, synthesis, channel_plan)
    )
    identity_match = identity_match and all(
        (
            artifact.brief_id == brief.brief_id,
            manifest.brief_id == brief.brief_id,
            artifact.content_revision == brief.content_revision,
            manifest.content_revision == brief.content_revision,
            artifact.brief_content_digest == brief.content_digest,
            manifest.brief_content_digest == brief.content_digest,
            manifest.artifact_ref == artifact.artifact_ref,
            manifest.artifact_digest == artifact.artifact_digest,
        )
    )
    if not identity_match:
        blocking(
            "ZEO_CREATOR_RENDER_IDENTITY_MISMATCH", "identity", "Brief/render identity mismatch"
        )

    required = set(required_render_elements(brief))
    missing_elements = sorted(required.difference(manifest.included_elements))
    element_coverage = not missing_elements
    if missing_elements:
        blocking(
            "ZEO_CREATOR_MISSING_RENDER_ELEMENT",
            "coverage",
            f"Missing required render elements: {', '.join(missing_elements)}",
        )

    allowed_claim_ids = {claim.claim_id for claim in brief.evidence_claims}
    rendered_claim_ids = set(manifest.rendered_claim_ids)
    source_claim_traceability = rendered_claim_ids == allowed_claim_ids and all(
        set(claim.evidence_refs).issubset(synthesis.evidence_refs)
        for claim in brief.evidence_claims
    )
    if rendered_claim_ids.difference(allowed_claim_ids):
        blocking(
            "ZEO_CREATOR_UNSUPPORTED_CLAIM",
            "evidence",
            "Render manifest contains a claim absent from the accepted brief",
        )
    if allowed_claim_ids.difference(rendered_claim_ids):
        blocking(
            "ZEO_CREATOR_MISSING_CLAIM_TRACE",
            "evidence",
            "Accepted brief claims are missing from the render manifest",
        )

    brand_pass = manifest.brand_profile_ref == publication.reference
    if not brand_pass:
        blocking("ZEO_CREATOR_BRAND_MISMATCH", "brand", "Render used the wrong brand profile")
    rendered_text = artifact.extracted_text.casefold()
    prohibited = [claim for claim in brief.prohibited_claims if claim.casefold() in rendered_text]
    if prohibited:
        brand_pass = False
        blocking(
            "ZEO_CREATOR_PROHIBITED_CLAIM",
            "brand",
            f"Render contains prohibited claims: {', '.join(prohibited)}",
        )

    destination_channels = {item.channel for item in channel_plan.destinations}
    unsupported_destinations = destination_channels.difference(brief.target_channels)
    if unsupported_destinations:
        brand_pass = False
        blocking(
            "ZEO_CREATOR_DESTINATION_MISMATCH",
            "distribution",
            f"Unapproved destination channels: {', '.join(sorted(unsupported_destinations))}",
        )

    failed_checks = sorted(name for name, passed in manifest.technical_checks.items() if not passed)
    technical_pass = bool(manifest.technical_checks) and not failed_checks
    if not manifest.technical_checks:
        blocking(
            "ZEO_CREATOR_TECHNICAL_CHECKS_MISSING", "technical", "No technical checks supplied"
        )
    elif failed_checks:
        blocking(
            "ZEO_CREATOR_TECHNICAL_CHECK_FAILED",
            "technical",
            f"Failed technical checks: {', '.join(failed_checks)}",
        )

    payload = proposed_payload(brief)
    approval_digest = approval_digest_for(
        brief=brief,
        artifact=artifact,
        manifest=manifest,
        channel_plan=channel_plan,
        payload=payload,
    )
    return DeliveryReviewBundle(
        review_id=stable_id("review", brief.brief_id, artifact.artifact_digest, approval_digest),
        created_at=created_at,
        organization_id=brief.organization_id,
        publication_id=brief.publication_id,
        input_refs=(
            brief.brief_id,
            artifact.artifact_ref,
            manifest.manifest_id,
            publication.reference,
            synthesis.synthesis_id,
            channel_plan.channel_plan_id,
        ),
        revision=revision,
        brief_id=brief.brief_id,
        artifact_ref=artifact.artifact_ref,
        manifest_id=manifest.manifest_id,
        identity_match=identity_match,
        required_element_coverage=element_coverage,
        source_claim_traceability=source_claim_traceability,
        brand_constraints_pass=brand_pass,
        technical_delivery_pass=technical_pass,
        findings=tuple(findings),
        proposed_payload=payload,
        proposed_destinations=channel_plan.destinations,
        approval_digest=approval_digest,
        ready_for_approval=not any(item.severity == FindingSeverity.BLOCKING for item in findings),
    )
