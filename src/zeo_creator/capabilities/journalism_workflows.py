"""News article composition, integrity review and correction capabilities."""

from datetime import datetime
from typing import cast

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._newsroom_examples import NOW, dossier
from zeo_creator.capabilities._specialization_examples import article_draft, article_plan
from zeo_creator.capabilities.editorial_support import require_scope
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.contracts.journalism import (
    CorrectionNotice,
    EditorialReview,
    NewsArticleDraft,
    NewsArticlePlan,
)
from zeo_creator.contracts.newsroom import StoryDossier
from zeo_creator.contracts.production import ContentDocument
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.specializations import (
    REFERENCE_SPECIALIZATION_STRATEGY,
    JournalismStrategy,
)


def _strategy(ctx: ToolContext) -> JournalismStrategy:
    return cast(
        JournalismStrategy,
        ctx.get_service("creator.journalism_strategy") or REFERENCE_SPECIALIZATION_STRATEGY,
    )


class ComposeNewsArticleRequest(CreatorModel):
    plan: NewsArticlePlan
    dossiers: tuple[StoryDossier, ...] = Field(min_length=1)
    created_at: datetime


class ComposeNewsArticleResponse(CreatorModel):
    draft: NewsArticleDraft


class ReviewNewsArticleRequest(CreatorModel):
    plan: NewsArticlePlan
    draft: NewsArticleDraft
    qualified_human_review_ref: str | None = None
    created_at: datetime


class ReviewNewsArticleResponse(CreatorModel):
    review: EditorialReview


class PrepareCorrectionRequest(CreatorModel):
    article: NewsArticleDraft
    review: EditorialReview
    publication_artifact_ref: str = Field(min_length=1)
    corrected_claim_refs: tuple[str, ...] = Field(min_length=1)
    correction_text: ContentDocument
    reason: str = Field(min_length=1)
    effective_at: datetime
    created_at: datetime


class PrepareCorrectionResponse(CreatorModel):
    correction: CorrectionNotice


@capability(
    id="creator.compose_news_article@1.0.0",
    description="Compose a provider-neutral news article draft from a plan and frozen dossiers.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="verified-article",
            request={
                "plan": article_plan().model_dump(mode="json"),
                "dossiers": [dossier().model_dump(mode="json")],
                "created_at": NOW.isoformat(),
            },
        ),
    ),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_PUBLICATION_LEAKAGE"),
    tags=("creator", "journalism", "pure"),
    metadata={"strategy_service": "creator.journalism_strategy"},
    projection_name="creator_compose_news_article",
)
def compose_news_article(
    request: ComposeNewsArticleRequest, ctx: ToolContext
) -> CapabilityResult[ComposeNewsArticleResponse]:
    try:
        require_scope(request.plan.organization_id, request.plan.publication_id, *request.dossiers)
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    draft = _strategy(ctx).compose_article(
        plan=request.plan, dossiers=request.dossiers, created_at=request.created_at
    )
    return CapabilityResult.ok(data=ComposeNewsArticleResponse(draft=draft), msg="Composed article")


@capability(
    id="creator.review_news_article@1.0.0",
    description="Review news integrity and fail closed when qualified human review is required.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="medium-risk-review",
            request={
                "plan": article_plan().model_dump(mode="json"),
                "draft": article_draft().model_dump(mode="json"),
                "qualified_human_review_ref": None,
                "created_at": NOW.isoformat(),
            },
        ),
    ),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_HUMAN_REVIEW_REQUIRED"),
    tags=("creator", "journalism", "review", "pure"),
    metadata={"strategy_service": "creator.journalism_strategy"},
    projection_name="creator_review_news_article",
)
def review_news_article(
    request: ReviewNewsArticleRequest, ctx: ToolContext
) -> CapabilityResult[ReviewNewsArticleResponse]:
    try:
        require_scope(request.plan.organization_id, request.plan.publication_id, request.draft)
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    review = _strategy(ctx).review_article(
        plan=request.plan,
        draft=request.draft,
        qualified_human_review_ref=request.qualified_human_review_ref,
        created_at=request.created_at,
    )
    return CapabilityResult.ok(
        data=ReviewNewsArticleResponse(review=review), msg="Reviewed article"
    )


@capability(
    id="creator.prepare_correction@1.0.0",
    description="Prepare a digest-bound correction notice without updating or publishing externally.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="claim-correction",
            request={
                "article": article_draft().model_dump(mode="json"),
                "review": REFERENCE_SPECIALIZATION_STRATEGY.review_article(
                    plan=article_plan(),
                    draft=article_draft(),
                    qualified_human_review_ref=None,
                    created_at=NOW,
                ).model_dump(mode="json"),
                "publication_artifact_ref": "publication_artifact_example",
                "corrected_claim_refs": [article_draft().claims[0].claim_id],
                "correction_text": {"media_type": "text/plain", "content": "The corrected fact."},
                "reason": "New primary evidence superseded the original claim.",
                "effective_at": NOW.isoformat(),
                "created_at": NOW.isoformat(),
            },
        ),
    ),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_CORRECTION_MISMATCH"),
    tags=("creator", "journalism", "correction", "pure"),
    metadata={"strategy_service": "creator.journalism_strategy"},
    projection_name="creator_prepare_correction",
)
def prepare_correction(
    request: PrepareCorrectionRequest, ctx: ToolContext
) -> CapabilityResult[PrepareCorrectionResponse]:
    try:
        require_scope(
            request.article.organization_id, request.article.publication_id, request.review
        )
        claim_ids = {claim.claim_id for claim in request.article.claims}
        if any(item not in claim_ids for item in request.corrected_claim_refs):
            raise CreatorDomainError(
                "ZEO_CREATOR_CORRECTION_MISMATCH", "correction references an unknown article claim"
            )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    correction = _strategy(ctx).prepare_correction(
        article=request.article,
        review=request.review,
        publication_artifact_ref=request.publication_artifact_ref,
        corrected_claim_refs=request.corrected_claim_refs,
        correction_text=request.correction_text,
        reason=request.reason,
        effective_at=request.effective_at,
        created_at=request.created_at,
    )
    return CapabilityResult.ok(
        data=PrepareCorrectionResponse(correction=correction), msg="Prepared correction"
    )
