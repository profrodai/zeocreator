"""Installed-wheel proof: capabilities -> artifacts -> simulated host -> observations."""

from zeo_core.contracts import CapabilityResult

from zeo_creator.capabilities.email_marketing import (
    AssessEmailProgramRequest,
    ComposeEmailMessageRequest,
    PlanEmailCampaignRequest,
    PlanEmailMessageRequest,
    PlanEmailSequenceRequest,
    PrepareEmailDeliveryRequest,
    ReviewEmailMessageRequest,
    assess_email_program,
    compose_email_message,
    plan_email_campaign,
    plan_email_message,
    plan_email_sequence,
    prepare_email_delivery,
    review_email_message,
)
from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.email_marketing import (
    EmailArtifactRef,
    EmailCampaignPlan,
    EmailDeliveryPackage,
    EmailEditorialReview,
    EmailEffectIntent,
    EmailMessageDraft,
    EmailMessagePlan,
    EmailMetricObservation,
    EmailModel,
    EmailOperationIntent,
    EmailProgramAssessment,
    EmailProofReceipt,
    EmailSequencePlan,
    ProposedEmailOperation,
)
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_simulation import (
    Shape,
    SimulatedEmailHost,
    SimulatedLoweringReceipt,
    operation_contract_digest,
    operation_identity,
)
from zeo_creator.runtime import make_context
from zeo_creator.services.email_marketing import EmailCampaignBrief, propose_operation


class EmailReferenceRun(EmailModel):
    publication: PublicationProfile
    campaign: EmailCampaignPlan
    sequence: EmailSequencePlan
    plans: tuple[EmailMessagePlan, ...]
    drafts: tuple[EmailMessageDraft, ...]
    reviews: tuple[EmailEditorialReview, ...]
    packages: tuple[EmailDeliveryPackage, ...]
    proposals: tuple[ProposedEmailOperation, ...]
    receipts: tuple[SimulatedLoweringReceipt, ...]
    observations: tuple[EmailMetricObservation, ...]
    assessment: EmailProgramAssessment


def _data[T](result: CapabilityResult[T]) -> T:
    if result.data is None:
        raise RuntimeError("Reference capability failed")
    return result.data


def _proposal(
    package: EmailDeliveryPackage, intent: EmailEffectIntent, key: str
) -> ProposedEmailOperation:
    return propose_operation(
        EmailOperationIntent(
            organization_id=package.organization_id,
            publication_id=package.publication_id,
            intent=intent,
            operation=operation_identity(intent),
            operation_contract_digest=operation_contract_digest(intent),
            delivery=package.binding(),
            delivery_approval_digest=package.approval_digest,
            audience=package.material.audience_snapshot,
        ),
        x.NOW,
        key,
    )


def run_program(
    publication: PublicationProfile,
    shape: Shape,
    campaign_name: str = "education",
    sequence_name: str = "welcome",
) -> EmailReferenceRun:
    """Caller supplies publication identity; every external effect here is simulated."""
    pub = publication.publication_id
    ctx = make_context(capability_name="email_reference")
    data = x.brief(pub).model_dump(mode="python")
    data["campaign_id"] = f"{pub}/{campaign_name}"
    campaign = _data(
        plan_email_campaign(
            PlanEmailCampaignRequest(
                publication=publication,
                brief=EmailCampaignBrief.model_validate(data),
                created_at=x.NOW,
            ),
            ctx,
        )
    ).campaign
    plans = tuple(
        _data(
            plan_email_message(
                PlanEmailMessageRequest(
                    publication=publication,
                    campaign=campaign,
                    directions=x.directions(pub, f"{campaign_name}/{name}"),
                    created_at=x.NOW,
                ),
                ctx,
            )
        ).plan
        for name in ("newsletter", "step-one", "step-two", "step-three")
    )
    sequence = _data(
        plan_email_sequence(
            PlanEmailSequenceRequest(
                campaign=campaign,
                sequence_id=f"{pub}/{sequence_name}",
                messages=plans[1:],
                delays_seconds=(0, 86400, 172800),
                policies=x.policies(pub),
                enrolment_window=campaign.campaign_window,
                required_provider_semantics=("linear", "retain_existing_revision"),
                created_at=x.NOW,
            ),
            ctx,
        )
    ).sequence
    host = SimulatedEmailHost(shape)
    drafts: list[EmailMessageDraft] = []
    reviews: list[EmailEditorialReview] = []
    packages: list[EmailDeliveryPackage] = []
    proposals: list[ProposedEmailOperation] = []
    receipts: list[SimulatedLoweringReceipt] = []
    for index, plan in enumerate(plans):
        draft = _data(
            compose_email_message(
                ComposeEmailMessageRequest(
                    plan=plan,
                    sections=x.sections(pub),
                    created_at=x.NOW,
                ),
                ctx,
            )
        ).draft
        review = _data(
            review_email_message(
                ReviewEmailMessageRequest(
                    publication=publication,
                    plan=plan,
                    draft=draft,
                    evidence=x.evidence(draft),
                    created_at=x.NOW,
                ),
                ctx,
            )
        ).review
        preview = EmailProofReceipt(
            artifact_id=f"{pub}/{campaign_name}/preview-{index}",
            created_at=x.NOW,
            organization_id=publication.organization_id,
            publication_id=pub,
            draft=draft.binding(),
            kind="preview",
            receipt_ref=f"{pub}/simulated-preview-{index}",
            personalization_resolved=True,
            successful=True,
            valid_until=x.LATER,
        )
        test_package = _data(
            prepare_email_delivery(
                PrepareEmailDeliveryRequest(
                    plan=plan,
                    draft=draft,
                    review=review,
                    audience_snapshot=x.snapshot(pub, "test"),
                    proofs=(preview,),
                    created_at=x.NOW,
                ),
                ctx,
            )
        ).package
        test_proposal = _proposal(
            test_package, EmailEffectIntent.TEST, f"{campaign_name}/test-{index}"
        )
        test_receipt = host.simulate(
            test_proposal, test_proposal.approval_digest, x.NOW, package=test_package
        )
        test_proof = EmailProofReceipt(
            artifact_id=f"{pub}/{campaign_name}/test-proof-{index}",
            created_at=x.NOW,
            organization_id=publication.organization_id,
            publication_id=pub,
            input_refs=(test_proposal.artifact_id,),
            draft=draft.binding(),
            kind="test_send",
            receipt_ref=test_receipt.receipt_id,
            audience_snapshot=x.snapshot(pub, "test"),
            personalization_resolved=True,
            successful=True,
            valid_until=x.LATER,
        )
        production_package = _data(
            prepare_email_delivery(
                PrepareEmailDeliveryRequest(
                    plan=plan,
                    draft=draft,
                    review=review,
                    audience_snapshot=x.snapshot(pub),
                    proofs=(preview, test_proof),
                    sequence=sequence if index else None,
                    created_at=x.NOW,
                ),
                ctx,
            )
        ).package
        production_proposal = _proposal(
            production_package, EmailEffectIntent.SEND, f"{campaign_name}/send-{index}"
        )
        production_receipt = host.simulate(
            production_proposal,
            production_proposal.approval_digest,
            x.NOW,
            package=production_package,
        )
        drafts.append(draft)
        reviews.append(review)
        packages.extend((test_package, production_package))
        proposals.extend((test_proposal, production_proposal))
        receipts.extend((test_receipt, production_receipt))
    # This reference host supplies already-collected aggregate observations. Creator
    # receives no subscriber events, provider response bodies or acquisition service.
    retrieval = EmailArtifactRef(
        organization_id=publication.organization_id,
        publication_id=pub,
        ref=f"{pub}/{campaign_name}/simulated-metrics-retrieval",
        revision=1,
        digest=canonical_digest(tuple(receipts)),
    )
    observation = EmailMetricObservation(
        artifact_id=f"{pub}/{campaign_name}/accepted-observation",
        created_at=x.NOW,
        organization_id=publication.organization_id,
        publication_id=pub,
        campaign=campaign.binding(),
        operation=proposals[1].binding(),
        retrieval_receipt=retrieval,
        provider_kind="simulation",
        connection_ref=f"{pub}/connection",
        aggregate_segment_ref=f"{pub}/aggregate",
        observation_window=campaign.campaign_window,
        metric="accepted",
        value=10,
        unit="count",
        provider_definition="Simulated acceptance; delivery and conversion remain unknown",
        provider_definition_version="simulation-1",
        completeness="partial",
        coverage=0.5,
        reliability="qualified",
        data_gaps=("Delivery and conversion observations have not arrived.",),
    )
    assessment = _data(
        assess_email_program(
            AssessEmailProgramRequest(
                campaign=campaign,
                observations=(observation,),
                observation_window=campaign.campaign_window,
                expected_metrics=("accepted", "delivered", "cta_conversions"),
                created_at=x.NOW,
            ),
            ctx,
        )
    ).assessment
    return EmailReferenceRun(
        publication=publication,
        campaign=campaign,
        sequence=sequence,
        plans=plans,
        drafts=tuple(drafts),
        reviews=tuple(reviews),
        packages=tuple(packages),
        proposals=tuple(proposals),
        receipts=tuple(receipts),
        observations=(observation,),
        assessment=assessment,
    )


def three_publications() -> tuple[EmailReferenceRun, ...]:
    return (
        run_program(
            x.profile("publication-a"), "hubspot-shaped", "newsletter-and-nurture", "nurture"
        ),
        run_program(x.profile("publication-b"), "kit-shaped", "membership", "lead-magnet-welcome"),
        run_program(x.profile("publication-c"), "kit-shaped", "product-interest", "orientation"),
    )


if __name__ == "__main__":
    for run in three_publications():
        print(
            f"{run.publication.publication_id}: {len(run.drafts)} messages, {len(run.proposals)} simulated proposals, {run.assessment.completeness} assessment"
        )
