"""Falsify email authority, integrity, isolation and observation claims offline."""

import json
from datetime import timedelta
from itertools import permutations

import pytest
from pydantic import ValidationError

from zeo_creator.capabilities.email_marketing import (
    ComposeEmailMessageRequest,
    compose_email_message,
)
from zeo_creator.contracts.common import canonical_digest, digest_is_current
from zeo_creator.contracts.email_marketing import (
    AudienceSnapshotSummary,
    EmailDeliveryPackage,
    EmailEffectIntent,
    EmailMetricObservation,
    EmailOperationIntent,
    EmailSequencePlan,
    PersonalizationDeclaration,
)
from zeo_creator.errors import CreatorDomainError
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_simulation import (
    SimulatedEmailHost,
    lower,
    operation_contract_digest,
    operation_identity,
)
from zeo_creator.runtime import make_context
from zeo_creator.services import email_marketing as s


def revised(model, **changes):
    data = model.model_dump(mode="python", exclude={"content_digest"})
    data.update(changes)
    return type(model).model_validate(data)


def reviewed(publication="publication-a"):
    plan, draft = x.plan(publication), x.draft(publication)
    review = s.review_message(x.profile(publication), plan, draft, x.evidence(draft), x.NOW)
    return plan, draft, review


def package(publication="publication-a", purpose="production", schedule=None):
    plan, draft, review = reviewed(publication)
    return s.prepare_delivery(
        plan,
        draft,
        review,
        x.snapshot(publication, purpose),
        x.proofs(draft, purpose),
        x.NOW,
        schedule,
        release=x.release(publication),
        execution=x.execution(publication),
        template_mapping_digest=x.mapping_digest(publication),
    )


def proposal(item, intent=EmailEffectIntent.SEND, key="logical-operation"):
    material = EmailOperationIntent(
        organization_id=item.organization_id,
        publication_id=item.publication_id,
        execution=item.material.execution,
        campaign_release=item.material.campaign_release,
        intent=intent,
        operation=operation_identity(intent),
        operation_contract_digest=operation_contract_digest(intent),
        delivery=item.binding(),
        delivery_approval_digest=item.approval_digest,
        audience=item.material.audience_snapshot,
    )
    return s.propose_operation(
        material, x.NOW, key, release=x.release(item.publication_id), package=item
    )


def sequence(publication="publication-a", previous=None, migration=None):
    return s.plan_sequence(
        x.campaign(publication),
        f"{publication}/welcome",
        tuple(x.plan(publication, f"step-{i}") for i in range(3)),
        (0, 3600, 7200),
        x.policies(publication),
        x.brief(publication).window,
        ("linear", "retain_existing_revision"),
        x.NOW,
        previous,
        migration,
    )


@pytest.mark.parametrize(
    "left,right", tuple(permutations(("publication-a", "publication-b", "publication-c"), 2))
)
def test_three_publications_cannot_mix_any_stage(left, right):
    with pytest.raises((CreatorDomainError, ValidationError)):
        s.plan_campaign(x.profile(left), x.brief(right), x.NOW)
    with pytest.raises((CreatorDomainError, ValidationError)):
        s.plan_message(x.profile(left), x.campaign(right), x.directions(left), x.NOW)
    with pytest.raises((CreatorDomainError, ValidationError)):
        s.compose_message(x.plan(left), x.sections(right), x.NOW)
    with pytest.raises((CreatorDomainError, ValidationError)):
        s.review_message(x.profile(left), x.plan(left), x.draft(right), (), x.NOW)
    plan, draft, review = reviewed(left)
    with pytest.raises((CreatorDomainError, ValidationError)):
        s.prepare_delivery(
            plan,
            draft,
            review,
            x.snapshot(right),
            x.proofs(draft),
            x.NOW,
            release=x.release("publication-a"),
            execution=x.execution("publication-a"),
            template_mapping_digest=x.mapping_digest("publication-a"),
        )
    with pytest.raises(ValidationError):
        revised(x.directions(left), sender=x.ref("sender", right))


def test_dual_format_composition_is_content_from_exact_scoped_evidence():
    draft = x.draft()
    assert x.sections()[0].text in draft.html
    assert x.sections()[0].text in draft.plain_text
    assert draft.generation.input_digests == (
        canonical_digest(x.plan()),
        canonical_digest(x.sections()),
    )
    assert draft.source_lineage == x.plan().source_evidence
    assert digest_is_current(draft)


def test_semantic_checks_need_evidence_and_never_self_approve():
    review = s.review_message(x.profile(), x.plan(), x.draft(), (), x.NOW)
    assert not review.ready_for_human_approval
    assert {row.check for row in review.findings if row.status == "human_needed"} == {
        "publication_voice",
        "subject_body",
        "links",
        "claims",
        "accessibility",
    }
    assert "approved" not in type(review).model_fields


@pytest.mark.parametrize(
    "change",
    [
        "subject",
        "html",
        "plain_text",
        "links",
        "sender_identity",
        "reply_to_identity",
        "audience_snapshot",
        "schedule_intent",
        "sequence_revision",
        "tracking_policy",
        "campaign",
    ],
)
def test_any_material_change_changes_the_digest(change):
    item = package()
    data = item.material.model_dump(mode="json")
    if change in {"subject", "html", "plain_text"}:
        data["draft"][change] += " changed"
    elif change in {"links", "sender_identity", "reply_to_identity"}:
        if change == "links":
            data["draft"][change][0]["url"] += "/changed"
        else:
            data["draft"][change]["revision"] += 1
    elif change == "audience_snapshot":
        data[change]["eligible_count"] += 1
    elif change == "schedule_intent":
        data[change] = x.LATER.isoformat()
    elif change == "sequence_revision":
        data[change] = x.ref("sequence").model_dump(mode="json")
    else:
        data[change]["revision"] += 1
    assert canonical_digest(data) != item.approval_digest
    corrupt = item.model_dump(mode="json")
    corrupt["material"] = data
    with pytest.raises(ValidationError):
        EmailDeliveryPackage.model_validate(corrupt)


def test_same_material_can_be_consumed_by_both_fake_lowerers():
    item = package()
    hubspot, kit = lower(item, "hubspot-shaped"), lower(item, "kit-shaped")
    assert hubspot["subject"] == kit["subject"] == item.material.draft.subject
    assert hubspot["content"]["html"] == kit["content_html"] == item.material.draft.html
    assert hubspot["content"]["plainText"] == kit["content_text"] == item.material.draft.plain_text
    assert hubspot["materialDigest"] == kit["material_digest"] == item.approval_digest
    # Pure wire projections can inspect the same neutral material; effects still bind a destination.
    op = proposal(item)
    with pytest.raises(CreatorDomainError, match="execution_provider_mismatch"):
        SimulatedEmailHost("kit-shaped").simulate(
            op, op.approval_digest, x.NOW, package=item, release=x.release()
        )


def test_test_approval_and_audience_cannot_authorize_production():
    test = proposal(package(purpose="test"), EmailEffectIntent.TEST)
    production_package = package()
    production = proposal(production_package)
    host = SimulatedEmailHost("kit-shaped")
    with pytest.raises(CreatorDomainError, match="approval_mismatch"):
        host.simulate(
            production, test.approval_digest, x.NOW, package=production_package, release=x.release()
        )
    with pytest.raises(ValidationError, match="test and production"):
        revised(test.material, intent=EmailEffectIntent.SEND)
    assert host.submissions == 0


def test_activation_is_not_enrolment_and_sequence_capability_refuses_approximation():
    seq = sequence()
    released = s.finalize_campaign(
        x.campaign(), tuple(x.plan(message=f"step-{i}") for i in range(3)), (seq,), x.NOW
    )
    prior = x.remote_receipt(
        x.ref("provisioned-sequence"),
        released.binding(),
        kind="sequence_revision",
        sequence=seq.binding(),
    )
    activate = EmailOperationIntent(
        execution=x.execution(),
        campaign_release=released.binding(),
        prior_receipt=prior,
        target_remote_ref=prior.remote_ref,
        expected_remote_revision_digest=prior.remote_revision_digest,
        organization_id=seq.organization_id,
        publication_id=seq.publication_id,
        intent=EmailEffectIntent.ACTIVATE,
        operation=operation_identity(EmailEffectIntent.ACTIVATE),
        operation_contract_digest=operation_contract_digest(EmailEffectIntent.ACTIVATE),
        sequence=seq.binding(),
    )
    activation = s.propose_operation(activate, x.NOW, "activation", release=released, sequence=seq)
    active = x.remote_receipt(
        activation.binding(),
        released.binding(),
        kind="sequence_revision",
        sequence=seq.binding(),
        intent=EmailEffectIntent.ACTIVATE,
    )
    enrol = revised(
        activate,
        prior_receipt=active,
        target_remote_ref=active.remote_ref,
        expected_remote_revision_digest=active.remote_revision_digest,
        intent=EmailEffectIntent.ENROL,
        operation=operation_identity(EmailEffectIntent.ENROL),
        operation_contract_digest=operation_contract_digest(EmailEffectIntent.ENROL),
        audience=x.snapshot(),
    )
    enrolment = s.propose_operation(enrol, x.NOW, "enrolment", release=released, sequence=seq)
    host = SimulatedEmailHost("hubspot-shaped")
    with pytest.raises(CreatorDomainError, match="approval_mismatch"):
        host.simulate(enrolment, activation.approval_digest, x.NOW, sequence=seq, release=released)
    with pytest.raises(CreatorDomainError, match="semantics_unsupported"):
        host.simulate(activation, activation.approval_digest, x.NOW, sequence=seq, release=released)
    with pytest.raises(ValidationError, match="activation cannot"):
        revised(activate, audience=x.snapshot())


@pytest.mark.parametrize(
    "mutation",
    [
        dict(eligible_count=0),
        dict(drift_status="unknown"),
        dict(drift_status="changed"),
        dict(audience_intent_digest=canonical_digest("other")),
        dict(consent_policy_digest=canonical_digest("other")),
        dict(suppression_policy_digest=canonical_digest("other")),
    ],
)
def test_audience_drift_empty_or_policy_changes_are_refused(mutation):
    plan, draft, review = reviewed()
    with pytest.raises(CreatorDomainError):
        s.prepare_delivery(
            plan,
            draft,
            review,
            revised(x.snapshot(), **mutation),
            x.proofs(draft),
            x.NOW,
            release=x.release("publication-a"),
            execution=x.execution("publication-a"),
            template_mapping_digest=x.mapping_digest("publication-a"),
        )


@pytest.mark.parametrize(
    "at", [x.NOW - timedelta(seconds=1), x.LATER, x.LATER + timedelta(seconds=1)]
)
def test_snapshot_boundary_is_inclusive_resolution_exclusive_expiry(at):
    plan, draft, review = reviewed()
    with pytest.raises(CreatorDomainError):
        s.prepare_delivery(
            plan,
            draft,
            review,
            x.snapshot(),
            x.proofs(draft),
            at,
            release=x.release("publication-a"),
            execution=x.execution("publication-a"),
            template_mapping_digest=x.mapping_digest("publication-a"),
        )


def test_changed_snapshot_cannot_be_substituted_at_lowering():
    item = package()
    op = proposal(item)
    changed = revised(op.material, audience=revised(x.snapshot(), eligible_count=11))
    with pytest.raises(CreatorDomainError, match="audience_changed"):
        s.propose_operation(changed, x.NOW, "changed", package=item, release=x.release())


@pytest.mark.parametrize("policy", ["consent_policy", "suppression_policy"])
def test_absent_consent_or_suppression_blocks_readiness(policy):
    plan = x.plan()
    audience = revised(plan.audience, **{policy: None})
    compliance = revised(plan.compliance, **{policy: None})
    plan = revised(plan, audience=audience, compliance=compliance)
    draft = s.compose_message(plan, x.sections(), x.NOW)
    review = s.review_message(x.profile(), plan, draft, x.evidence(draft), x.NOW)
    assert not review.ready_for_human_approval
    with pytest.raises(CreatorDomainError):
        s.prepare_delivery(
            plan,
            draft,
            review,
            x.snapshot(),
            x.proofs(draft),
            x.NOW,
            release=x.release("publication-a"),
            execution=x.execution("publication-a"),
            template_mapping_digest=x.mapping_digest("publication-a"),
        )


def test_divergent_html_and_plain_text_are_blocked():
    draft = revised(x.draft(), plain_text=x.draft().plain_text + " Another claim.")
    review = s.review_message(x.profile(), x.plan(), draft, x.evidence(draft), x.NOW)
    assert (
        next(row for row in review.findings if row.check == "html_plain_text").status == "blocked"
    )
    assert not review.ready_for_human_approval


@pytest.mark.parametrize("placeholder", ["{{first_name}}", "{{ unknown }}", "{{", "}}"])
def test_unresolved_personalization_blocks_readiness(placeholder):
    draft = revised(x.draft(), subject=x.draft().subject + placeholder)
    review = s.review_message(x.profile(), x.plan(), draft, x.evidence(draft), x.NOW)
    assert (
        next(row for row in review.findings if row.check == "personalization").status == "blocked"
    )
    assert not review.ready_for_human_approval


def test_symbolic_declaration_contains_no_contact_value_field():
    token = PersonalizationDeclaration(name="first_name", source_policy="public/symbolic-policy")
    with pytest.raises(ValidationError):
        revised(token, value="subscriber-value")


def test_sequence_steps_deterministic_unique_and_revisioned():
    seq = sequence()
    assert seq.content_digest == sequence().content_digest
    assert [step.ordinal for step in seq.steps] == [1, 2, 3]
    assert len({step.step_id for step in seq.steps}) == 3
    newer = sequence(previous=seq)
    assert newer.revision == 2 and newer.previous_revision == seq.binding()
    assert newer.content_digest != seq.content_digest
    assert newer.existing_enrollee_migration_policy == "retain_existing_revision"
    for steps in [(seq.steps[0], seq.steps[0]), tuple(reversed(seq.steps)), ()]:
        with pytest.raises(ValidationError):
            revised(seq, steps=steps)
    with pytest.raises(ValidationError):
        revised(seq, revision=2)
    with pytest.raises(ValidationError):
        revised(newer, revision=1)
    assert EmailSequencePlan.model_validate_json(seq.model_dump_json()) == seq


def test_migration_requires_explicit_policy_and_new_authority():
    seq = sequence()
    with pytest.raises(ValidationError):
        revised(seq, existing_enrollee_migration_policy="explicit_new_authority")
    migrated = sequence(previous=seq, migration=x.ref("migration"))
    assert migrated.revision == 2
    assert migrated.migration_policy == x.ref("migration")
    assert migrated.content_digest != seq.content_digest


def test_duplicate_execution_is_logical_once_conflicts_fail_and_ambiguity_reconciles():
    item = package()
    op = proposal(item)
    host = SimulatedEmailHost("hubspot-shaped")
    receipt = host.simulate(
        op, op.approval_digest, x.NOW, package=item, outcome="ambiguous", release=x.release()
    )
    assert (
        host.simulate(op, op.approval_digest, x.LATER, package=item, release=x.release()) == receipt
    )
    assert host.submissions == 1
    changed = proposal(package(schedule=x.NOW + timedelta(hours=1)), EmailEffectIntent.SCHEDULE)
    with pytest.raises(CreatorDomainError, match="conflicting_idempotency"):
        host.simulate(changed, changed.approval_digest, x.NOW, package=item, release=x.release())
    final = host.reconcile(op, receipt.submitted_payload_digest)
    assert final.outcome == "accepted" and host.submissions == 1
    transformed = host.reconcile(op, canonical_digest("transformed"))
    assert transformed.outcome == "needs_review" and host.submissions == 1


def observation(publication="publication-a", **changes):
    data = dict(
        artifact_id=f"{publication}/metric-delivered",
        created_at=x.NOW,
        organization_id="example-org",
        publication_id=publication,
        campaign=x.campaign(publication).binding(),
        operation=x.ref("delivery-operation", publication),
        retrieval_receipt=x.ref("retrieval-receipt", publication),
        campaign_release=x.release(publication).binding(),
        operation_receipt=x.remote_receipt(
            x.ref("delivery-operation", publication), x.release(publication).binding()
        ),
        provider_kind=x.execution(publication).provider_kind,
        connection_ref=f"{publication}/connection",
        aggregate_segment_ref=f"{publication}/aggregate-segment",
        observation_window=x.brief(publication).window,
        metric="delivered",
        value=8,
        unit="count",
        provider_definition="Provider-accepted delivery observation",
        provider_definition_version="1.0.0",
        completeness="partial",
        coverage=0.8,
        reliability="qualified",
        data_gaps=("Two delivery outcomes pending.",),
    )
    data.update(changes)
    return EmailMetricObservation(**data)


def test_partial_metrics_stay_partial_and_missing_observations_stay_unknown():
    assessment = s.assess_program(
        x.campaign(),
        (observation(),),
        x.brief().window,
        ("delivered", "cta_conversions"),
        x.NOW,
        release=x.release(),
        expected_operations=tuple(dict.fromkeys(row.operation_receipt for row in (observation(),))),
    )
    assert assessment.completeness == "partial" and assessment.confidence == "limited"
    assert "Missing metric: cta_conversions" in assessment.data_gaps
    with pytest.raises(ValidationError):
        revised(assessment, completeness="complete", confidence="qualified")
    empty = s.assess_program(
        x.campaign(),
        (),
        x.brief().window,
        ("delivered",),
        x.NOW,
        release=x.release(),
        expected_operations=tuple(dict.fromkeys(row.operation_receipt for row in ())),
    )
    assert empty.completeness == "unknown" and empty.confidence == "limited"
    with pytest.raises((ValidationError, CreatorDomainError)):
        s.assess_program(
            x.campaign(),
            (observation("publication-b"),),
            x.brief().window,
            ("delivered",),
            x.NOW,
            release=x.release(),
            expected_operations=tuple(
                dict.fromkeys(row.operation_receipt for row in (observation("publication-b"),))
            ),
        )


@pytest.mark.parametrize(
    "changes",
    [
        dict(metric="opened"),
        dict(metric="attributed_revenue"),
        dict(value=float("nan")),
        dict(denominator=0),
        dict(unit="rate", numerator=1, denominator=2, value=0.7),
        dict(completeness="complete"),
    ],
)
def test_metrics_require_qualifications_and_valid_denominators(changes):
    with pytest.raises(ValidationError):
        observation(**changes)


def test_subscriber_fields_are_forbidden_and_safe_errors_do_not_echo_inputs():
    for field in ("emails", "names", "contact_ids", "crm_properties", "provider_error_body"):
        with pytest.raises(ValidationError):
            revised(x.snapshot(), **{field: ["opaque-subscriber-data"]})
    marker = "private" + "@" + "example.invalid"
    with pytest.raises(ValidationError) as error:
        revised(x.draft(), subject=marker)
    assert marker not in str(error.value)

    class FailingStrategy:
        def compose(self, *args):
            raise RuntimeError(marker)

    result = compose_email_message(
        ComposeEmailMessageRequest(plan=x.plan(), sections=x.sections(), created_at=x.NOW),
        make_context(
            capability_name="creator.compose_email_message",
            services={"creator.email_strategy": FailingStrategy()},
        ),
    )
    assert result.status.value == "error"
    assert marker not in result.model_dump_json()
    assert "RuntimeError" not in result.model_dump_json()


def test_unsafe_model_copy_and_wrong_strategy_publication_fail():
    item = package()
    corrupt = item.model_copy(update={"approval_digest": canonical_digest("other")})
    with pytest.raises(CreatorDomainError):
        lower(corrupt, "kit-shaped")

    class WrongPublicationStrategy:
        def compose(self, *args):
            return x.draft("publication-b")

    with pytest.raises(CreatorDomainError):
        s.compose_message(x.plan(), x.sections(), x.NOW, WrongPublicationStrategy())


def test_python_json_roundtrip_preserves_digest():
    for item in (x.campaign(), x.plan(), x.draft(), sequence(), package(), observation()):
        parsed = type(item).model_validate_json(item.model_dump_json())
        assert parsed == item and digest_is_current(parsed)
        assert json.loads(parsed.model_dump_json()) == item.model_dump(mode="json")
    assert (
        AudienceSnapshotSummary.model_validate_json(x.snapshot().model_dump_json()) == x.snapshot()
    )
