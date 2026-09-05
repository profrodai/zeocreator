"""`creator.research_synthesis@1.0.0`."""

from datetime import datetime
from typing import cast

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._examples import research_request
from zeo_creator.capabilities.support import EVIDENCE_READ_REQUIREMENTS
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.evidence import EvidenceQuery, ResearchSynthesis, ResearchWindow
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError
from zeo_creator.ports.evidence_sources import EvidenceSourcePort
from zeo_creator.services.research import synthesize_research


class ResearchSynthesisRequest(CreatorModel):
    organization_id: str = Field(min_length=1)
    publication: PublicationProfile
    research_window: ResearchWindow
    queries: tuple[EvidenceQuery, ...] = Field(min_length=1)
    content_history_refs: tuple[str, ...] = ()
    created_at: datetime
    revision: int = Field(default=1, ge=1)


class ResearchSynthesisResponse(CreatorModel):
    synthesis: ResearchSynthesis


@capability(
    id="creator.research_synthesis@1.0.0",
    description="Retrieve permitted evidence through an injected read port and synthesize one publication.",
    effects={EffectKind.READ, EffectKind.EXTERNAL_COMMUNICATION},
    examples=(CapabilityExample(name="one-publication", request=research_request()),),
    error_codes=(
        "ZEO_CREATOR_NO_EVIDENCE",
        "ZEO_CREATOR_NO_USABLE_EVIDENCE",
        "ZEO_CREATOR_PROVENANCE_MISMATCH",
        "ZEO_CREATOR_PUBLICATION_LEAKAGE",
        "ZEO_CREATOR_SCOPE_MISMATCH",
        "ZEO_CREATOR_STALE_INPUT",
        "ZEO_CREATOR_WINDOW_MISMATCH",
    ),
    requirements=EVIDENCE_READ_REQUIREMENTS,
    tags=("creator", "research", "read-only"),
    projection_name="creator_research_synthesis",
)
def research_synthesis(
    request: ResearchSynthesisRequest,
    ctx: ToolContext,
) -> CapabilityResult[ResearchSynthesisResponse]:
    source = cast(EvidenceSourcePort, ctx.require_service("creator.evidence_source"))
    try:
        synthesis = synthesize_research(
            organization_id=request.organization_id,
            publication=request.publication,
            research_window=request.research_window,
            queries=request.queries,
            content_history_refs=request.content_history_refs,
            created_at=request.created_at,
            revision=request.revision,
            source=source,
        )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    return CapabilityResult.ok(
        data=ResearchSynthesisResponse(synthesis=synthesis),
        msg=f"Synthesized {len(synthesis.evidence_refs)} evidence items for {synthesis.publication_id}",
    )
