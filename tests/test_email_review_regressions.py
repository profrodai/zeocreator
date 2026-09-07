"""Independent counterexamples from the two external reviews of merged PR 2."""

import json
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from zeo_core.contracts import CapabilityStatus

from tests.test_email_marketing import observation, package, proposal, reviewed, revised, sequence
from zeo_creator.capabilities.email_marketing import (
    PrepareEmailDeliveryRequest,
    prepare_email_delivery,
)
from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.email_marketing import EmailEffectIntent, EmailLink, EmailOperationIntent
from zeo_creator.errors import CreatorDomainError
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_program_suite import effect_family, publication_suite
from zeo_creator.reference.email_simulation import (
    SimulatedEmailHost,
    operation_contract_digest,
    operation_identity,
)
from zeo_creator.runtime import make_context
from zeo_creator.services import email_marketing as s


def delivery_options():
    return dict(
        release=x.release(), execution=x.execution(), template_mapping_digest=x.mapping_digest()
    )


def test_retry_key_requires_its_own_approval_and_receipt():
    item = package()
    first, second = proposal(item, key="first"), proposal(item, key="second")
    assert first.approval_digest != second.approval_digest
    host = SimulatedEmailHost("hubspot-shaped")
    receipt = host.simulate(first, first.approval_digest, x.NOW, package=item, release=x.release())
    with pytest.raises(CreatorDomainError, match="approval_mismatch"):
        host.simulate(second, first.approval_digest, x.NOW, package=item, release=x.release())
    assert host.submissions == 1
    assert (
        host.simulate(first, first.approval_digest, x.LATER, package=item, release=x.release())
        == receipt
    )


@pytest.mark.parametrize(
    "field",
    ["account_ref", "connection_ref", "connector_revision", "provider_kind", "lowering_profile"],
)
def test_execution_namespace_is_approval_material(field):
    op = proposal(package())
    value = x.ref("other-lowering") if field == "lowering_profile" else "other-context"
    material = revised(op.material, execution=revised(op.material.execution, **{field: value}))
    from zeo_creator.contracts.email_marketing import effect_approval_digest

    assert effect_approval_digest(material, op.idempotency_key) != op.approval_digest
    with pytest.raises(CreatorDomainError):
        s.propose_operation(
            material, x.NOW, op.idempotency_key, release=x.release(), package=package()
        )


@pytest.mark.parametrize("purpose,count", [("test", 10), ("production", 100000)])
def test_creator_refuses_production_proposal_over_wrong_package(purpose, count):
    item = package(purpose=purpose)
    intent = EmailEffectIntent.SEND
    material = EmailOperationIntent(
        organization_id=item.organization_id,
        publication_id=item.publication_id,
        execution=x.execution(),
        campaign_release=x.release().binding(),
        intent=intent,
        operation=operation_identity(intent),
        operation_contract_digest=operation_contract_digest(intent),
        delivery=item.binding(),
        delivery_approval_digest=item.approval_digest,
        audience=revised(x.snapshot(), eligible_count=count),
    )
    with pytest.raises(CreatorDomainError, match="delivery_or_audience_changed"):
        s.propose_operation(material, x.NOW, "bypass", package=item, release=x.release())


@pytest.mark.parametrize(
    "intent,schedule",
    [(EmailEffectIntent.SCHEDULE, None), (EmailEffectIntent.SEND, x.NOW + timedelta(hours=1))],
)
def test_creator_enforces_schedule_semantics(intent, schedule):
    with pytest.raises(CreatorDomainError, match="schedule"):
        proposal(package(schedule=schedule), intent)


def test_concrete_delivery_is_required_even_with_valid_references():
    op = proposal(package())
    with pytest.raises(CreatorDomainError, match="package_required"):
        s.propose_operation(op.material, x.NOW, "ref-only", release=x.release())


def enrolment(seq, snapshot):
    messages = tuple(x.plan(message=f"step-{i}") for i in range(3))
    released = s.finalize_campaign(x.campaign(), messages, (seq,), x.NOW)
    prior = x.remote_receipt(
        x.ref("provisioned-sequence"),
        released.binding(),
        kind="sequence_revision",
        sequence=seq.binding(),
    )
    intent = EmailEffectIntent.ENROL
    material = EmailOperationIntent(
        organization_id=seq.organization_id,
        publication_id=seq.publication_id,
        execution=x.execution(),
        campaign_release=released.binding(),
        intent=intent,
        operation=operation_identity(intent),
        operation_contract_digest=operation_contract_digest(intent),
        sequence=seq.binding(),
        audience=snapshot,
        prior_receipt=prior,
        target_remote_ref=prior.remote_ref,
        expected_remote_revision_digest=prior.remote_revision_digest,
    )
    return material, released


@pytest.mark.parametrize(
    "change",
    [
        dict(audience_intent_digest=canonical_digest("wrong")),
        dict(consent_policy_digest=canonical_digest("wrong")),
        dict(suppression_policy_digest=canonical_digest("wrong")),
        dict(resolved_at=x.NOW - timedelta(days=400)),
    ],
)
def test_sequence_enrolment_checks_audience_and_snapshot_resolution_window(change):
    seq = sequence()
    material, released = enrolment(seq, revised(x.snapshot(), **change))
    with pytest.raises(CreatorDomainError):
        s.propose_operation(material, x.NOW, "enrol", release=released, sequence=seq)


def test_enrolment_window_has_exclusive_end():
    seq = revised(
        sequence(),
        maximum_enrolment_window=revised(x.brief().window, ends_at=x.NOW + timedelta(hours=1)),
    )
    material, released = enrolment(seq, x.snapshot())
    with pytest.raises(CreatorDomainError, match="window_closed"):
        s.propose_operation(
            material, x.NOW + timedelta(hours=1), "enrol", release=released, sequence=seq
        )


def test_release_is_acyclic_and_membership_changes_invalidate_delivery():
    release = x.release()
    changed = s.finalize_campaign(
        x.campaign(), (*release.messages, x.plan(message="second")), (), x.NOW
    )
    assert changed.content_digest != release.content_digest
    assert changed.campaign == release.campaign
    op = proposal(package())
    with pytest.raises(CreatorDomainError, match="release_mismatch"):
        s.propose_operation(
            op.material, x.NOW, "different-release", release=changed, package=package()
        )
    with pytest.raises(ValidationError):
        revised(release, messages=())


@pytest.mark.parametrize(
    "mutation",
    [
        "execution",
        "sender_identity",
        "template_mapping_digest",
        "covered_snapshot_digest",
        "covered_tokens",
        "draft",
        "outcome",
    ],
)
def test_lowering_provenance_changes_refuse_delivery(mutation):
    plan, draft, review = reviewed()
    proof = x.proofs(draft)[0]
    values = dict(
        execution=revised(x.execution(), account_ref="other-account"),
        sender_identity=x.ref("other-sender"),
        template_mapping_digest=canonical_digest("different"),
        covered_snapshot_digest=canonical_digest("other-snapshot"),
        covered_tokens=("extra",),
        draft=x.ref("other-draft"),
        outcome="needs_review",
    )
    proof = revised(proof, lowering=revised(proof.lowering, **{mutation: values[mutation]}))
    with pytest.raises(CreatorDomainError, match="provenance"):
        s.prepare_delivery(
            plan,
            draft,
            review,
            x.snapshot(),
            (proof, x.proofs(draft)[1]),
            x.NOW,
            **delivery_options(),
        )


def test_production_preview_is_allowed_while_test_audience_must_be_distinct():
    plan, draft, review = reviewed()
    preview, test = x.proofs(draft)
    preview = revised(preview, audience_snapshot=x.snapshot())
    assert s.prepare_delivery(
        plan, draft, review, x.snapshot(), (preview, test), x.NOW, **delivery_options()
    )
    test = revised(
        test,
        audience_snapshot=revised(
            x.snapshot("publication-a", "test"), snapshot_digest=x.snapshot().snapshot_digest
        ),
    )
    with pytest.raises(CreatorDomainError, match="test_audience_must_differ"):
        s.prepare_delivery(
            plan, draft, review, x.snapshot(), (preview, test), x.NOW, **delivery_options()
        )


def test_accessibility_requires_evidence_even_for_allowlisted_html():
    draft = x.draft()
    evidence = tuple(row for row in x.evidence(draft) if row.check != "accessibility")
    review = s.review_message(x.profile(), x.plan(), draft, evidence, x.NOW)
    assert (
        next(row.status for row in review.findings if row.check == "accessibility")
        == "human_needed"
    )


@pytest.mark.parametrize("mutation", ["swap", "plain-label"])
def test_cta_and_unsubscribe_anchor_relationships_are_checked(mutation):
    draft = x.draft()
    if mutation == "swap":
        html = (
            draft.html.replace('href="https://example.org/guide"', 'href="TEMP"')
            .replace('href="https://example.org/preferences"', 'href="https://example.org/guide"')
            .replace('href="TEMP"', 'href="https://example.org/preferences"')
        )
    else:
        html = draft.html.replace(
            '<a href="https://example.org/guide">Read the guide</a>', "Read the guide"
        )
    draft = revised(draft, html=html)
    review = s.review_message(x.profile(), x.plan(), draft, x.evidence(draft), x.NOW)
    assert next(row.status for row in review.findings if row.check == "cta") == "blocked"
    assert not review.ready_for_human_approval


def test_primary_cta_can_be_second_but_cannot_be_unsubscribe():
    directions = x.directions()
    secondary = revised(
        directions.calls_to_action[0], cta_id="secondary", primary=False, desired_action="Secondary"
    )
    directions = revised(directions, calls_to_action=(secondary, directions.calls_to_action[0]))
    plan = s.plan_message(x.profile(), x.campaign(), directions, x.NOW)
    seq = s.plan_sequence(
        x.campaign(), "welcome", (plan,), (0,), x.policies(), x.brief().window, ("linear",), x.NOW
    )
    assert seq.steps[0].desired_audience_action == "Read"
    with pytest.raises(ValidationError):
        revised(plan, calls_to_action=(secondary,))
    with pytest.raises(ValidationError):
        revised(
            plan, calls_to_action=(revised(directions.calls_to_action[1], link_id="unsubscribe"),)
        )


@pytest.mark.parametrize(
    "url", ["https://youtube.com/watch?v=abc123#t=30", "https://example.org/guide?page=2#section"]
)
def test_ordinary_query_parameters_and_fragments_are_accepted(url):
    assert EmailLink(link_id="video", url=url, purpose="cta", tracking_required=False).url == url


@pytest.mark.parametrize(
    "query",
    [
        "utm_source=x",
        "subscriber_id=123",
        "email=redacted",
        "contact_id=123",
        "mc_eid=123",
        "gclid=x",
    ],
)
def test_tracking_and_subscriber_query_parameters_are_refused(query):
    with pytest.raises(ValidationError):
        EmailLink(
            link_id="bad",
            url=f"https://example.org/?{query}",
            purpose="cta",
            tracking_required=False,
        )


def test_assessment_retains_expectations_window_and_descriptive_values():
    row = observation(completeness="complete", coverage=1, data_gaps=())
    result = s.assess_program(
        x.campaign(), (row,), x.brief().window, ("delivered",), x.NOW, release=x.release()
    )
    assert result.expected_metrics == ("delivered",)
    assert any("delivered: 8 count" in text for text in result.conclusions)
    assert result.stopping_conditions[0].status == "human_needed"
    assert result.completeness == "complete"
    with pytest.raises(ValidationError):
        revised(result, expected_metrics=("delivered", "cta_conversions"))
    with pytest.raises(ValidationError):
        revised(result, observation_window=revised(result.observation_window, ends_at=x.LATER))
    with pytest.raises(ValidationError):
        observation(unit="ratio", value=2, numerator=4, denominator=2)
    other = revised(row, artifact_id="conflicting-row", value=99)
    conflict = s.assess_program(
        x.campaign(), (row, other), x.brief().window, ("delivered",), x.NOW, release=x.release()
    )
    assert conflict.confidence == "limited" and any(
        "Conflicting" in gap for gap in conflict.data_gaps
    )
    with pytest.raises(ValidationError):
        s.assess_program(
            x.campaign(),
            (row, revised(other, aggregate_segment_ref="other-cohort")),
            x.brief().window,
            ("delivered",),
            x.NOW,
            release=x.release(),
        )


def test_safe_refusal_reason_survives_capability_envelope():
    plan, draft, review = reviewed()
    request = PrepareEmailDeliveryRequest(
        plan=plan,
        draft=draft,
        review=review,
        audience_snapshot=revised(x.snapshot(), eligible_count=0),
        proofs=x.proofs(draft),
        created_at=x.NOW,
        **delivery_options(),
    )
    result = prepare_email_delivery(request, make_context(capability_name="review-regression"))
    assert result.status == CapabilityStatus.error
    assert "audience_snapshot_drift_or_empty" in result.model_dump_json()


def test_original_email_v1_schemas_remain_frozen():
    archive = json.loads(Path("reference/email-v1-frozen.json").read_text())
    for path, schema in archive["schemas"].items():
        assert json.loads(Path(path).read_text()) == schema


def test_eight_independent_programs_and_every_effect_intent():
    runs = publication_suite()
    assert len(runs) == 8 and len({row.campaign.artifact_id for row in runs}) == 8
    assert len({row.campaign.business_objective for row in runs}) >= 6
    for pub in ("publication-a", "publication-b", "publication-c"):
        run = next(row for row in runs if row.publication.publication_id == pub)
        family = effect_family(run)
        assert {row.material.intent for row in family.proposals} == set(EmailEffectIntent)
        assert len({row.approval_digest for row in family.proposals}) == 11
        migration = next(
            row for row in family.proposals if row.material.intent == EmailEffectIntent.MIGRATE
        )
        assert migration.material.migration.source_sequence == run.sequence.binding()
        assert (
            migration.material.migration.target_sequence
            == family.migration_release.sequences[0].binding()
        )
        activation = next(
            row for row in family.proposals if row.material.intent == EmailEffectIntent.ACTIVATE
        )
        with pytest.raises(ValidationError):
            revised(
                activation.material,
                migration=migration.material.migration,
                migration_policy=migration.material.migration_policy,
            )
        cancel = next(
            row for row in family.proposals if row.material.intent == EmailEffectIntent.CANCEL
        )
        with pytest.raises(ValidationError):
            revised(
                cancel.material,
                prior_receipt=revised(cancel.material.prior_receipt, kind="broadcast"),
            )
