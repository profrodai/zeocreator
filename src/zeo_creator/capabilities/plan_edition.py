"""`creator.plan_edition@1.0.0`."""

from datetime import datetime
from typing import cast

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._newsroom_examples import edition_request
from zeo_creator.capabilities.editorial_support import strategy
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.evidence import ResearchWindow
from zeo_creator.contracts.newsroom import EditionPlan, EditorialAgenda
from zeo_creator.services.editorial_kernel import EditionPlanningStrategy


class PlanEditionRequest(CreatorModel):
    agenda: EditorialAgenda
    edition_kind: str = Field(min_length=1)
    publication_window: ResearchWindow
    update_policy_ref: str = Field(min_length=1)
    human_editor_requirements: tuple[str, ...] = ()
    created_at: datetime
    revision: int = Field(default=1, ge=1)


class PlanEditionResponse(CreatorModel):
    edition: EditionPlan


@capability(
    id="creator.plan_edition@1.0.0",
    description="Arrange one publication agenda into a coherent time-bounded edition surface.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(name="living-web-edition", request=edition_request()),),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_STALE_INPUT"),
    tags=("creator", "edition", "pure"),
    metadata={"strategy_service": "creator.edition_planner"},
    projection_name="creator_plan_edition",
)
def plan_edition(
    request: PlanEditionRequest, ctx: ToolContext
) -> CapabilityResult[PlanEditionResponse]:
    implementation = cast(EditionPlanningStrategy, strategy(ctx, "creator.edition_planner"))
    edition = implementation.plan_edition(
        agenda=request.agenda,
        edition_kind=request.edition_kind,
        publication_window=request.publication_window,
        update_policy_ref=request.update_policy_ref,
        human_editor_requirements=request.human_editor_requirements,
        created_at=request.created_at,
        revision=request.revision,
    )
    return CapabilityResult.ok(data=PlanEditionResponse(edition=edition), msg="Planned edition")
