"""Construction of authorized-runtime inputs without provider execution."""

from datetime import datetime

from zeo_creator.contracts.common import digest_is_current, stable_id
from zeo_creator.contracts.delivery import ArtifactManifest, DeliveryReviewBundle
from zeo_creator.contracts.distribution import ChannelPlan, ProposedPublicationOperation
from zeo_creator.contracts.production import ContentBrief
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.validation import approval_digest_for


def prepare_distribution_operations(
    *,
    brief: ContentBrief,
    manifest: ArtifactManifest,
    review: DeliveryReviewBundle,
    channel_plan: ChannelPlan,
    created_at: datetime,
    revision: int,
) -> tuple[ProposedPublicationOperation, ...]:
    if not all(digest_is_current(item) for item in (brief, manifest, review)):
        raise CreatorDomainError("ZEO_CREATOR_STALE_INPUT", "distribution input digest is stale")
    if not review.ready_for_approval or review.blocking_findings:
        raise CreatorDomainError(
            "ZEO_CREATOR_DELIVERY_BLOCKED", "delivery is not ready for approval"
        )
    if review.proposed_variants != channel_plan.variants:
        raise CreatorDomainError(
            "ZEO_CREATOR_APPROVAL_STALE", "distribution plan changed after review"
        )
    if not digest_is_current(channel_plan):
        raise CreatorDomainError("ZEO_CREATOR_STALE_INPUT", "channel plan digest is stale")
    expected_approval = approval_digest_for(
        brief=brief,
        manifest=manifest,
        channel_plan=channel_plan,
    )
    if expected_approval != review.approval_digest:
        raise CreatorDomainError("ZEO_CREATOR_APPROVAL_STALE", "approval digest no longer matches")

    artifact_refs = {item.artifact_ref for item in manifest.artifacts}
    operations: list[ProposedPublicationOperation] = []
    for variant in channel_plan.variants:
        destination = variant.destination
        if not set(variant.selected_artifact_refs).issubset(artifact_refs):
            raise CreatorDomainError(
                "ZEO_CREATOR_ARTIFACT_SELECTION_MISMATCH",
                "distribution variant selects artifacts outside the manifest",
            )
        identity_material = (
            brief.publication_id,
            manifest.content_digest,
            channel_plan.content_digest,
            destination.provider_kind,
            destination.channel,
            destination.connection_ref,
            destination.destination_account_ref,
            destination.scheduled_for.isoformat() if destination.scheduled_for else "immediate",
            expected_approval,
        )
        operation_id = stable_id("operation", *identity_material)
        operations.append(
            ProposedPublicationOperation(
                operation_id=operation_id,
                created_at=created_at,
                organization_id=brief.organization_id,
                publication_id=brief.publication_id,
                input_refs=(
                    review.review_id,
                    brief.brief_id,
                    manifest.manifest_id,
                    *variant.selected_artifact_refs,
                ),
                revision=revision,
                artifact_manifest_ref=manifest.manifest_id,
                artifact_manifest_digest=manifest.content_digest,
                channel=destination.channel,
                destination=destination,
                selected_artifact_refs=variant.selected_artifact_refs,
                content=variant.content,
                accessibility_text=variant.accessibility_text,
                extension=variant.extension,
                scheduled_for=destination.scheduled_for,
                approval_digest=expected_approval,
                idempotency_key=stable_id("publish", *identity_material),
            )
        )
    return tuple(operations)
