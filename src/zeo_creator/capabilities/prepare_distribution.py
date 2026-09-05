"""`creator.prepare_distribution@1.0.0`."""

from datetime import datetime

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._examples import distribution_request
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.delivery import DeliveryReviewBundle, RenderedArtifact, RenderManifest
from zeo_creator.contracts.distribution import ChannelPlan, ProposedPublicationOperation
from zeo_creator.contracts.ducktyper import DucktyperBrief
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.distribution import prepare_distribution_operations


class PrepareDistributionRequest(CreatorModel):
    brief: DucktyperBrief
    artifact: RenderedArtifact
    manifest: RenderManifest
    review: DeliveryReviewBundle
    channel_plan: ChannelPlan
    created_at: datetime
    revision: int = Field(default=1, ge=1)


class PrepareDistributionResponse(CreatorModel):
    operations: tuple[ProposedPublicationOperation, ...]


@capability(
    id="creator.prepare_distribution@1.0.0",
    description="Prepare digest-bound provider-neutral publication proposals without executing them.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(name="one-proposal", request=distribution_request()),),
    error_codes=(
        "ZEO_CREATOR_APPROVAL_STALE",
        "ZEO_CREATOR_DELIVERY_BLOCKED",
        "ZEO_CREATOR_STALE_INPUT",
    ),
    tags=("creator", "distribution", "proposal-only", "pure"),
    metadata={"execution": "pure-deterministic", "provider_write": False},
    projection_name="creator_prepare_distribution",
)
def prepare_distribution(
    request: PrepareDistributionRequest,
    ctx: ToolContext,
) -> CapabilityResult[PrepareDistributionResponse]:
    del ctx
    try:
        operations = prepare_distribution_operations(
            brief=request.brief,
            artifact=request.artifact,
            manifest=request.manifest,
            review=request.review,
            channel_plan=request.channel_plan,
            created_at=request.created_at,
            revision=request.revision,
        )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    return CapabilityResult.ok(
        data=PrepareDistributionResponse(operations=operations),
        msg=f"Prepared {len(operations)} publication proposals; executed none",
    )
