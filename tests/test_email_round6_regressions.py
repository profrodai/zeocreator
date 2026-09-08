"""Proposal preparation must reject same-kind receipts with contradictory effects."""

import pytest
from zeo_core.contracts import CapabilityStatus

from tests.test_email_marketing import revised
from zeo_creator.capabilities.email_marketing import (
    ProposeEmailOperationRequest,
    propose_email_operation,
)
from zeo_creator.contracts.email_marketing import EmailEffectIntent as Intent
from zeo_creator.errors import CreatorDomainError
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_program_suite import effect_family
from zeo_creator.reference.email_workflow import remote_from_simulation, run_program
from zeo_creator.runtime import make_context
from zeo_creator.services import email_marketing as service


@pytest.fixture(scope="module")
def family():
    return effect_family(run_program(x.profile(), "hubspot-shaped"))


@pytest.mark.parametrize("origin_intent", [Intent.CREATE_DRAFT, Intent.UPDATE_DRAFT])
@pytest.mark.parametrize("contradictory", [True, False])
def test_origin_receipt_effect_is_exact_through_service_and_capability(
    family, origin_intent, contradictory
):
    origin = next(p for p in family.proposals if p.material.intent == origin_intent)
    package = family.source.packages[1]
    prior = remote_from_simulation(
        origin, family.receipts[family.proposals.index(origin)], package=package
    )
    if contradictory:
        other = Intent.UPDATE_DRAFT if origin_intent == Intent.CREATE_DRAFT else Intent.CREATE_DRAFT
        prior = revised(prior, result=revised(prior.result, intent=other))
    template = next(
        p.material for p in family.proposals if p.material.intent == Intent.UPDATE_DRAFT
    )
    material = revised(
        template,
        prior_receipt=prior,
        originating_operation=origin.binding(),
        target_delivery=origin.material.delivery,
        target_remote_ref=prior.remote_ref,
        expected_remote_revision_digest=prior.remote_revision_digest,
    )
    options = dict(release=family.source.release, package=package, originating_operation=origin)
    if contradictory:
        with pytest.raises(CreatorDomainError, match="originating_operation_effect_mismatch"):
            service.propose_operation(material, x.NOW, "wrong-effect", **options)
    else:
        assert service.propose_operation(material, x.NOW, "matching-effect", **options)
    response = propose_email_operation(
        ProposeEmailOperationRequest(
            material=material, created_at=x.NOW, idempotency_key="public-effect-check", **options
        ),
        make_context(capability_name="receipt-effect-regression"),
    )
    if contradictory:
        assert response.status == CapabilityStatus.error
        assert response.data is None
        assert "originating_operation_effect_mismatch" in response.model_dump_json()
    else:
        assert response.status == CapabilityStatus.success
        assert response.data is not None
