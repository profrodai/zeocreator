"""Provider-neutral commentary opportunity, composition and review capabilities."""

from datetime import datetime
from typing import cast

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.capabilities._newsroom_examples import NOW, dossier
from zeo_creator.capabilities._specialization_examples import (
    commentary_draft,
    conversation,
    opportunity,
)
from zeo_creator.capabilities.editorial_support import require_scope
from zeo_creator.contracts.commentary import (
    CommentaryDraft,
    CommentaryReview,
    ConversationObservation,
    EngagementOpportunity,
)
from zeo_creator.contracts.common import CreatorModel
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.specializations import (
    REFERENCE_SPECIALIZATION_STRATEGY,
    CommentaryStrategy,
)


def _strategy(ctx: ToolContext) -> CommentaryStrategy:
    return cast(
        CommentaryStrategy,
        ctx.get_service("creator.commentary_strategy") or REFERENCE_SPECIALIZATION_STRATEGY,
    )


class IdentifyEngagementOpportunitiesRequest(CreatorModel):
    conversation: ConversationObservation
    persona_ref: str = Field(min_length=1)
    distinctive_contribution: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()
    created_at: datetime
    expires_at: datetime


class IdentifyEngagementOpportunitiesResponse(CreatorModel):
    opportunity: EngagementOpportunity


class ComposeCommentaryRequest(CreatorModel):
    opportunity: EngagementOpportunity
    conversation: ConversationObservation
    tone: str = Field(min_length=1)
    authorship_mode: str = Field(min_length=1)
    created_at: datetime


class ComposeCommentaryResponse(CreatorModel):
    draft: CommentaryDraft


class ReviewCommentaryRequest(CreatorModel):
    draft: CommentaryDraft
    conversation: ConversationObservation
    persona_position_refs: tuple[str, ...] = ()
    personal_experience_refs: tuple[str, ...] = ()
    approval_policy_ref: str = Field(min_length=1)
    created_at: datetime


class ReviewCommentaryResponse(CreatorModel):
    review: CommentaryReview


@capability(
    id="creator.identify_engagement_opportunities@1.0.0",
    description="Identify a publication-scoped opportunity to add value to a conversation.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="evidence-led-reply",
            request={
                "conversation": conversation().model_dump(mode="json"),
                "persona_ref": "persona_example",
                "distinctive_contribution": "Preserve immutable source references before synthesis.",
                "evidence_refs": list(dossier().evidence_lineage),
                "created_at": NOW.isoformat(),
                "expires_at": opportunity().timeliness_expires_at.isoformat(),
            },
        ),
    ),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_STALE_INPUT"),
    tags=("creator", "commentary", "pure"),
    metadata={"strategy_service": "creator.commentary_strategy"},
    projection_name="creator_identify_engagement_opportunities",
)
def identify_engagement_opportunities(
    request: IdentifyEngagementOpportunitiesRequest, ctx: ToolContext
) -> CapabilityResult[IdentifyEngagementOpportunitiesResponse]:
    item = _strategy(ctx).identify_engagement(
        conversation=request.conversation,
        persona_ref=request.persona_ref,
        distinctive_contribution=request.distinctive_contribution,
        evidence_refs=request.evidence_refs,
        created_at=request.created_at,
        expires_at=request.expires_at,
    )
    return CapabilityResult.ok(
        data=IdentifyEngagementOpportunitiesResponse(opportunity=item),
        msg=f"Recommended {item.disposition.value}",
    )


@capability(
    id="creator.compose_commentary@1.0.0",
    description="Compose provider-neutral commentary bound to one conversation and persona stance.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="reply-draft",
            request={
                "opportunity": opportunity().model_dump(mode="json"),
                "conversation": conversation().model_dump(mode="json"),
                "tone": "constructive",
                "authorship_mode": "human-reviewed",
                "created_at": NOW.isoformat(),
            },
        ),
    ),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_PUBLICATION_LEAKAGE"),
    tags=("creator", "commentary", "pure"),
    metadata={"strategy_service": "creator.commentary_strategy"},
    projection_name="creator_compose_commentary",
)
def compose_commentary(
    request: ComposeCommentaryRequest, ctx: ToolContext
) -> CapabilityResult[ComposeCommentaryResponse]:
    try:
        require_scope(
            request.opportunity.organization_id,
            request.opportunity.publication_id,
            request.conversation,
        )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    item = _strategy(ctx).compose_commentary(
        opportunity=request.opportunity,
        conversation=request.conversation,
        tone=request.tone,
        authorship_mode=request.authorship_mode,
        created_at=request.created_at,
    )
    return CapabilityResult.ok(
        data=ComposeCommentaryResponse(draft=item), msg="Composed commentary"
    )


@capability(
    id="creator.review_commentary@1.0.0",
    description="Review commentary for added value, grounded persona stance, safety and timeliness.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="human-approval-candidate",
            request={
                "draft": commentary_draft().model_dump(mode="json"),
                "conversation": conversation().model_dump(mode="json"),
                "persona_position_refs": ["position_example"],
                "personal_experience_refs": [],
                "approval_policy_ref": "approval.human@1",
                "created_at": NOW.isoformat(),
            },
        ),
    ),
    error_codes=("ZEO_CREATOR_SCOPE_MISMATCH", "ZEO_CREATOR_PUBLICATION_LEAKAGE"),
    tags=("creator", "commentary", "review", "pure"),
    metadata={"strategy_service": "creator.commentary_strategy"},
    projection_name="creator_review_commentary",
)
def review_commentary(
    request: ReviewCommentaryRequest, ctx: ToolContext
) -> CapabilityResult[ReviewCommentaryResponse]:
    try:
        require_scope(
            request.draft.organization_id, request.draft.publication_id, request.conversation
        )
    except CreatorDomainError as exc:
        return CapabilityResult.fail(msg=str(exc), code=exc.code, exception=exc)
    item = _strategy(ctx).review_commentary(
        draft=request.draft,
        conversation=request.conversation,
        persona_position_refs=request.persona_position_refs,
        personal_experience_refs=request.personal_experience_refs,
        approval_policy_ref=request.approval_policy_ref,
        created_at=request.created_at,
    )
    return CapabilityResult.ok(
        data=ReviewCommentaryResponse(review=item), msg="Reviewed commentary"
    )
