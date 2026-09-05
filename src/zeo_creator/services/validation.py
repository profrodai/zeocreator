"""Producer-neutral artifact validation and approval binding."""

from datetime import datetime

from zeo_creator.contracts.common import canonical_digest, digest_is_current, stable_id
from zeo_creator.contracts.delivery import (
    ArtifactManifest,
    DeliveryFinding,
    DeliveryReviewBundle,
    FindingSeverity,
)
from zeo_creator.contracts.distribution import ChannelPlan, PublicationPayload
from zeo_creator.contracts.evidence import ResearchSynthesis
from zeo_creator.contracts.production import AttestationPolicy, ContentBrief
from zeo_creator.contracts.publications import PublicationProfile


def proposed_payload(brief: ContentBrief) -> PublicationPayload:
    return PublicationPayload(
        title=brief.working_title,
        caption=f"{brief.core_message}\n\n{brief.desired_audience_action}",
        description=f"{brief.objective} — {brief.content_kind}",
        alt_text=f"{brief.content_kind}: {brief.working_title}",
    )


def approval_digest_for(
    *,
    brief: ContentBrief,
    manifest: ArtifactManifest,
    channel_plan: ChannelPlan,
    payload: PublicationPayload,
) -> str:
    return canonical_digest(
        {
            "brief_id": brief.brief_id,
            "brief_content_digest": brief.content_digest,
            "content_revision": brief.content_revision,
            "manifest_id": manifest.manifest_id,
            "manifest_content_digest": manifest.content_digest,
            "artifact_digests": {item.artifact_ref: item.digest for item in manifest.artifacts},
            "channel_plan_content_digest": channel_plan.content_digest,
            "payload": payload.model_dump(mode="json"),
        }
    )


def validate_delivery_bundle(
    *,
    brief: ContentBrief,
    manifest: ArtifactManifest,
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

    contracts = (brief, manifest, publication, synthesis, channel_plan)
    if not all(digest_is_current(item) for item in contracts):
        blocking("ZEO_CREATOR_STALE_DIGEST", "identity", "One or more contract digests are stale")

    scope = (brief.organization_id, brief.publication_id)
    identity_match = all(
        (item.organization_id, item.publication_id) == scope
        for item in (manifest, publication, synthesis, channel_plan)
    ) and all(
        (
            manifest.brief_id == brief.brief_id,
            manifest.content_revision == brief.content_revision,
            manifest.brief_content_digest == brief.content_digest,
        )
    )
    if not identity_match:
        blocking(
            "ZEO_CREATOR_ARTIFACT_IDENTITY_MISMATCH",
            "identity",
            "Brief/artifact identity mismatch",
        )

    artifact_by_ref = {item.artifact_ref: item for item in manifest.artifacts}
    proof_by_ref = {item.artifact_ref: item for item in manifest.digest_proofs}
    artifact_integrity_pass = all(
        reference in proof_by_ref
        and proof_by_ref[reference].digest == artifact.digest
        and proof_by_ref[reference].storage_ref == artifact.storage_ref
        and proof_by_ref[reference].byte_length == artifact.byte_length
        for reference, artifact in artifact_by_ref.items()
    )
    if not artifact_integrity_pass:
        blocking(
            "ZEO_CREATOR_ARTIFACT_DIGEST_UNVERIFIED",
            "technical",
            "Artifact digest proof does not bind every retrieved artifact",
        )

    attestations = {(item.check_id, item.check_version): item for item in manifest.attestations}
    failed_required: list[str] = []
    for requirement in brief.delivery_requirements:
        if requirement.policy != AttestationPolicy.REQUIRED:
            continue
        candidates = [
            item
            for (check_id, check_version), item in attestations.items()
            if check_id == requirement.check_id
            and (requirement.check_version is None or check_version == requirement.check_version)
        ]
        if not candidates or not any(item.result for item in candidates):
            failed_required.append(requirement.check_id)
    required_attestations_pass = not failed_required
    if failed_required:
        blocking(
            "ZEO_CREATOR_REQUIRED_ATTESTATION_FAILED",
            "technical",
            f"Required attestations absent or failed: {', '.join(sorted(failed_required))}",
        )

    allowed_claim_ids = {claim.claim_id for claim in brief.evidence_claims}
    produced_claim_ids = set(manifest.produced_claim_ids)
    source_claim_traceability = (
        produced_claim_ids == allowed_claim_ids
        and all(
            set(claim.evidence_refs).issubset(synthesis.evidence_refs)
            for claim in brief.evidence_claims
        )
        and set(brief.source_refs).issubset(synthesis.evidence_refs)
    )
    if produced_claim_ids.difference(allowed_claim_ids):
        blocking(
            "ZEO_CREATOR_UNSUPPORTED_CLAIM",
            "evidence",
            "Artifact manifest contains a claim absent from the accepted brief",
        )
    if not source_claim_traceability:
        blocking(
            "ZEO_CREATOR_MISSING_CLAIM_TRACE",
            "evidence",
            "Brief or produced claims do not resolve entirely to the accepted synthesis",
        )

    brand_pass = manifest.brand_profile_ref == publication.reference
    if not brand_pass:
        blocking("ZEO_CREATOR_BRAND_MISMATCH", "brand", "Producer used the wrong brand profile")
    text_required = bool(brief.evidence_claims or brief.prohibited_claims)
    if text_required and not manifest.extracted_text.strip():
        brand_pass = False
        blocking(
            "ZEO_CREATOR_EXTRACTED_TEXT_MISSING",
            "evidence",
            "Extracted text is required for claim and prohibited-language checks",
        )
    produced_text = manifest.extracted_text.casefold()
    prohibited = [claim for claim in brief.prohibited_claims if claim.casefold() in produced_text]
    if prohibited:
        brand_pass = False
        blocking(
            "ZEO_CREATOR_PROHIBITED_CLAIM",
            "brand",
            f"Produced content contains prohibited claims: {', '.join(prohibited)}",
        )

    destination_channels = {item.channel for item in channel_plan.destinations}
    unsupported = destination_channels.difference(brief.target_channels)
    if unsupported:
        blocking(
            "ZEO_CREATOR_DESTINATION_MISMATCH",
            "distribution",
            f"Unapproved destination channels: {', '.join(sorted(unsupported))}",
        )

    payload = proposed_payload(brief)
    approval_digest = approval_digest_for(
        brief=brief,
        manifest=manifest,
        channel_plan=channel_plan,
        payload=payload,
    )
    artifact_refs = tuple(item.artifact_ref for item in manifest.artifacts)
    return DeliveryReviewBundle(
        review_id=stable_id("review", brief.brief_id, manifest.content_digest, approval_digest),
        created_at=created_at,
        organization_id=brief.organization_id,
        publication_id=brief.publication_id,
        input_refs=(
            brief.brief_id,
            manifest.manifest_id,
            *artifact_refs,
            publication.reference,
            synthesis.synthesis_id,
            channel_plan.channel_plan_id,
        ),
        revision=revision,
        brief_id=brief.brief_id,
        manifest_id=manifest.manifest_id,
        artifact_refs=artifact_refs,
        identity_match=identity_match,
        required_attestations_pass=required_attestations_pass,
        source_claim_traceability=source_claim_traceability,
        brand_constraints_pass=brand_pass,
        artifact_integrity_pass=artifact_integrity_pass,
        findings=tuple(findings),
        proposed_payload=payload,
        proposed_destinations=channel_plan.destinations,
        approval_digest=approval_digest,
        ready_for_approval=not any(item.severity == FindingSeverity.BLOCKING for item in findings),
    )
