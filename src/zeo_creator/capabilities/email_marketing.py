"""Canonical input-only campaign, linear sequence and email editorial capabilities."""

from collections.abc import Callable
from typing import cast

from pydantic import Field
from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.tools import ToolContext, capability

from zeo_creator.contracts.common import UtcDatetime
from zeo_creator.contracts.email_marketing import (
    AudienceSnapshotSummary,
    EmailArtifactRef,
    EmailCampaignPlan,
    EmailDeliveryPackage,
    EmailEditorialReview,
    EmailMessageDraft,
    EmailMessagePlan,
    EmailMetricName,
    EmailMetricObservation,
    EmailModel,
    EmailProgramAssessment,
    EmailProofReceipt,
    EmailReviewEvidence,
    EmailSequencePlan,
    OpaqueRef,
)
from zeo_creator.contracts.evidence import ResearchWindow
from zeo_creator.contracts.newsletter import NewsletterIssuePlan
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.reference import email_inputs as sample
from zeo_creator.services import email_marketing as service


class PlanEmailCampaignRequest(EmailModel):
    publication: PublicationProfile
    brief: service.EmailCampaignBrief
    created_at: UtcDatetime


class PlanEmailCampaignResponse(EmailModel):
    campaign: EmailCampaignPlan


class PlanEmailSequenceRequest(EmailModel):
    campaign: EmailCampaignPlan
    sequence_id: OpaqueRef
    messages: tuple[EmailMessagePlan, ...] = Field(min_length=1, max_length=100)
    delays_seconds: tuple[int, ...] = Field(min_length=1, max_length=100)
    policies: service.EmailSequencePolicies
    enrolment_window: ResearchWindow
    required_provider_semantics: tuple[OpaqueRef, ...] = Field(min_length=1)
    previous: EmailSequencePlan | None = None
    migration_policy: EmailArtifactRef | None = None
    created_at: UtcDatetime


class PlanEmailSequenceResponse(EmailModel):
    sequence: EmailSequencePlan


class PlanEmailMessageRequest(EmailModel):
    publication: PublicationProfile
    campaign: EmailCampaignPlan
    directions: service.EmailMessageDirections
    newsletter: NewsletterIssuePlan | None = None
    created_at: UtcDatetime


class PlanEmailMessageResponse(EmailModel):
    plan: EmailMessagePlan


class ComposeEmailMessageRequest(EmailModel):
    plan: EmailMessagePlan
    sections: tuple[service.EmailSourceSection, ...] = Field(min_length=1)
    created_at: UtcDatetime


class ComposeEmailMessageResponse(EmailModel):
    draft: EmailMessageDraft


class ReviewEmailMessageRequest(EmailModel):
    publication: PublicationProfile
    plan: EmailMessagePlan
    draft: EmailMessageDraft
    evidence: tuple[EmailReviewEvidence, ...] = ()
    created_at: UtcDatetime


class ReviewEmailMessageResponse(EmailModel):
    review: EmailEditorialReview


class PrepareEmailDeliveryRequest(EmailModel):
    plan: EmailMessagePlan
    draft: EmailMessageDraft
    review: EmailEditorialReview
    audience_snapshot: AudienceSnapshotSummary
    proofs: tuple[EmailProofReceipt, ...] = ()
    schedule_intent: UtcDatetime | None = None
    sequence: EmailSequencePlan | None = None
    created_at: UtcDatetime


class PrepareEmailDeliveryResponse(EmailModel):
    package: EmailDeliveryPackage


class AssessEmailProgramRequest(EmailModel):
    campaign: EmailCampaignPlan
    observations: tuple[EmailMetricObservation, ...]
    observation_window: ResearchWindow
    expected_metrics: tuple[EmailMetricName, ...] = Field(min_length=1)
    created_at: UtcDatetime


class AssessEmailProgramResponse(EmailModel):
    assessment: EmailProgramAssessment


def _result[T: EmailModel](request: EmailModel, transform: Callable[[], T]) -> CapabilityResult[T]:
    try:
        service.current(request)
        result = transform()
        service.current(result)
        return CapabilityResult.ok(
            data=result, msg="Prepared email artifact; runtime authority required"
        )
    except Exception:
        # Never persist validation input, injected exception text, or provider error bodies.
        return CapabilityResult.fail(
            code="ZEO_CREATOR_EMAIL_INVALID", msg="Email input or strategy output failed validation"
        )


@capability(
    id="creator.plan_email_campaign@1.0.0",
    description="Plan a publication-scoped bounded email campaign from supplied editorial intent.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="campaign",
            request=PlanEmailCampaignRequest(
                publication=sample.profile(), brief=sample.brief(), created_at=sample.NOW
            ).model_dump(mode="json"),
        ),
    ),
    error_codes=("ZEO_CREATOR_EMAIL_INVALID",),
    tags=("creator", "email", "pure"),
    projection_name="creator_plan_email_campaign",
)
def plan_email_campaign(
    request: PlanEmailCampaignRequest, ctx: ToolContext
) -> CapabilityResult[PlanEmailCampaignResponse]:
    return _result(
        request,
        lambda: PlanEmailCampaignResponse(
            campaign=service.plan_campaign(request.publication, request.brief, request.created_at)
        ),
    )


@capability(
    id="creator.plan_email_sequence@1.0.0",
    description="Build a bounded linear sequence revision without activation or enrolment.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="sequence",
            request=PlanEmailSequenceRequest(
                campaign=sample.campaign(),
                sequence_id="publication-a/welcome",
                messages=(sample.plan(),),
                delays_seconds=(0,),
                policies=sample.policies(),
                enrolment_window=sample.brief().window,
                required_provider_semantics=("linear", "retain_existing_revision"),
                created_at=sample.NOW,
            ).model_dump(mode="json"),
        ),
    ),
    error_codes=("ZEO_CREATOR_EMAIL_INVALID",),
    tags=("creator", "email", "pure"),
    projection_name="creator_plan_email_sequence",
)
def plan_email_sequence(
    request: PlanEmailSequenceRequest, ctx: ToolContext
) -> CapabilityResult[PlanEmailSequenceResponse]:
    return _result(
        request,
        lambda: PlanEmailSequenceResponse(
            sequence=service.plan_sequence(
                request.campaign,
                request.sequence_id,
                request.messages,
                request.delays_seconds,
                request.policies,
                request.enrolment_window,
                request.required_provider_semantics,
                request.created_at,
                request.previous,
                request.migration_policy,
            )
        ),
    )


@capability(
    id="creator.plan_email_message@1.0.0",
    description="Plan message content, symbolic personalization, audience and compliance requirements.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="message",
            request=PlanEmailMessageRequest(
                publication=sample.profile(),
                campaign=sample.campaign(),
                directions=sample.directions(),
                created_at=sample.NOW,
            ).model_dump(mode="json"),
        ),
    ),
    error_codes=("ZEO_CREATOR_EMAIL_INVALID",),
    tags=("creator", "email", "pure"),
    projection_name="creator_plan_email_message",
)
def plan_email_message(
    request: PlanEmailMessageRequest, ctx: ToolContext
) -> CapabilityResult[PlanEmailMessageResponse]:
    return _result(
        request,
        lambda: PlanEmailMessageResponse(
            plan=service.plan_message(
                request.publication,
                request.campaign,
                request.directions,
                request.created_at,
                request.newsletter,
            )
        ),
    )


@capability(
    id="creator.compose_email_message@1.0.0",
    description="Compose exact HTML and plain text from curated evidence using an optional injected strategy.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="dual-format",
            request=ComposeEmailMessageRequest(
                plan=sample.plan(), sections=sample.sections(), created_at=sample.NOW
            ).model_dump(mode="json"),
        ),
    ),
    error_codes=("ZEO_CREATOR_EMAIL_INVALID",),
    tags=("creator", "email", "pure"),
    metadata={"strategy_service": "creator.email_strategy"},
    projection_name="creator_compose_email_message",
)
def compose_email_message(
    request: ComposeEmailMessageRequest, ctx: ToolContext
) -> CapabilityResult[ComposeEmailMessageResponse]:
    return _result(
        request,
        lambda: ComposeEmailMessageResponse(
            draft=service.compose_message(
                request.plan,
                request.sections,
                request.created_at,
                cast(
                    service.EmailCreativeStrategy | None, ctx.get_service("creator.email_strategy")
                ),
            )
        ),
    )


@capability(
    id="creator.review_email_message@1.0.0",
    description="Review supplied email artifacts; semantic checks require evidence and never confer approval.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="review",
            request=ReviewEmailMessageRequest(
                publication=sample.profile(),
                plan=sample.plan(),
                draft=sample.draft(),
                created_at=sample.NOW,
            ).model_dump(mode="json"),
        ),
    ),
    error_codes=("ZEO_CREATOR_EMAIL_INVALID",),
    tags=("creator", "email", "pure"),
    projection_name="creator_review_email_message",
)
def review_email_message(
    request: ReviewEmailMessageRequest, ctx: ToolContext
) -> CapabilityResult[ReviewEmailMessageResponse]:
    return _result(
        request,
        lambda: ReviewEmailMessageResponse(
            review=service.review_message(
                request.publication,
                request.plan,
                request.draft,
                request.evidence,
                request.created_at,
            )
        ),
    )


@capability(
    id="creator.prepare_email_delivery@1.0.0",
    description="Freeze exact delivery material bound to a current opaque audience snapshot; never send.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="delivery",
            request=PrepareEmailDeliveryRequest(
                plan=sample.plan(),
                draft=sample.draft(),
                review=service.review_message(
                    sample.profile(),
                    sample.plan(),
                    sample.draft(),
                    sample.evidence(sample.draft()),
                    sample.NOW,
                ),
                audience_snapshot=sample.snapshot(),
                proofs=sample.proofs(sample.draft()),
                created_at=sample.NOW,
            ).model_dump(mode="json"),
        ),
    ),
    error_codes=("ZEO_CREATOR_EMAIL_INVALID",),
    tags=("creator", "email", "pure"),
    projection_name="creator_prepare_email_delivery",
)
def prepare_email_delivery(
    request: PrepareEmailDeliveryRequest, ctx: ToolContext
) -> CapabilityResult[PrepareEmailDeliveryResponse]:
    return _result(
        request,
        lambda: PrepareEmailDeliveryResponse(
            package=service.prepare_delivery(
                request.plan,
                request.draft,
                request.review,
                request.audience_snapshot,
                request.proofs,
                request.created_at,
                request.schedule_intent,
                request.sequence,
            )
        ),
    )


@capability(
    id="creator.assess_email_program@1.0.0",
    description="Assess receipt-linked aggregate observations already collected outside Creator.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            name="missing-observations",
            request=AssessEmailProgramRequest(
                campaign=sample.campaign(),
                observations=(),
                observation_window=sample.brief().window,
                expected_metrics=("delivered", "cta_conversions"),
                created_at=sample.NOW,
            ).model_dump(mode="json"),
        ),
    ),
    error_codes=("ZEO_CREATOR_EMAIL_INVALID",),
    tags=("creator", "email", "pure"),
    projection_name="creator_assess_email_program",
)
def assess_email_program(
    request: AssessEmailProgramRequest, ctx: ToolContext
) -> CapabilityResult[AssessEmailProgramResponse]:
    return _result(
        request,
        lambda: AssessEmailProgramResponse(
            assessment=service.assess_program(
                request.campaign,
                request.observations,
                request.observation_window,
                request.expected_metrics,
                request.created_at,
            )
        ),
    )
