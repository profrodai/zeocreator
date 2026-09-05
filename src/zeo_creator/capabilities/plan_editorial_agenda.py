"""`creator.plan_editorial_agenda@1.0.0`."""

from datetime import datetime
from typing import cast

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._newsroom_examples import agenda_request
from zeo_creator.capabilities.editorial_support import require_scope, strategy
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.evidence import ResearchWindow
from zeo_creator.contracts.newsroom import EditorialAgenda, PublicationSlot, StoryDossier
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.editorial_kernel import PortfolioPlanningStrategy


class PlanEditorialAgendaRequest(CreatorModel):
    organization_id: str = Field(min_length=1)
    publication_id: str = Field(min_length=1)
    desk_id: str = Field(min_length=1)
    coverage_window: ResearchWindow
    dossiers: tuple[StoryDossier, ...] = ()
    slots: tuple[PublicationSlot, ...] = ()
    created_at: datetime
    revision: int = Field(default=1, ge=1)


class PlanEditorialAgendaResponse(CreatorModel):
    agenda: EditorialAgenda


@capability(
    id="creator.plan_editorial_agenda@1.0.0",
    description="Select frozen dossiers and opportunities into one publication desk agenda.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(name="daily-desk", request=agenda_request()),),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_PUBLICATION_LEAKAGE"),
    tags=("creator", "editorial", "pure"),
    metadata={"strategy_service": "creator.editorial_planner"},
    projection_name="creator_plan_editorial_agenda",
)
def plan_editorial_agenda(
    request: PlanEditorialAgendaRequest, ctx: ToolContext
) -> CapabilityResult[PlanEditorialAgendaResponse]:
    try:
        require_scope(request.organization_id, request.publication_id, *request.dossiers)
        if any(slot.publication_id != request.publication_id for slot in request.slots):
            raise CreatorDomainError(
                "ZEO_CREATOR_PUBLICATION_LEAKAGE", "publication slot belongs to another publication"
            )
        implementation = cast(PortfolioPlanningStrategy, strategy(ctx, "creator.editorial_planner"))
        agenda = implementation.plan_agenda(
            organization_id=request.organization_id,
            publication_id=request.publication_id,
            desk_id=request.desk_id,
            coverage_window=request.coverage_window,
            dossiers=request.dossiers,
            slots=request.slots,
            created_at=request.created_at,
            revision=request.revision,
        )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    return CapabilityResult.ok(
        data=PlanEditorialAgendaResponse(agenda=agenda), msg="Planned agenda"
    )
