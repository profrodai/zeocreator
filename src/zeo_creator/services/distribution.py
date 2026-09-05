"""Construction of authorized-runtime inputs without provider execution."""

from datetime import datetime

from zeo_creator.contracts.common import digest_is_current, stable_id
from zeo_creator.contracts.delivery import DeliveryReviewBundle, RenderedArtifact, RenderManifest
from zeo_creator.contracts.distribution import (
    ChannelPlan,
    ProposedPublicationOperation,
)
from zeo_creator.contracts.ducktyper import DucktyperBrief
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.validation import approval_digest_for


def prepare_distribution_operations(
    *,
    brief: DucktyperBrief,
    artifact: RenderedArtifact,
    manifest: RenderManifest,
    review: DeliveryReviewBundle,
    channel_plan: ChannelPlan,
    created_at: datetime,
    revision: int,
) -> tuple[ProposedPublicationOperation, ...]:
    if not all(
        digest_is_current(item) for item in (brief, artifact, manifest, review, channel_plan)
    ):
        raise CreatorDomainError("ZEO_CREATOR_STALE_INPUT", "distribution input digest is stale")
    if not review.ready_for_approval or review.blocking_findings:
        raise CreatorDomainError(
            "ZEO_CREATOR_DELIVERY_BLOCKED", "delivery is not ready for approval"
        )
    if review.proposed_destinations != channel_plan.destinations:
        raise CreatorDomainError(
            "ZEO_CREATOR_APPROVAL_STALE", "destination plan changed after review"
        )
    expected_approval = approval_digest_for(
        brief=brief,
        artifact=artifact,
        manifest=manifest,
        channel_plan=channel_plan,
        payload=review.proposed_payload,
    )
    if expected_approval != review.approval_digest:
        raise CreatorDomainError("ZEO_CREATOR_APPROVAL_STALE", "approval digest no longer matches")

    operations: list[ProposedPublicationOperation] = []
    for destination in channel_plan.destinations:
        identity_material = (
            brief.publication_id,
            artifact.artifact_digest,
            destination.provider_kind.value,
            destination.connection_ref,
            destination.destination_account_ref,
            destination.scheduled_for.isoformat() if destination.scheduled_for else "immediate",
            expected_approval,
        )
        operation_id = stable_id("operation", *identity_material)
        idempotency_key = stable_id("publish", *identity_material)
        operations.append(
            ProposedPublicationOperation(
                operation_id=operation_id,
                created_at=created_at,
                organization_id=brief.organization_id,
                publication_id=brief.publication_id,
                input_refs=(review.review_id, brief.brief_id, artifact.artifact_ref),
                revision=revision,
                artifact_ref=artifact.artifact_ref,
                artifact_digest=artifact.artifact_digest,
                provider_kind=destination.provider_kind,
                connection_ref=destination.connection_ref,
                destination_account_ref=destination.destination_account_ref,
                payload=review.proposed_payload,
                scheduled_for=destination.scheduled_for,
                approval_digest=expected_approval,
                idempotency_key=idempotency_key,
            )
        )
    return tuple(operations)
