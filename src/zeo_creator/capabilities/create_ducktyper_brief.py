"""`creator.create_ducktyper_brief@1.0.0`."""

from datetime import datetime

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._examples import brief_request
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.ducktyper import DucktyperBrief
from zeo_creator.contracts.editorial import EditorialAssignment
from zeo_creator.contracts.evidence import ResearchSynthesis
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.briefing import create_brief


class CreateDucktyperBriefRequest(CreatorModel):
    assignment: EditorialAssignment
    publication: PublicationProfile
    synthesis: ResearchSynthesis
    created_at: datetime
    content_revision: int = Field(default=1, ge=1)


class CreateDucktyperBriefResponse(CreatorModel):
    brief: DucktyperBrief


@capability(
    id="creator.create_ducktyper_brief@1.0.0",
    description="Convert one accepted editorial assignment into one typed Ducktyper brief.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(name="animated-brief", request=brief_request()),),
    error_codes=(
        "ZEO_CREATOR_BRAND_MISMATCH",
        "ZEO_CREATOR_PUBLICATION_LEAKAGE",
        "ZEO_CREATOR_STALE_INPUT",
        "ZEO_CREATOR_UNSUPPORTED_CLAIM",
    ),
    tags=("creator", "ducktyper", "pure"),
    metadata={"execution": "pure-deterministic"},
    projection_name="creator_create_ducktyper_brief",
)
def create_ducktyper_brief(
    request: CreateDucktyperBriefRequest,
    ctx: ToolContext,
) -> CapabilityResult[CreateDucktyperBriefResponse]:
    del ctx
    try:
        brief = create_brief(
            assignment=request.assignment,
            publication=request.publication,
            synthesis=request.synthesis,
            created_at=request.created_at,
            content_revision=request.content_revision,
        )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    return CapabilityResult.ok(
        data=CreateDucktyperBriefResponse(brief=brief),
        msg=f"Created {brief.deliverable_kind.value} brief {brief.brief_id}",
    )
