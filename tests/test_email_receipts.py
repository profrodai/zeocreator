"""Receipt correspondence is independent of provider execution and issuer authentication."""

from datetime import timedelta

import pytest

from tests.test_email_marketing import revised
from zeo_creator.contracts.email_marketing import EmailEffectIntent as Intent
from zeo_creator.errors import CreatorDomainError
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_program_suite import effect_family
from zeo_creator.reference.email_workflow import remote_from_simulation, run_program
from zeo_creator.services.email_receipts import validate_operation_receipt


@pytest.fixture(scope="module")
def program():
    return run_program(x.profile(), "hubspot-shaped")


@pytest.fixture(scope="module")
def family(program):
    return effect_family(program)


def test_all_content_and_sequence_receipts_bind_actual_origin_and_target(program, family):
    for i, proposal in enumerate(program.proposals):
        receipt = remote_from_simulation(proposal, program.receipts[i], package=program.packages[i])
        assert validate_operation_receipt(proposal, receipt, package=program.packages[i]) == receipt
    for i, proposal in enumerate(family.proposals):
        if not proposal.material.sequence:
            continue
        receipt = remote_from_simulation(proposal, family.receipts[i])
        assert validate_operation_receipt(proposal, receipt) == receipt
        if proposal.material.intent == Intent.MIGRATE:
            assert receipt.remote_ref == proposal.material.migration.target_receipt.remote_ref
            assert receipt.remote_ref != proposal.material.prior_receipt.remote_ref
            with pytest.raises(CreatorDomainError, match="receipt_remote_target_mismatch"):
                validate_operation_receipt(
                    proposal,
                    revised(receipt, remote_ref=proposal.material.prior_receipt.remote_ref),
                )


@pytest.mark.parametrize(
    "mutation",
    [
        "operation",
        "campaign_release",
        "execution",
        "created_at",
        "intent",
        "message_plan",
        "audience",
        "delivery",
    ],
)
def test_mutated_receipt_claims_refuse_even_with_fresh_digests(program, mutation):
    proposal = program.proposals[1]
    package = program.packages[1]
    receipt = remote_from_simulation(proposal, program.receipts[1], package=package)
    if mutation == "operation":
        bad = revised(receipt, operation=program.proposals[3].binding())
    elif mutation == "campaign_release":
        bad = revised(receipt, campaign_release=x.ref("different-release"))
    elif mutation == "execution":
        bad = revised(receipt, execution=revised(receipt.execution, account_ref="other-account"))
    elif mutation == "created_at":
        bad = revised(receipt, created_at=proposal.created_at - timedelta(seconds=1))
    elif mutation == "intent":
        data = receipt.model_dump(mode="python", exclude={"content_digest"})
        data["result"].update(kind="draft", intent=Intent.CREATE_DRAFT)
        bad = type(receipt).model_validate(data)
    else:
        value = {
            "message_plan": program.plans[1].binding(),
            "delivery": program.packages[3].binding(),
            "audience": revised(package.material.audience_snapshot, eligible_count=9),
        }[mutation]
        bad = revised(receipt, result=revised(receipt.result, **{mutation: value}))
    with pytest.raises(CreatorDomainError, match=r"receipt_.*_mismatch"):
        validate_operation_receipt(proposal, bad, package=package)


def test_historical_consumption_preserves_uncertainty_and_does_not_reauthorize(program):
    proposal = program.proposals[1]
    package = program.packages[1]
    receipt = remote_from_simulation(proposal, program.receipts[1], package=package)
    for outcome in ("ambiguous", "needs_review", "confirmed"):
        later = revised(receipt, created_at=x.LATER + timedelta(days=1), outcome=outcome)
        assert validate_operation_receipt(proposal, later, package=package).outcome == outcome
    with pytest.raises(CreatorDomainError, match="receipt_delivery_package_required"):
        validate_operation_receipt(proposal, receipt)
    with pytest.raises(CreatorDomainError, match="receipt_delivery_package_mismatch"):
        validate_operation_receipt(proposal, receipt, package=program.packages[3])


def test_cancellation_receipt_consumption_keeps_original_delivery(family):
    proposal = next(p for p in family.proposals if p.material.intent == Intent.CANCEL)
    receipt = remote_from_simulation(proposal, family.receipts[family.proposals.index(proposal)])
    assert receipt.delivery == proposal.material.target_delivery
    assert validate_operation_receipt(proposal, receipt) == receipt
    with pytest.raises(CreatorDomainError, match="receipt_remote_target_mismatch"):
        validate_operation_receipt(proposal, revised(receipt, remote_ref="other-broadcast"))


def test_sequence_receipt_cannot_claim_another_sequence_or_audience(family):
    proposal = next(p for p in family.proposals if p.material.intent == Intent.ENROL)
    receipt = remote_from_simulation(proposal, family.receipts[family.proposals.index(proposal)])
    for change in (
        {"sequence": x.ref("another-sequence")},
        {"audience": revised(receipt.result.audience, eligible_count=9)},
    ):
        bad = revised(receipt, result=revised(receipt.result, **change))
        with pytest.raises(CreatorDomainError, match="receipt_sequence_binding_mismatch"):
            validate_operation_receipt(proposal, bad)
