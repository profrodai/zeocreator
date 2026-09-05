"""`creator.create_content_brief@1.0.0`."""

from datetime import datetime

from pydantic import Field, model_validator
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._examples import brief_request
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.editorial import EditorialAssignment
from zeo_creator.contracts.evidence import ResearchSynthesis
from zeo_creator.contracts.newsroom import StoryDossier
from zeo_creator.contracts.production import AttestationRequirement, ContentBrief, ExtensionPayload
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.briefing import create_brief


class CreateContentBriefRequest(CreatorModel):
    assignment: EditorialAssignment
    publication: PublicationProfile
    synthesis: ResearchSynthesis | None = None
    dossier: StoryDossier | None = None
    creative_direction: str = Field(min_length=1)
    delivery_requirements: tuple[AttestationRequirement, ...] = Field(min_length=1)
    producer_extension: ExtensionPayload | None = None
    created_at: datetime
    content_revision: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def one_evidence_package(self) -> CreateContentBriefRequest:
        if (self.synthesis is None) == (self.dossier is None):
            raise ValueError("provide exactly one synthesis or story dossier")
        return self


class CreateContentBriefResponse(CreatorModel):
    brief: ContentBrief


@capability(
    id="creator.create_content_brief@1.0.0",
    description="Convert one accepted editorial assignment into a producer-neutral creative brief.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(name="content-brief", request=brief_request()),),
    error_codes=(
        "ZEO_CREATOR_BRAND_MISMATCH",
        "ZEO_CREATOR_PUBLICATION_LEAKAGE",
        "ZEO_CREATOR_STALE_INPUT",
        "ZEO_CREATOR_UNSUPPORTED_CLAIM",
    ),
    tags=("creator", "production", "pure"),
    metadata={"execution": "pure-deterministic"},
    projection_name="creator_create_content_brief",
)
def create_content_brief(
    request: CreateContentBriefRequest,
    ctx: ToolContext,
) -> CapabilityResult[CreateContentBriefResponse]:
    del ctx
    try:
        brief = create_brief(
            assignment=request.assignment,
            publication=request.publication,
            synthesis=request.synthesis,
            dossier=request.dossier,
            creative_direction=request.creative_direction,
            delivery_requirements=request.delivery_requirements,
            producer_extension=request.producer_extension,
            created_at=request.created_at,
            content_revision=request.content_revision,
        )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    return CapabilityResult.ok(
        data=CreateContentBriefResponse(brief=brief),
        msg=f"Created {brief.content_kind} brief {brief.brief_id}",
    )
