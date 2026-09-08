"""Adversarial direct-model and public-boundary probes for the elders' v3 findings."""

import json
from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from tests.test_email_marketing import observation, revised
from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.email_marketing import (
    EmailEffectIntent as Intent,
)
from zeo_creator.contracts.email_marketing import (
    EmailMeasurementPopulation,
    EmailMetricName,
    EmailOperationIntent,
    EmailRemoteReceipt,
)
from zeo_creator.errors import CreatorDomainError
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_program_suite import effect_family
from zeo_creator.reference.email_workflow import remote_from_simulation, run_program
from zeo_creator.services import email_marketing as s


@pytest.fixture(scope="module")
def family():
    return effect_family(run_program(x.profile(), "hubspot-shaped"))


STATES = {
    "provisioned": Intent.PROVISION,
    "active": Intent.ACTIVATE,
    "paused": Intent.PAUSE,
    "retired": Intent.RETIRE,
}


def state_receipt(release, sequence, state):
    return x.remote_receipt(
        x.ref(f"sequence-{state}"),
        release,
        kind="sequence_revision",
        sequence=sequence,
        intent=STATES[state],
    )


@pytest.mark.parametrize(
    "intent,allowed",
    [
        (Intent.ACTIVATE, {"provisioned"}),
        (Intent.ENROL, {"active"}),
        (Intent.PAUSE, {"active"}),
        (Intent.RETIRE, {"active", "paused"}),
    ],
)
@pytest.mark.parametrize("state", STATES)
def test_sequence_prior_transition_table_is_enforced_directly(family, intent, allowed, state):
    original = next(p.material for p in family.proposals if p.material.intent == intent)
    receipt = state_receipt(original.campaign_release, original.sequence, state)
    data = original.model_dump(mode="python")
    data.update(
        prior_receipt=receipt,
        target_remote_ref=receipt.remote_ref,
        expected_remote_revision_digest=receipt.remote_revision_digest,
    )
    if state in allowed:
        assert EmailOperationIntent.model_validate(data).prior_receipt.lifecycle_state == state
    else:
        with pytest.raises(ValidationError, match="prior lifecycle state"):
            EmailOperationIntent.model_validate(data)


@pytest.mark.parametrize("state", STATES)
def test_migration_requires_paused_source_and_provisioned_target(family, state):
    material = next(p.material for p in family.proposals if p.material.intent == Intent.MIGRATE)
    source = state_receipt(
        material.prior_receipt.campaign_release, material.prior_receipt.sequence, state
    )
    data = material.model_dump(mode="python")
    data.update(
        prior_receipt=source,
        target_remote_ref=source.remote_ref,
        expected_remote_revision_digest=source.remote_revision_digest,
    )
    if state == "paused":
        assert EmailOperationIntent.model_validate(data)
    else:
        with pytest.raises(ValidationError, match="prior lifecycle state"):
            EmailOperationIntent.model_validate(data)
    target = state_receipt(material.campaign_release, material.sequence, state)
    migration = revised(material.migration, target_receipt=target)
    if state == "provisioned":
        assert revised(material, migration=migration)
    else:
        with pytest.raises(ValidationError, match="migration target"):
            revised(material, migration=migration)


def test_normalization_uses_actual_effect_and_keeps_migration_inactive(family):
    for proposal, receipt in zip(family.proposals, family.receipts, strict=True):
        if proposal.material.sequence is None:
            continue
        normalized = remote_from_simulation(proposal, receipt)
        assert normalized.operation == proposal.binding()
        assert normalized.result.intent == proposal.material.intent
        expected = {
            Intent.PROVISION: "provisioned",
            Intent.ACTIVATE: "active",
            Intent.ENROL: "active",
            Intent.PAUSE: "paused",
            Intent.MIGRATE: "provisioned",
            Intent.RETIRE: "retired",
        }
        assert normalized.lifecycle_state == expected[proposal.material.intent]
        if proposal.material.intent == Intent.MIGRATE:
            assert normalized.result.audience == proposal.material.audience
        with pytest.raises(ValueError, match="contradicts"):
            remote_from_simulation(proposal, receipt, kind="broadcast")


@pytest.mark.parametrize(
    "kind",
    ["draft", "scheduled_broadcast", "test_send", "cancelled_broadcast", "sequence_revision"],
)
@pytest.mark.parametrize("metric", get_args(EmailMetricName))
def test_non_delivery_effects_cannot_establish_production_metrics(kind, metric):
    receipt = x.remote_receipt(
        x.ref("nondelivery"),
        x.release().binding(),
        kind=kind,
        sequence=x.ref("sequence") if kind == "sequence_revision" else None,
    )
    with pytest.raises(ValidationError, match="not admissible"):
        observation(operation=receipt.operation, operation_receipt=receipt, metric=metric)
    with pytest.raises(ValidationError, match="eligible production"):
        EmailMeasurementPopulation(
            organization_id="example-org",
            publication_id="publication-a",
            release=x.release(),
            operations=(receipt,),
        )


def test_draft_receipt_cannot_complete_a_second_message_and_valid_broadcasts_can():
    release = s.finalize_campaign(x.campaign(), (x.plan(), x.plan(message="second")), (), x.NOW)
    a = x.remote_receipt(x.ref("send-a"), release.binding())
    b = x.remote_receipt(x.ref("draft-b"), release.binding(), kind="draft")
    b = revised(b, result=revised(b.result, message_plan=release.messages[1].binding()))
    with pytest.raises(ValidationError, match="eligible production"):
        EmailMeasurementPopulation(
            organization_id="example-org",
            publication_id="publication-a",
            release=release,
            operations=(a, b),
        )
    second = x.remote_receipt(x.ref("send-b"), release.binding())
    second = revised(
        second, result=revised(second.result, message_plan=release.messages[1].binding())
    )
    observations = tuple(
        observation(
            operation=r.operation,
            operation_receipt=r,
            campaign_release=release.binding(),
            artifact_id=f"obs-{i}",
            completeness="complete",
            coverage=1,
            data_gaps=(),
        )
        for i, r in enumerate((a, second))
    )
    result = s.assess_program(
        x.campaign(),
        observations,
        x.brief().window,
        ("delivered",),
        x.NOW,
        release=release,
        expected_operations=(a, second),
    )
    assert (result.completeness, result.confidence) == ("complete", "qualified")


def test_receipt_discriminator_rejects_contradictory_fields_and_test_relabeling():
    receipt = x.remote_receipt(x.ref("send"), x.release().binding())
    for change in (
        {"sequence": x.ref("seq")},
        {"intent": Intent.TEST},
        {"audience": x.snapshot(purpose="test")},
        {"kind": "sequence_revision"},
    ):
        data = receipt.model_dump(mode="python", exclude={"content_digest"})
        data["result"].update(change)
        with pytest.raises(ValidationError):
            EmailRemoteReceipt.model_validate(data)
    sequence = state_receipt(x.release().binding(), x.ref("seq"), "provisioned")
    for change in (
        {"delivery": x.ref("delivery"), "message_plan": x.plan().binding()},
        {"lifecycle_state": "active"},
        {"audience": x.snapshot()},
    ):
        data = sequence.model_dump(mode="python", exclude={"content_digest"})
        data["result"].update(change)
        with pytest.raises(ValidationError):
            EmailRemoteReceipt.model_validate(data)
    schema = EmailRemoteReceipt.model_json_schema()
    assert schema["properties"]["result"]["discriminator"]["propertyName"] == "kind"
    assert len(schema["properties"]["result"]["oneOf"]) == 6


def test_sequence_metrics_require_enrolment_and_do_not_satisfy_delivery(family):
    enrol = next(p for p in family.proposals if p.material.intent == Intent.ENROL)
    receipt = remote_from_simulation(enrol, family.receipts[family.proposals.index(enrol)])
    run = family.source
    base = run.observations[0]
    for metric in ("sequence_enrolments", "step_completion", "step_exit"):
        row = revised(base, operation=receipt.operation, operation_receipt=receipt, metric=metric)
        assert row.metric == metric
    with pytest.raises(ValidationError, match="not admissible"):
        revised(base, operation=receipt.operation, operation_receipt=receipt, metric="delivered")
    with pytest.raises(ValidationError, match="not admissible"):
        revised(base, metric="sequence_enrolments")
    population = EmailMeasurementPopulation(
        organization_id=run.release.organization_id,
        publication_id=run.release.publication_id,
        release=run.release,
        operations=(receipt, base.operation_receipt),
    )
    gaps = population.gaps((), ("delivered", "sequence_enrolments"))
    assert f"Missing operation metric: {receipt.operation.ref}/sequence_enrolments" in gaps
    assert f"Missing operation metric: {receipt.operation.ref}/delivered" not in gaps
    assert f"Missing operation metric: {base.operation.ref}/sequence_enrolments" not in gaps


def test_cta_invariants_hold_on_direct_campaign_message_and_release_construction():
    cta = x.campaign().calls_to_action[0]
    other = revised(cta, cta_id="second", link_id="second-link")
    with pytest.raises(ValidationError, match="exactly one primary"):
        revised(x.campaign(), calls_to_action=(cta, other))
    with pytest.raises(ValidationError, match="exactly one primary"):
        revised(x.campaign(), calls_to_action=(revised(cta, primary=False),))
    for duplicate in (
        revised(cta, primary=False),
        revised(cta, label="Conflicting", primary=False),
    ):
        for model in (x.campaign(), x.plan()):
            with pytest.raises(ValidationError, match="identities must be unique"):
                revised(model, calls_to_action=(cta, duplicate))
    with pytest.raises(ValidationError, match="link identities"):
        revised(x.plan(), links=(*x.plan().links, x.plan().links[0]))
    with pytest.raises(ValidationError, match="link identities"):
        revised(
            x.campaign(), calls_to_action=(cta, revised(other, link_id=cta.link_id, primary=False))
        )
    conflict = revised(x.plan(), calls_to_action=(revised(cta, label="Different definition"),))
    with pytest.raises(ValidationError, match="conflicting definitions"):
        revised(x.release(), messages=(conflict,))
    # The same declared identity may appear unchanged across different messages.
    assert s.finalize_campaign(x.campaign(), (x.plan(), x.plan(message="second")), (), x.NOW)


def test_nested_stale_artifact_has_safe_specific_error():
    release = x.release()
    bad = release.messages[0].model_copy(update={"subject_direction": "private-input-marker"})
    corrupted = release.model_copy(update={"messages": (bad,)})
    corrupted = corrupted.model_copy(update={"content_digest": canonical_digest(corrupted)})
    with pytest.raises(CreatorDomainError, match=r"^stale_email_artifact$"):
        s.current(corrupted)


def test_frozen_v3_schemas_keep_exact_raw_bytes():
    frozen = json.loads(Path("reference/email-v3-frozen.json").read_text())
    assert len(frozen["schemas"]) == 86
    for name, schema in frozen["schemas"].items():
        assert Path(name).read_text() == json.dumps(schema, indent=2, sort_keys=True) + "\n", name
