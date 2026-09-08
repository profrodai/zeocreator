"""The shared corpus must detect permissive, rejecting and incomplete implementations."""

import copy

import pytest

from zeo_creator.contracts.email_marketing import EmailRemoteReceipt, ProposedEmailOperation
from zeo_creator.reference.email_receipt_conformance import (
    creator_validators,
    packaged_cases,
    verify_cases,
)


def test_creator_matches_portable_cases():
    corpus = packaged_cases()
    assert len(corpus["cases"]) == 135
    assert verify_cases(corpus, creator_validators()) == ()
    assert corpus["authentication_proven"] is False


def test_corpus_cannot_bless_accept_everything():
    validators = {name: lambda value: value for name in creator_validators()}
    failures = verify_cases(packaged_cases(), validators)
    assert "migration-cannot-return-source-object-as-target" in failures
    assert "activate_sequence_revision-from-paused" in failures


def test_corpus_cannot_bless_reject_everything():
    def reject(value):
        raise ValueError("rejected")

    validators = dict.fromkeys(creator_validators(), reject)
    assert "broadcast-correspondence" in verify_cases(packaged_cases(), validators)


def test_missing_validator_refuses_instead_of_skipping():
    validators = creator_validators()
    validators.pop("correspondence")
    with pytest.raises(ValueError, match="every declared validator"):
        verify_cases(packaged_cases(), validators)


@pytest.mark.parametrize("section", ["cases", "schemas"])
def test_modified_corpus_refuses(section):
    corpus = copy.deepcopy(packaged_cases())
    if section == "cases":
        corpus["cases"][0]["valid"] = not corpus["cases"][0]["valid"]
    else:
        corpus["schemas"]["result"]["description"] = "changed"
    with pytest.raises(ValueError, match="digest mismatch"):
        verify_cases(corpus, creator_validators())


def lax_correspondence(value):
    """The Steward counterexample: valid receipt, but only three bindings enforced."""
    proposal = ProposedEmailOperation.model_validate(value["proposal"])
    receipt = EmailRemoteReceipt.model_validate(value["receipt"])
    if (
        receipt.operation != proposal.binding()
        or receipt.campaign_release != proposal.material.campaign_release
    ):
        raise ValueError("mismatch")
    if (
        proposal.material.migration is not None
        and receipt.remote_ref == proposal.material.prior_receipt.remote_ref
    ):
        raise ValueError("source object")
    return receipt


def test_lax_correspondence_passes_retired_v1_but_fails_current_corpus():
    validators = creator_validators()
    validators["correspondence"] = lax_correspondence
    assert verify_cases(packaged_cases(1), validators) == ()
    failures = set(verify_cases(packaged_cases(), validators))
    assert {
        "binding/account_ref",
        "binding/connector_revision",
        "binding/created_at",
        "binding/message_plan",
        "binding/delivery",
        "binding/larger-audience",
        "binding/missing-package",
        "binding/different-package",
        "effect/create_remote_draft/wrong-intent",
        "effect/update_remote_draft/wrong-intent",
        "effect/update_remote_draft/wrong-remote-target",
        "cancel/wrong-historical-delivery",
        "effect/enrol_audience_snapshot/larger-audience",
        "effect/migrate_existing_enrollees/larger-audience",
    } <= failures


def test_partial_result_implementation_passes_retired_v1_but_fails_current_corpus():
    def partial(target, validator):
        def validate(value):
            result = (
                value
                if target == "result"
                else value["result"]
                if target == "receipt"
                else value["receipt"]["result"]
            )
            if result["kind"] not in {"broadcast", "sequence_revision"}:
                raise ValueError("unsupported result variant")
            return validator(value)

        return validate

    validators = creator_validators()
    for target in ("result", "receipt", "correspondence"):
        validators[target] = partial(target, validators[target])
    assert verify_cases(packaged_cases(1), validators) == ()
    failures = set(verify_cases(packaged_cases(), validators))
    assert {
        f"effect/{intent}/{target}"
        for intent in (
            "create_remote_draft",
            "update_remote_draft",
            "schedule_broadcast",
            "send_test",
            "cancel_scheduled_broadcast",
        )
        for target in ("result", "receipt", "correspondence")
    } <= failures


def test_every_effect_has_result_receipt_and_correspondence_coverage():
    from zeo_creator.contracts.email_marketing import EmailEffectIntent

    cases = packaged_cases()["cases"]
    for target in ("result", "receipt", "correspondence"):
        values = [c["input"] for c in cases if c["target"] == target and c["valid"]]
        results = [
            v
            if target == "result"
            else v["result"]
            if target == "receipt"
            else v["receipt"]["result"]
            for v in values
        ]
        assert {r["kind"] for r in results} == {
            "draft",
            "scheduled_broadcast",
            "broadcast",
            "test_send",
            "cancelled_broadcast",
            "sequence_revision",
        }
        assert {r["intent"] for r in results} == {i.value for i in EmailEffectIntent}
    names = {c["name"] for c in cases if c["target"] == "correspondence" and not c["valid"]}
    assert {f"effect/{i.value}/wrong-intent" for i in EmailEffectIntent} <= names


def test_bundle_contains_exact_schemas_for_its_full_inputs():
    from zeo_creator.contracts.email_marketing import EmailDeliveryPackage

    bundle = packaged_cases()
    assert bundle["format_version"] == 2
    assert set(bundle["schemas"]) == {"result", "receipt", "intent", "proposal", "package"}
    assert bundle["schemas"]["proposal"] == ProposedEmailOperation.model_json_schema()
    assert bundle["schemas"]["package"] == EmailDeliveryPackage.model_json_schema()


def test_binding_counterexamples_are_valid_freshly_digested_receipts():
    for case in packaged_cases()["cases"]:
        if case["target"] == "correspondence" and case["name"].startswith(
            ("binding/", "effect/", "cancel/")
        ):
            raw = case["input"]["receipt"]
            assert "content_digest" in raw
            assert EmailRemoteReceipt.model_validate(raw).content_digest == raw["content_digest"]
