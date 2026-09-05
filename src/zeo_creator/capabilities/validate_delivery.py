"""`creator.validate_delivery@1.0.0`."""

from datetime import datetime

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._examples import delivery_request
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.delivery import DeliveryReviewBundle, RenderedArtifact, RenderManifest
from zeo_creator.contracts.distribution import ChannelPlan
from zeo_creator.contracts.ducktyper import DucktyperBrief
from zeo_creator.contracts.evidence import ResearchSynthesis
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.services.validation import validate_delivery_bundle


class ValidateDeliveryRequest(CreatorModel):
    brief: DucktyperBrief
    artifact: RenderedArtifact
    manifest: RenderManifest
    publication: PublicationProfile
    synthesis: ResearchSynthesis
    channel_plan: ChannelPlan
    created_at: datetime
    revision: int = Field(default=1, ge=1)


class ValidateDeliveryResponse(CreatorModel):
    review: DeliveryReviewBundle


@capability(
    id="creator.validate_delivery@1.0.0",
    description="Validate a Ducktyper render against its accepted brief, evidence, brand, and channel plan.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(name="valid-render", request=delivery_request()),),
    error_codes=(
        "ZEO_CREATOR_BRAND_MISMATCH",
        "ZEO_CREATOR_ARTIFACT_DIGEST_UNVERIFIED",
        "ZEO_CREATOR_DESTINATION_MISMATCH",
        "ZEO_CREATOR_EXTRACTED_TEXT_MISSING",
        "ZEO_CREATOR_MISSING_CLAIM_TRACE",
        "ZEO_CREATOR_MISSING_RENDER_ELEMENT",
        "ZEO_CREATOR_PROHIBITED_CLAIM",
        "ZEO_CREATOR_RENDER_IDENTITY_MISMATCH",
        "ZEO_CREATOR_STALE_DIGEST",
        "ZEO_CREATOR_TECHNICAL_CHECK_FAILED",
        "ZEO_CREATOR_TECHNICAL_CHECKS_MISSING",
        "ZEO_CREATOR_UNSUPPORTED_CLAIM",
    ),
    tags=("creator", "ducktyper", "validation", "pure"),
    metadata={"execution": "pure-deterministic"},
    projection_name="creator_validate_delivery",
)
def validate_delivery(
    request: ValidateDeliveryRequest,
    ctx: ToolContext,
) -> CapabilityResult[ValidateDeliveryResponse]:
    del ctx
    review = validate_delivery_bundle(
        brief=request.brief,
        artifact=request.artifact,
        manifest=request.manifest,
        publication=request.publication,
        synthesis=request.synthesis,
        channel_plan=request.channel_plan,
        created_at=request.created_at,
        revision=request.revision,
    )
    return CapabilityResult.ok(
        data=ValidateDeliveryResponse(review=review),
        msg=(
            f"Delivery {review.review_id} is ready for approval"
            if review.ready_for_approval
            else f"Delivery {review.review_id} has blocking findings"
        ),
    )
