"""Independent publication programs and every effect intent through a fake host only."""

from datetime import timedelta
from typing import cast

from zeo_creator.capabilities.email_marketing import (
    ProposeEmailOperationRequest,
    propose_email_operation,
)
from zeo_creator.contracts.email_marketing import (
    EmailCampaignRelease,
    EmailDeliveryPackage,
    EmailEffectIntent,
    EmailMigrationPlan,
    EmailMigrationStep,
    EmailModel,
    EmailOperationIntent,
    EmailRemoteReceipt,
    EmailSequencePlan,
    ProposedEmailOperation,
)
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_simulation import (
    Shape,
    SimulatedEmailHost,
    SimulatedLoweringReceipt,
    operation_contract_digest,
    operation_identity,
)
from zeo_creator.reference.email_workflow import (
    EmailReferenceRun,
    remote_from_simulation,
    run_program,
)
from zeo_creator.runtime import make_context
from zeo_creator.services import email_marketing as s


class EmailEffectFamilyRun(EmailModel):
    source: EmailReferenceRun
    migration_release: EmailCampaignRelease
    proposals: tuple[ProposedEmailOperation, ...]
    receipts: tuple[SimulatedLoweringReceipt, ...]


def effect_family(run: EmailReferenceRun) -> EmailEffectFamilyRun:
    """Provisioning receipt is a supplied simulation fixture, never a real provider claim."""
    pub = run.publication.publication_id
    host = SimulatedEmailHost("hubspot-shaped" if pub == "publication-a" else "kit-shaped")
    proposals: list[ProposedEmailOperation] = []
    receipts: list[SimulatedLoweringReceipt] = []

    def propose(
        intent: EmailEffectIntent,
        *,
        package: EmailDeliveryPackage | None = None,
        sequence: EmailSequencePlan | None = None,
        release: EmailCampaignRelease = run.release,
        prior: EmailRemoteReceipt | None = None,
        migration: EmailMigrationPlan | None = None,
        source_sequence: EmailSequencePlan | None = None,
    ) -> ProposedEmailOperation:
        material = EmailOperationIntent(
            organization_id=run.publication.organization_id,
            publication_id=pub,
            execution=x.execution(pub),
            campaign_release=release.binding(),
            intent=intent,
            operation=operation_identity(intent),
            operation_contract_digest=operation_contract_digest(intent),
            delivery=package.binding() if package else None,
            delivery_approval_digest=package.approval_digest if package else None,
            audience=package.material.audience_snapshot
            if package
            else x.snapshot(pub)
            if intent in {EmailEffectIntent.ENROL, EmailEffectIntent.MIGRATE}
            else None,
            sequence=sequence.binding() if sequence else None,
            prior_receipt=prior,
            target_remote_ref=prior.remote_ref if prior else None,
            expected_remote_revision_digest=prior.remote_revision_digest if prior else None,
            migration=migration,
            migration_policy=migration.policy if migration else None,
        )
        result = propose_email_operation(
            ProposeEmailOperationRequest(
                material=material,
                release=release,
                package=package,
                sequence=sequence,
                source_sequence=source_sequence,
                idempotency_key=f"family/{intent.value}",
                created_at=x.NOW,
            ),
            make_context(capability_name="email_reference_family"),
        )
        if result.data is None:
            raise RuntimeError("Effect family proposal refused")
        proposal = result.data.proposal
        receipt = host.simulate(
            proposal,
            proposal.approval_digest,
            x.NOW,
            package=package,
            sequence=sequence,
            source_sequence=source_sequence,
            release=release,
            supported_semantics=("linear", "retain_existing_revision"),
        )
        proposals.append(proposal)
        receipts.append(receipt)
        return proposal

    production = run.packages[1]
    created = propose(EmailEffectIntent.CREATE_DRAFT, package=production)
    propose(
        EmailEffectIntent.UPDATE_DRAFT,
        package=production,
        prior=remote_from_simulation(created, receipts[0], kind="draft"),
    )
    propose(EmailEffectIntent.TEST, package=run.packages[0])
    propose(EmailEffectIntent.SEND, package=production)
    scheduled_package = s.prepare_delivery(
        run.plans[0],
        run.drafts[0],
        run.reviews[0],
        x.snapshot(pub),
        production.material.proofs,
        x.NOW,
        x.NOW + timedelta(hours=1),
        release=run.release,
        execution=x.execution(pub),
        template_mapping_digest=x.mapping_digest(pub),
    )
    scheduled = propose(EmailEffectIntent.SCHEDULE, package=scheduled_package)
    propose(
        EmailEffectIntent.CANCEL,
        prior=x.remote_receipt(
            scheduled.binding(), run.release.binding(), kind="scheduled_broadcast"
        ),
    )
    provisioned = x.remote_receipt(
        x.ref("simulated-provisioned-sequence", pub),
        run.release.binding(),
        kind="sequence_revision",
        sequence=run.sequence.binding(),
    )
    for intent in (EmailEffectIntent.ACTIVATE, EmailEffectIntent.PAUSE, EmailEffectIntent.RETIRE):
        propose(intent, sequence=run.sequence, prior=provisioned)
    propose(EmailEffectIntent.ENROL, sequence=run.sequence, prior=provisioned)
    migrated = s.plan_sequence(
        run.campaign,
        run.sequence.artifact_id,
        run.plans[1:],
        (0, 86400, 172800),
        x.policies(pub),
        run.campaign.campaign_window,
        run.sequence.required_provider_semantics,
        x.NOW,
        run.sequence,
        x.ref("migration-policy", pub),
    )
    released = s.finalize_campaign(run.campaign, run.plans, (migrated,), x.NOW)
    migration = EmailMigrationPlan(
        organization_id=run.publication.organization_id,
        publication_id=pub,
        source_sequence=run.sequence.binding(),
        target_sequence=migrated.binding(),
        enrollees=x.snapshot(pub),
        policy=x.ref("migration-policy", pub),
        steps=tuple(
            EmailMigrationStep(
                source_step=old.step_id, target_step=new.step_id, disposition="retain"
            )
            for old, new in zip(run.sequence.steps, migrated.steps, strict=True)
        ),
    )
    propose(
        EmailEffectIntent.MIGRATE,
        sequence=migrated,
        release=released,
        prior=provisioned,
        migration=migration,
        source_sequence=run.sequence,
    )
    assert host.submissions == len(EmailEffectIntent)
    return EmailEffectFamilyRun(
        source=run, migration_release=released, proposals=tuple(proposals), receipts=tuple(receipts)
    )


def publication_suite() -> tuple[EmailReferenceRun, ...]:
    """Eight separate bounded programs, with caller-owned sanitized publication intent."""
    return tuple(
        run_program(x.profile(pub), cast(Shape, shape), program, f"{program}-journey")
        for pub, shape, programs in (
            ("publication-a", "hubspot-shaped", ("weekly-newsletter", "learning-nurture")),
            (
                "publication-b",
                "kit-shaped",
                ("weekly-newsletter", "lead-magnet-welcome", "membership-campaign"),
            ),
            (
                "publication-c",
                "kit-shaped",
                ("weekly-newsletter", "orientation", "product-interest-campaign"),
            ),
        )
        for program in programs
    )


if __name__ == "__main__":
    for program in publication_suite():
        family = effect_family(program)
        print(
            f"{program.campaign.artifact_id}: {len(program.drafts)} messages; {len(family.proposals)} simulated effect intents; {program.assessment.completeness} assessment"
        )
