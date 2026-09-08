"""Installed-wheel proof: capabilities -> artifacts -> simulated host -> observations."""

from typing import Literal

from zeo_core.contracts import CapabilityResult

from zeo_creator.capabilities.email_marketing import (
    AssessEmailProgramRequest,
    ComposeEmailMessageRequest,
    FinalizeEmailCampaignRequest,
    PlanEmailCampaignRequest,
    PlanEmailMessageRequest,
    PlanEmailSequenceRequest,
    PrepareEmailDeliveryRequest,
    ProposeEmailOperationRequest,
    ReviewEmailMessageRequest,
    assess_email_program,
    compose_email_message,
    finalize_email_campaign,
    plan_email_campaign,
    plan_email_message,
    plan_email_sequence,
    prepare_email_delivery,
    propose_email_operation,
    review_email_message,
)
from zeo_creator.contracts.common import canonical_digest, stable_id
from zeo_creator.contracts.email_marketing import (
    EmailArtifactRef,
    EmailCampaignPlan,
    EmailCampaignRelease,
    EmailContentResult,
    EmailDeliveryPackage,
    EmailEditorialReview,
    EmailEffectIntent,
    EmailLoweringEvidence,
    EmailMessageDraft,
    EmailMessagePlan,
    EmailMetricObservation,
    EmailModel,
    EmailOperationIntent,
    EmailProgramAssessment,
    EmailProofReceipt,
    EmailRemoteReceipt,
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
from zeo_creator.services.email_marketing import EmailCampaignBrief


class EmailReferenceRun(EmailModel):
    publication: PublicationProfile
    campaign: EmailCampaignPlan
    release: EmailCampaignRelease
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
    package: EmailDeliveryPackage,
    intent: EmailEffectIntent,
    key: str,
    release: EmailCampaignRelease,
) -> ProposedEmailOperation:
    return _data(
        propose_email_operation(
            ProposeEmailOperationRequest(
                material=EmailOperationIntent(
                    organization_id=package.organization_id,
                    publication_id=package.publication_id,
                    execution=package.material.execution,
                    campaign_release=release.binding(),
                    intent=intent,
                    operation=operation_identity(intent),
                    operation_contract_digest=operation_contract_digest(intent),
                    delivery=package.binding(),
                    delivery_approval_digest=package.approval_digest,
                    audience=package.material.audience_snapshot,
                ),
                created_at=x.NOW,
                idempotency_key=key,
                release=release,
                package=package,
            ),
            make_context(capability_name="email_reference"),
        )
    ).proposal


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
    data["objective"] = (
        f"Support {campaign_name.replace(chr(45), chr(32))} through consented education"
    )
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
    release = _data(
        finalize_email_campaign(
            FinalizeEmailCampaignRequest(
                campaign=campaign,
                messages=plans,
                sequences=(sequence,),
                created_at=x.NOW,
            ),
            ctx,
        )
    ).release
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
            lowering=x.lowering_evidence(draft, "test"),
            personalization_resolved=True,
            successful=True,
            valid_until=x.LATER,
        )
        test_package = _data(
            prepare_email_delivery(
                PrepareEmailDeliveryRequest(
                    release=release,
                    execution=x.execution(pub),
                    template_mapping_digest=x.mapping_digest(pub),
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
            test_package, EmailEffectIntent.TEST, f"{campaign_name}/test-{index}", release
        )
        test_receipt = host.simulate(
            test_proposal,
            test_proposal.approval_digest,
            x.NOW,
            package=test_package,
            release=release,
        )
        test_proof = EmailProofReceipt(
            artifact_id=f"{pub}/{campaign_name}/test-proof-{index}",
            created_at=x.NOW,
            organization_id=publication.organization_id,
            publication_id=pub,
            input_refs=(test_proposal.artifact_id,),
            draft=draft.binding(),
            kind="test_send",
            lowering=lowering_from_test(test_receipt, test_package),
            audience_snapshot=x.snapshot(pub, "test"),
            personalization_resolved=True,
            successful=True,
            valid_until=x.LATER,
        )
        production_package = _data(
            prepare_email_delivery(
                PrepareEmailDeliveryRequest(
                    release=release,
                    execution=x.execution(pub),
                    template_mapping_digest=x.mapping_digest(pub),
                    plan=plan,
                    draft=draft,
                    review=review,
                    audience_snapshot=x.snapshot(pub),
                    proofs=(x.proofs(draft)[0], test_proof),
                    sequence=sequence if index else None,
                    created_at=x.NOW,
                ),
                ctx,
            )
        ).package
        production_proposal = _proposal(
            production_package, EmailEffectIntent.SEND, f"{campaign_name}/send-{index}", release
        )
        production_receipt = host.simulate(
            production_proposal,
            production_proposal.approval_digest,
            x.NOW,
            package=production_package,
            release=release,
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
        campaign_release=release.binding(),
        operation_receipt=remote_from_simulation(proposals[1], receipts[1], package=packages[1]),
        retrieval_receipt=retrieval,
        provider_kind=x.execution(pub).provider_kind,
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
                release=release,
                campaign=campaign,
                observations=(observation,),
                observation_window=campaign.campaign_window,
                expected_metrics=("accepted", "delivered", "cta_conversions"),
                expected_operations=tuple(
                    remote_from_simulation(proposals[i], receipts[i], package=packages[i])
                    for i in range(1, len(proposals), 2)
                ),
                created_at=x.NOW,
            ),
            ctx,
        )
    ).assessment
    return EmailReferenceRun(
        publication=publication,
        campaign=campaign,
        release=release,
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


def lowering_from_test(
    receipt: SimulatedLoweringReceipt, package: EmailDeliveryPackage
) -> EmailLoweringEvidence:
    if (
        receipt.outcome != "accepted"
        or receipt.creator_artifact != package.binding()
        or receipt.provider_observed_payload_digest != receipt.submitted_payload_digest
    ):
        raise ValueError("test simulation did not confirm exact material")
    draft = package.material.draft
    data = x.lowering_evidence(draft, "test").model_dump(mode="python", exclude={"content_digest"})
    data.update(
        receipt=EmailArtifactRef(
            organization_id=package.organization_id,
            publication_id=package.publication_id,
            ref=receipt.receipt_id,
            revision=1,
            digest=canonical_digest(receipt),
        ),
        submitted_payload_digest=receipt.submitted_payload_digest,
        observed_payload_digest=receipt.provider_observed_payload_digest,
    )
    return EmailLoweringEvidence.model_validate(data)


def remote_from_simulation(
    proposal: ProposedEmailOperation,
    receipt: SimulatedLoweringReceipt,
    kind: Literal[
        "draft",
        "scheduled_broadcast",
        "sequence_revision",
        "broadcast",
        "test_send",
        "cancelled_broadcast",
    ]
    | None = None,
    *,
    package: EmailDeliveryPackage | None = None,
) -> EmailRemoteReceipt:
    if (
        receipt.outcome != "accepted"
        or receipt.provider_observed_payload_digest is None
        or receipt.idempotency_identity != proposal.idempotency_key
        or receipt.receipt_id != stable_id("simulated_receipt", proposal.approval_digest)
        or receipt.creator_artifact
        != (proposal.material.delivery or proposal.material.sequence or proposal.binding())
    ):
        raise ValueError("simulation receipt did not confirm the logical operation")
    if proposal.material.delivery and (
        package is None or package.binding() != proposal.material.delivery
    ):
        raise ValueError("simulation receipt requires the exact delivery package")
    expected_kind = {
        EmailEffectIntent.CREATE_DRAFT: "draft",
        EmailEffectIntent.UPDATE_DRAFT: "draft",
        EmailEffectIntent.SEND: "broadcast",
        EmailEffectIntent.SCHEDULE: "scheduled_broadcast",
        EmailEffectIntent.TEST: "test_send",
        EmailEffectIntent.CANCEL: "cancelled_broadcast",
    }.get(proposal.material.intent, "sequence_revision")
    if kind is not None and kind != expected_kind:
        raise ValueError("simulation receipt kind contradicts the originating effect")
    base = x.remote_receipt(
        proposal.binding(),
        proposal.material.campaign_release,
        kind=expected_kind,  # type: ignore[arg-type]
        sequence=proposal.material.sequence,
        intent=proposal.material.intent,
        audience=package.material.audience_snapshot if package else proposal.material.audience,
    )
    data = base.model_dump(mode="python", exclude={"content_digest"})
    if isinstance(base.result, EmailContentResult):
        prior = proposal.material.prior_receipt
        data["result"].update(
            delivery=package.binding() if package else prior.delivery if prior else None,
            message_plan=package.material.draft.message_plan
            if package
            else prior.message_plan
            if prior
            else None,
            audience=package.material.audience_snapshot
            if package
            else prior.result.audience
            if prior
            else None,
        )
    data.update(
        artifact_id=receipt.receipt_id,
        remote_ref=receipt.remote_ref,
        execution=proposal.material.execution,
        remote_revision_digest=receipt.provider_observed_payload_digest,
    )
    return EmailRemoteReceipt.model_validate(data)


if __name__ == "__main__":
    for run in three_publications():
        print(
            f"{run.publication.publication_id}: {len(run.drafts)} messages, {len(run.proposals)} simulated proposals, {run.assessment.completeness} assessment"
        )
