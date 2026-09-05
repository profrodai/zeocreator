"""Newsletter planning, composition and editorial review capabilities."""

from datetime import datetime
from typing import cast

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._newsroom_examples import NOW, dossier
from zeo_creator.capabilities._specialization_examples import (
    audience,
    edition,
    newsletter_draft,
    newsletter_plan,
)
from zeo_creator.capabilities.editorial_support import require_scope
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.newsletter import (
    AudienceSelection,
    NewsletterEditorialReview,
    NewsletterIssueDraft,
    NewsletterIssuePlan,
)
from zeo_creator.contracts.newsroom import EditionPlan, StoryDossier
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.specializations import (
    REFERENCE_SPECIALIZATION_STRATEGY,
    NewsletterStrategy,
)


def _strategy(ctx: ToolContext) -> NewsletterStrategy:
    return cast(
        NewsletterStrategy,
        ctx.get_service("creator.newsletter_strategy") or REFERENCE_SPECIALIZATION_STRATEGY,
    )


class PlanNewsletterIssueRequest(CreatorModel):
    edition: EditionPlan
    dossiers: tuple[StoryDossier, ...] = Field(min_length=1)
    audience: AudienceSelection
    created_at: datetime


class PlanNewsletterIssueResponse(CreatorModel):
    plan: NewsletterIssuePlan


class ComposeNewsletterIssueRequest(CreatorModel):
    plan: NewsletterIssuePlan
    dossiers: tuple[StoryDossier, ...] = Field(min_length=1)
    created_at: datetime


class ComposeNewsletterIssueResponse(CreatorModel):
    draft: NewsletterIssueDraft


class ReviewNewsletterIssueRequest(CreatorModel):
    plan: NewsletterIssuePlan
    draft: NewsletterIssueDraft
    created_at: datetime


class ReviewNewsletterIssueResponse(CreatorModel):
    review: NewsletterEditorialReview


@capability(
    id="creator.plan_newsletter_issue@1.0.0",
    description="Plan a newsletter issue as a specialization of an edition and frozen dossiers.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="periodic-issue",
            request={
                "edition": edition().model_dump(mode="json"),
                "dossiers": [dossier().model_dump(mode="json")],
                "audience": audience().model_dump(mode="json"),
                "created_at": NOW.isoformat(),
            },
        ),
    ),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_PUBLICATION_LEAKAGE"),
    tags=("creator", "newsletter", "pure"),
    metadata={"strategy_service": "creator.newsletter_strategy"},
    projection_name="creator_plan_newsletter_issue",
)
def plan_newsletter_issue(
    request: PlanNewsletterIssueRequest, ctx: ToolContext
) -> CapabilityResult[PlanNewsletterIssueResponse]:
    try:
        require_scope(
            request.edition.organization_id,
            request.edition.publication_id,
            *request.dossiers,
        )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    item = _strategy(ctx).plan_newsletter(
        edition=request.edition,
        dossiers=request.dossiers,
        audience=request.audience,
        created_at=request.created_at,
    )
    return CapabilityResult.ok(data=PlanNewsletterIssueResponse(plan=item), msg="Planned issue")


@capability(
    id="creator.compose_newsletter_issue@1.0.0",
    description="Compose HTML and plain-text newsletter representations from an accepted issue plan.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="dual-format-issue",
            request={
                "plan": newsletter_plan().model_dump(mode="json"),
                "dossiers": [dossier().model_dump(mode="json")],
                "created_at": NOW.isoformat(),
            },
        ),
    ),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_PUBLICATION_LEAKAGE"),
    tags=("creator", "newsletter", "pure"),
    metadata={"strategy_service": "creator.newsletter_strategy"},
    projection_name="creator_compose_newsletter_issue",
)
def compose_newsletter_issue(
    request: ComposeNewsletterIssueRequest, ctx: ToolContext
) -> CapabilityResult[ComposeNewsletterIssueResponse]:
    try:
        require_scope(request.plan.organization_id, request.plan.publication_id, *request.dossiers)
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    item = _strategy(ctx).compose_newsletter(
        plan=request.plan, dossiers=request.dossiers, created_at=request.created_at
    )
    return CapabilityResult.ok(
        data=ComposeNewsletterIssueResponse(draft=item), msg="Composed newsletter issue"
    )


@capability(
    id="creator.review_newsletter_issue@1.0.0",
    description="Review newsletter coverage, lineage and audience-policy readiness without sending it.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="issue-review",
            request={
                "plan": newsletter_plan().model_dump(mode="json"),
                "draft": newsletter_draft().model_dump(mode="json"),
                "created_at": NOW.isoformat(),
            },
        ),
    ),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_STALE_INPUT"),
    tags=("creator", "newsletter", "review", "pure"),
    metadata={"strategy_service": "creator.newsletter_strategy"},
    projection_name="creator_review_newsletter_issue",
)
def review_newsletter_issue(
    request: ReviewNewsletterIssueRequest, ctx: ToolContext
) -> CapabilityResult[ReviewNewsletterIssueResponse]:
    try:
        require_scope(request.plan.organization_id, request.plan.publication_id, request.draft)
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    item = _strategy(ctx).review_newsletter(
        plan=request.plan, draft=request.draft, created_at=request.created_at
    )
    return CapabilityResult.ok(
        data=ReviewNewsletterIssueResponse(review=item), msg="Reviewed newsletter issue"
    )
