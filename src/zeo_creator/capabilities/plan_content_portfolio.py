"""`creator.plan_content_portfolio@1.0.0`."""

from datetime import datetime

from pydantic import Field, model_validator
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._examples import plan_request
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.editorial import (
    ContentHistoryEntry,
    ContentPortfolioPlan,
    PortfolioConstraints,
    PublicationObjective,
)
from zeo_creator.contracts.evidence import ResearchSynthesis, ResearchWindow
from zeo_creator.contracts.newsroom import EditorialAgenda, StoryDossier
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.planning import plan_portfolio, plan_portfolio_from_agendas


class PlanContentPortfolioRequest(CreatorModel):
    organization_id: str = Field(min_length=1)
    profiles: tuple[PublicationProfile, ...] = Field(min_length=1)
    syntheses: tuple[ResearchSynthesis, ...] = ()
    editorial_agendas: tuple[EditorialAgenda, ...] = ()
    story_dossiers: tuple[StoryDossier, ...] = ()
    content_history: tuple[ContentHistoryEntry, ...] = ()
    objectives: tuple[PublicationObjective, ...] = Field(min_length=1)
    constraints: PortfolioConstraints
    planning_window: ResearchWindow
    due_at: datetime
    created_at: datetime
    revision: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def one_editorial_source_mode(self) -> PlanContentPortfolioRequest:
        synthesis_mode = bool(self.syntheses)
        agenda_mode = bool(self.editorial_agendas or self.story_dossiers)
        if synthesis_mode == agenda_mode:
            raise ValueError("provide either syntheses or agendas with dossiers")
        if agenda_mode and (not self.editorial_agendas or not self.story_dossiers):
            raise ValueError("agenda mode requires editorial_agendas and story_dossiers")
        return self


class PlanContentPortfolioResponse(CreatorModel):
    plan: ContentPortfolioPlan


@capability(
    id="creator.plan_content_portfolio@1.0.0",
    description="Create a publication-isolated, evidence-backed content portfolio for a planning window.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(name="one-publication", request=plan_request()),),
    error_codes=(
        "ZEO_CREATOR_DUPLICATE_PUBLICATION",
        "ZEO_CREATOR_INSUFFICIENT_NOVEL_TOPICS",
        "ZEO_CREATOR_SCOPE_MISMATCH",
        "ZEO_CREATOR_STALE_INPUT",
    ),
    tags=("creator", "editorial", "pure"),
    metadata={"execution": "pure-deterministic"},
    projection_name="creator_plan_content_portfolio",
)
def plan_content_portfolio(
    request: PlanContentPortfolioRequest,
    ctx: ToolContext,
) -> CapabilityResult[PlanContentPortfolioResponse]:
    del ctx
    try:
        if request.editorial_agendas:
            plan = plan_portfolio_from_agendas(
                organization_id=request.organization_id,
                profiles=request.profiles,
                agendas=request.editorial_agendas,
                dossiers=request.story_dossiers,
                content_history=request.content_history,
                objectives=request.objectives,
                planning_window=request.planning_window,
                due_at=request.due_at,
                created_at=request.created_at,
                revision=request.revision,
            )
        else:
            plan = plan_portfolio(
                organization_id=request.organization_id,
                profiles=request.profiles,
                syntheses=request.syntheses,
                content_history=request.content_history,
                objectives=request.objectives,
                constraints=request.constraints,
                planning_window=request.planning_window,
                due_at=request.due_at,
                created_at=request.created_at,
                revision=request.revision,
            )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    return CapabilityResult.ok(
        data=PlanContentPortfolioResponse(plan=plan),
        msg=f"Planned {len(plan.assignments)} editorial assignments",
    )
