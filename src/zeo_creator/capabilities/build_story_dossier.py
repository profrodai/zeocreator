"""`creator.build_story_dossier@1.0.0`."""

from datetime import datetime
from typing import cast

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._newsroom_examples import dossier_request
from zeo_creator.capabilities.editorial_support import strategy
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.newsroom import StoryDossier, StoryRevision
from zeo_creator.services.editorial_kernel import StoryDossierStrategy


class BuildStoryDossierRequest(CreatorModel):
    story: StoryRevision
    audience_significance: str = Field(min_length=1)
    prior_coverage_refs: tuple[str, ...] = ()
    created_at: datetime
    revision: int = Field(default=1, ge=1)


class BuildStoryDossierResponse(CreatorModel):
    dossier: StoryDossier


@capability(
    id="creator.build_story_dossier@1.0.0",
    description="Freeze one publication-scoped story revision into a reusable editorial dossier.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(name="verified-story", request=dossier_request()),),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_STALE_INPUT"),
    tags=("creator", "story", "pure"),
    metadata={"strategy_service": "creator.story_dossier_strategy"},
    projection_name="creator_build_story_dossier",
)
def build_story_dossier(
    request: BuildStoryDossierRequest, ctx: ToolContext
) -> CapabilityResult[BuildStoryDossierResponse]:
    implementation = cast(StoryDossierStrategy, strategy(ctx, "creator.story_dossier_strategy"))
    dossier = implementation.build_dossier(
        story=request.story,
        audience_significance=request.audience_significance,
        prior_coverage_refs=request.prior_coverage_refs,
        created_at=request.created_at,
        revision=request.revision,
    )
    return CapabilityResult.ok(
        data=BuildStoryDossierResponse(dossier=dossier), msg="Built frozen story dossier"
    )
