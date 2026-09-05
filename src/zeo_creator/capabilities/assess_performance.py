"""`creator.assess_performance@1.0.0`."""

from datetime import datetime
from typing import cast

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._examples import performance_request
from zeo_creator.capabilities.support import METRICS_READ_REQUIREMENTS
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.performance import DailyPerformanceAssessment, MetricsQuery
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError
from zeo_creator.ports.metrics import MetricsSourcePort
from zeo_creator.services.assessment import assess_publication_performance


class AssessPerformanceRequest(CreatorModel):
    publication: PublicationProfile
    queries: tuple[MetricsQuery, ...] = Field(min_length=1)
    objective: str = Field(min_length=1)
    created_at: datetime
    revision: int = Field(default=1, ge=1)


class AssessPerformanceResponse(CreatorModel):
    assessment: DailyPerformanceAssessment


@capability(
    id="creator.assess_performance@1.0.0",
    description="Retrieve permitted metrics through an injected read port and assess one publication.",
    effects={EffectKind.READ, EffectKind.EXTERNAL_COMMUNICATION},
    examples=(CapabilityExample(name="one-publication", request=performance_request()),),
    error_codes=(
        "ZEO_CREATOR_PROVENANCE_MISMATCH",
        "ZEO_CREATOR_PUBLICATION_LEAKAGE",
        "ZEO_CREATOR_STALE_INPUT",
        "ZEO_CREATOR_SCOPE_MISMATCH",
        "ZEO_CREATOR_WINDOW_MISMATCH",
    ),
    requirements=METRICS_READ_REQUIREMENTS,
    tags=("creator", "performance", "read-only"),
    projection_name="creator_assess_performance",
)
def assess_performance(
    request: AssessPerformanceRequest,
    ctx: ToolContext,
) -> CapabilityResult[AssessPerformanceResponse]:
    source = cast(MetricsSourcePort, ctx.require_service("creator.metrics_source"))
    try:
        assessment = assess_publication_performance(
            publication=request.publication,
            queries=request.queries,
            objective=request.objective,
            created_at=request.created_at,
            revision=request.revision,
            source=source,
        )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    return CapabilityResult.ok(
        data=AssessPerformanceResponse(assessment=assessment),
        msg=f"Assessed {assessment.publication_id} from {len(assessment.metrics)} observations",
    )
