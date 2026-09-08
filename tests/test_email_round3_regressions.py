"""Reproduce the remaining packet-02 review findings through supported and direct paths."""

import json
import warnings
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.test_email_marketing import observation, revised
from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.email_marketing import (
    EmailEffectIntent,
    EmailMeasurementPopulation,
    EmailOperationIntent,
    EmailProofReceipt,
    EmailReviewEvidence,
    PersonalizationDeclaration,
)
from zeo_creator.errors import CreatorDomainError
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_program_suite import effect_family
from zeo_creator.reference.email_simulation import (
    SimulatedEmailHost,
    operation_contract_digest,
    operation_identity,
)
from zeo_creator.reference.email_workflow import remote_from_simulation, run_program
from zeo_creator.services import email_marketing as s


@pytest.fixture(scope="module")
def program():
    return run_program(x.profile(), "hubspot-shaped")


@pytest.fixture(scope="module")
def family(program):
    return effect_family(program)


def test_sequence_provisioning_produces_the_activation_and_migration_receipts(family):
    intents = [row.material.intent for row in family.proposals]
    assert set(intents) == set(EmailEffectIntent)
    assert intents.count(EmailEffectIntent.PROVISION) == 2
    for proposal in family.proposals:
        if proposal.material.intent == EmailEffectIntent.ACTIVATE:
            prior = proposal.material.prior_receipt
            source = next(row for row in family.proposals if row.binding() == prior.operation)
            assert source.material.intent == EmailEffectIntent.PROVISION
            assert source.material.sequence == proposal.material.sequence == prior.sequence
            receipt = family.receipts[family.proposals.index(source)]
            assert receipt.remote_ref == prior.remote_ref
        if proposal.material.intent == EmailEffectIntent.MIGRATE:
            target = proposal.material.migration.target_receipt
            source = next(row for row in family.proposals if row.binding() == target.operation)
            assert source.material.intent == EmailEffectIntent.PROVISION
            assert source.material.sequence == target.sequence == proposal.material.sequence


def content_intent(package, kind, *, original=None, prior=None):
    return EmailOperationIntent(
        organization_id=package.organization_id,
        publication_id=package.publication_id,
        execution=package.material.execution,
        campaign_release=package.material.campaign_release,
        intent=kind,
        operation=operation_identity(kind),
        operation_contract_digest=operation_contract_digest(kind),
        delivery=package.binding(),
        delivery_approval_digest=package.approval_digest,
        audience=package.material.audience_snapshot if kind == EmailEffectIntent.SCHEDULE else None,
        originating_operation=original.binding() if original else None,
        target_delivery=original.material.delivery if original else None,
        prior_receipt=prior,
        target_remote_ref=prior.remote_ref if prior else None,
        expected_remote_revision_digest=prior.remote_revision_digest if prior else None,
    )


def make_package(program, index, *, schedule=None, draft=None):
    plan = program.plans[index]
    draft = draft or program.drafts[index]
    review = s.review_message(program.publication, plan, draft, x.evidence(draft), x.NOW)
    return s.prepare_delivery(
        plan,
        draft,
        review,
        x.snapshot(),
        x.proofs(draft),
        x.NOW,
        schedule,
        release=program.release,
        execution=x.execution(),
        template_mapping_digest=x.mapping_digest(),
    )


@pytest.mark.parametrize("kind", [EmailEffectIntent.CANCEL, EmailEffectIntent.UPDATE_DRAFT])
def test_another_deliveries_receipt_cannot_authorize_a_mutation(program, kind):
    origin_kind = (
        EmailEffectIntent.SCHEDULE
        if kind == EmailEffectIntent.CANCEL
        else EmailEffectIntent.CREATE_DRAFT
    )
    packages = tuple(
        make_package(
            program,
            index,
            schedule=x.NOW + timedelta(hours=1) if kind == EmailEffectIntent.CANCEL else None,
        )
        for index in (0, 1)
    )
    originals = []
    priors = []
    host = SimulatedEmailHost("hubspot-shaped")
    for index, package in enumerate(packages):
        original = s.propose_operation(
            content_intent(package, origin_kind),
            x.NOW,
            f"origin-{index}",
            release=program.release,
            package=package,
        )
        receipt = host.simulate(
            original, original.approval_digest, x.NOW, release=program.release, package=package
        )
        originals.append(original)
        priors.append(
            remote_from_simulation(
                original,
                receipt,
                kind="scheduled_broadcast" if kind == EmailEffectIntent.CANCEL else "draft",
                package=package,
            )
        )
    # An A origin reference with B receipt fails before a service is invoked.
    with pytest.raises(ValidationError, match="originating operation"):
        content_intent(packages[0], kind, original=originals[0], prior=priors[1])
    # Relabel every target as B while retaining A's new/editorial material.
    with pytest.raises((ValidationError, CreatorDomainError)):
        material = content_intent(packages[0], kind, original=originals[1], prior=priors[1])
        s.propose_operation(
            material,
            x.NOW,
            "wrong-target",
            release=program.release,
            package=packages[0],
            originating_operation=originals[1],
        )
    material = content_intent(packages[0], kind, original=originals[0], prior=priors[0])
    with pytest.raises(CreatorDomainError, match="originating_operation_required"):
        s.propose_operation(
            material, x.NOW, "no-origin", release=program.release, package=packages[0]
        )
    # Cancellation remains possible after the original audience/proofs expire.
    at = x.LATER + timedelta(seconds=1) if kind == EmailEffectIntent.CANCEL else x.NOW
    assert s.propose_operation(
        material,
        at,
        "valid-target",
        release=program.release,
        package=packages[0],
        originating_operation=originals[0],
    )
    if kind == EmailEffectIntent.UPDATE_DRAFT:
        draft = s.compose_message(
            program.plans[0],
            (revised(x.sections()[0], text="A corrected educational explanation."),),
            x.NOW,
        )
        changed = make_package(program, 0, draft=draft)
        assert changed.binding() != packages[0].binding()
        update = content_intent(changed, kind, original=originals[0], prior=priors[0])
        assert s.propose_operation(
            update,
            x.NOW,
            "new-content",
            release=program.release,
            package=changed,
            originating_operation=originals[0],
        )


@pytest.mark.parametrize("required", [True, False])
def test_editorial_review_does_not_claim_preview_or_test_delivery_checks(required):
    plan = revised(x.plan(), preview_required=required, test_send_required=required)
    draft = s.compose_message(plan, x.sections(), x.NOW)
    review = s.review_message(x.profile(), plan, draft, x.evidence(draft), x.NOW)
    assert review.ready_for_human_approval
    assert not {"preview", "test_send"} & {row.check for row in review.findings}
    release = s.finalize_campaign(x.campaign(), (plan,), (), x.NOW)
    options = dict(
        release=release, execution=x.execution(), template_mapping_digest=x.mapping_digest()
    )
    if required:
        with pytest.raises(CreatorDomainError, match="preview_and_test"):
            s.prepare_delivery(plan, draft, review, x.snapshot(), (), x.NOW, **options)
    else:
        assert s.prepare_delivery(plan, draft, review, x.snapshot(), (), x.NOW, **options)


def test_campaign_completeness_covers_every_declared_operation_and_message():
    release = s.finalize_campaign(x.campaign(), (x.plan(), x.plan(message="second")), (), x.NOW)
    first_receipt = revised(
        x.remote_receipt(x.ref("first-operation"), release.binding()),
        result=revised(
            x.remote_receipt(x.ref("first-operation"), release.binding()).result,
            message_plan=release.messages[0].binding(),
        ),
    )
    second_receipt = revised(
        x.remote_receipt(x.ref("second-operation"), release.binding()),
        result=revised(
            x.remote_receipt(x.ref("second-operation"), release.binding()).result,
            message_plan=release.messages[1].binding(),
        ),
    )
    first = observation(
        operation=first_receipt.operation,
        operation_receipt=first_receipt,
        campaign_release=release.binding(),
        completeness="complete",
        coverage=1,
        data_gaps=(),
    )
    result = s.assess_program(
        x.campaign(),
        (first,),
        x.brief().window,
        ("delivered",),
        x.NOW,
        release=release,
        expected_operations=(first_receipt, second_receipt),
    )
    assert result.completeness == "partial" and result.confidence == "limited"
    assert any("second-operation/delivered" in gap for gap in result.data_gaps)
    with pytest.raises(ValidationError):
        revised(result, completeness="complete", confidence="qualified", data_gaps=())
    # Omitting B from the caller's expected population also cannot hide release message B.
    omitted = s.assess_program(
        x.campaign(),
        (first,),
        x.brief().window,
        ("delivered",),
        x.NOW,
        release=release,
        expected_operations=(first_receipt,),
    )
    assert omitted.completeness == "partial"
    assert any("Unmeasured release message" in gap for gap in omitted.data_gaps)
    second = revised(
        first,
        artifact_id="second-observation",
        operation=second_receipt.operation,
        operation_receipt=second_receipt,
    )
    complete = s.assess_program(
        x.campaign(),
        (first, second),
        x.brief().window,
        ("delivered",),
        x.NOW,
        release=release,
        expected_operations=(first_receipt, second_receipt),
    )
    assert complete.completeness == "complete" and complete.confidence == "qualified"
    # A second operation for the SAME message also needs its own metric cell.
    third_receipt = revised(
        first_receipt, artifact_id="third-receipt", operation=x.ref("third-operation")
    )
    with pytest.raises(ValidationError):
        revised(
            complete,
            population=EmailMeasurementPopulation(
                organization_id="example-org",
                publication_id="publication-a",
                release=release,
                operations=(first_receipt, second_receipt, third_receipt),
            ),
        )
    with pytest.raises(CreatorDomainError, match="expected_population"):
        s.assess_program(
            x.campaign(),
            (first, second),
            x.brief().window,
            ("delivered",),
            x.NOW,
            release=release,
            expected_operations=(first_receipt,),
        )


def test_migration_receipt_kind_and_source_checked_by_direct_construction(family):
    material = next(
        row.material for row in family.proposals if row.material.intent == EmailEffectIntent.MIGRATE
    )
    with pytest.raises(ValidationError):
        revised(material.prior_receipt, result=revised(material.prior_receipt.result, kind="draft"))
    with pytest.raises(ValidationError, match="migration source"):
        revised(
            material,
            prior_receipt=revised(
                material.prior_receipt,
                result=revised(material.prior_receipt.result, sequence=x.ref("another-source")),
            ),
        )
    with pytest.raises(ValidationError, match="migration target"):
        revised(
            material,
            migration=revised(
                material.migration,
                target_receipt=revised(material.migration.target_receipt, outcome="ambiguous"),
            ),
        )


def test_campaign_and_message_ctas_must_form_one_coordinating_set():
    extra = revised(
        x.brief().calls_to_action[0], cta_id="orphan", link_id="orphan-link", primary=False
    )
    campaign = s.plan_campaign(
        x.profile(), revised(x.brief(), calls_to_action=(*x.brief().calls_to_action, extra)), x.NOW
    )
    plan = s.plan_message(x.profile(), campaign, x.directions(), x.NOW)
    with pytest.raises(ValidationError, match="every campaign CTA"):
        s.finalize_campaign(campaign, (plan,), (), x.NOW)


def test_personalized_test_then_production_requires_distinct_coverage_reviews():
    token = PersonalizationDeclaration(name="greeting", source_policy="symbolic/greeting")
    plan = revised(
        x.plan(), subject_direction="{{greeting}} A practical capability", personalization=(token,)
    )
    draft = s.compose_message(plan, x.sections(), x.NOW)
    release = s.finalize_campaign(x.campaign(), (plan,), (), x.NOW)

    def supplied_resolution(purpose):
        # Qualified external evidence fixture; this tests receipt consumption, not a provider renderer.
        rendered = canonical_digest(
            {
                "subject": "Hello reader. A practical capability",
                "html": draft.html,
                "plain_text": draft.plain_text,
                "snapshot": x.snapshot(purpose=purpose).snapshot_digest,
            }
        )
        return revised(
            x.lowering_evidence(x.draft(), purpose),
            draft=draft.binding(),
            covered_tokens=("greeting",),
            rendered_preview_digest=rendered,
            submitted_payload_digest=rendered,
            observed_payload_digest=rendered,
        )

    def review_for(lowering):
        evidence = EmailReviewEvidence(
            artifact_id="personalization-review",
            created_at=x.NOW,
            organization_id="example-org",
            publication_id="publication-a",
            draft=draft.binding(),
            check="personalization",
            passed=True,
            policy=x.ref("personalization-policy"),
            receipt=lowering.receipt,
            issuer=lowering.issuer,
            lowering=lowering,
            valid_until=x.LATER,
        )
        return s.review_message(x.profile(), plan, draft, (*x.evidence(draft), evidence), x.NOW)

    def proof(kind, lowering, purpose):
        return EmailProofReceipt(
            artifact_id=f"proof-{kind}-{purpose}",
            created_at=x.NOW,
            organization_id="example-org",
            publication_id="publication-a",
            draft=draft.binding(),
            kind=kind,
            lowering=lowering,
            audience_snapshot=x.snapshot(purpose=purpose),
            personalization_resolved=True,
            successful=True,
            valid_until=x.LATER,
        )

    test_lowering = supplied_resolution("test")
    production_lowering = supplied_resolution("production")
    test_review = review_for(test_lowering)
    production_review = review_for(production_lowering)
    options = dict(
        release=release, execution=x.execution(), template_mapping_digest=x.mapping_digest()
    )
    assert s.prepare_delivery(
        plan,
        draft,
        test_review,
        x.snapshot(purpose="test"),
        (proof("preview", test_lowering, "test"),),
        x.NOW,
        **options,
    )
    proofs = (
        proof("preview", production_lowering, "production"),
        proof("test_send", test_lowering, "test"),
    )
    with pytest.raises(CreatorDomainError, match="provenance"):
        s.prepare_delivery(plan, draft, test_review, x.snapshot(), proofs, x.NOW, **options)
    assert s.prepare_delivery(
        plan, draft, production_review, x.snapshot(), proofs, x.NOW, **options
    )
    assert not review_for(revised(production_lowering, covered_tokens=())).ready_for_human_approval
    with pytest.raises(ValueError, match="cannot render personalization"):
        x.proofs(draft)


def test_current_validates_one_root_graph_without_revalidating_each_descendant(
    program, monkeypatch
):
    model = type(program.release)
    nested = type(program.plans[0])
    calls = []
    original = model.model_validate_json

    def root_validate(*args, **kwargs):
        calls.append("root")
        return original(*args, **kwargs)

    def redundant(*args, **kwargs):
        pytest.fail("nested JSON roundtrip repeats a graph already validated by Pydantic")

    monkeypatch.setattr(model, "model_validate_json", root_validate)
    monkeypatch.setattr(nested, "model_validate_json", redundant)
    s.current(program.release)
    assert calls == ["root"]
    bad_type = program.release.model_copy(update={"messages": "private-input-marker"})
    with warnings.catch_warnings(record=True) as emitted:
        with pytest.raises(CreatorDomainError, match="stale_email_artifact"):
            s.current(bad_type)
    assert not emitted
    # Nested corruption still fails, even with a freshly forged ancestor digest.
    bad_plan = program.plans[0].model_copy(update={"subject_direction": "Tampered nested draft"})
    corrupt = program.release.model_copy(update={"messages": (bad_plan, *program.plans[1:])})
    corrupt = corrupt.model_copy(update={"content_digest": canonical_digest(corrupt)})
    with pytest.raises((ValidationError, CreatorDomainError)):
        s.current(corrupt)


def test_all_published_email_v2_schemas_are_preserved():
    frozen = json.loads(Path("reference/email-v2-frozen.json").read_text())
    for name, schema in frozen["schemas"].items():
        assert Path(name).read_text() == json.dumps(schema, indent=2, sort_keys=True) + "\n", name
