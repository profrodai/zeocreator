"""Portable normalized-receipt cases for independently implemented host validators.

Expected verdicts are authored from the contract table, never inferred by running
our validator. These sanitized cases exercise structure and correspondence only.
"""

import copy
import json
from collections.abc import Callable, Mapping
from importlib.resources import files
from typing import Any

from pydantic import TypeAdapter

from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.email_marketing import (
    EmailDeliveryPackage,
    EmailOperationIntent,
    EmailRemoteReceipt,
    EmailRemoteResult,
    ProposedEmailOperation,
)
from zeo_creator.contracts.email_marketing import (
    EmailEffectIntent as Intent,
)
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_program_suite import effect_family
from zeo_creator.reference.email_receipt_cases_v2 import extend_cases
from zeo_creator.reference.email_workflow import remote_from_simulation, run_program
from zeo_creator.services.email_receipts import validate_operation_receipt

JsonObject = dict[str, Any]
Validator = Callable[[JsonObject], object]


def result_schema() -> JsonObject:
    """Export the exact existing result union, including its complete definitions."""
    return TypeAdapter(EmailRemoteResult).json_schema()


def build_cases() -> JsonObject:
    run = run_program(x.profile(), "hubspot-shaped")
    family = effect_family(run)
    cases: list[JsonObject] = []

    def add(name: str, target: str, value: JsonObject, expected: bool) -> None:
        cases.append(dict(name=name, target=target, input=copy.deepcopy(value), valid=expected))

    state_intents = {
        "provisioned": Intent.PROVISION,
        "active": Intent.ACTIVATE,
        "paused": Intent.PAUSE,
        "retired": Intent.RETIRE,
    }
    transitions = {
        Intent.ACTIVATE: {"provisioned"},
        Intent.ENROL: {"active"},
        Intent.PAUSE: {"active"},
        Intent.RETIRE: {"active", "paused"},
    }
    for intent, allowed in transitions.items():
        material = next(p.material for p in family.proposals if p.material.intent == intent)
        for state, previous in state_intents.items():
            prior = x.remote_receipt(
                x.ref(f"prior-{state}"),
                material.campaign_release,
                kind="sequence_revision",
                sequence=material.sequence,
                intent=previous,
            )
            value = material.model_dump(mode="json")
            value.update(
                prior_receipt=prior.model_dump(mode="json"),
                target_remote_ref=prior.remote_ref,
                expected_remote_revision_digest=prior.remote_revision_digest,
            )
            add(f"{intent.value}-from-{state}", "intent", value, state in allowed)

    content = remote_from_simulation(run.proposals[1], run.receipts[1], package=run.packages[1])
    add("broadcast-result", "result", content.result.model_dump(mode="json"), True)
    bad = content.result.model_dump(mode="json")
    bad["sequence"] = x.ref("forbidden-sequence").model_dump(mode="json")
    add("broadcast-cannot-carry-sequence", "result", bad, False)
    bad = content.model_dump(mode="json", exclude={"content_digest"})
    bad["result"]["audience"]["purpose"] = "test"
    add("test-audience-cannot-be-production-broadcast", "receipt", bad, False)
    add("confirmed-broadcast-receipt", "receipt", content.model_dump(mode="json"), True)
    for intent in (
        Intent.PROVISION,
        Intent.ACTIVATE,
        Intent.ENROL,
        Intent.PAUSE,
        Intent.MIGRATE,
        Intent.RETIRE,
    ):
        proposal = next(p for p in family.proposals if p.material.intent == intent)
        receipt = remote_from_simulation(
            proposal, family.receipts[family.proposals.index(proposal)]
        )
        add(f"{intent.value}-result", "result", receipt.result.model_dump(mode="json"), True)
        value = dict(
            proposal=proposal.model_dump(mode="json"),
            receipt=receipt.model_dump(mode="json"),
            package=None,
        )
        add(f"{intent.value}-correspondence", "correspondence", value, True)
        if intent == Intent.MIGRATE:
            bad = copy.deepcopy(value)
            bad["receipt"].pop("content_digest")
            bad["receipt"]["remote_ref"] = (
                proposal.material.prior_receipt.remote_ref
                if proposal.material.prior_receipt
                else "missing"
            )
            add("migration-cannot-return-source-object-as-target", "correspondence", bad, False)
    value = dict(
        proposal=run.proposals[1].model_dump(mode="json"),
        receipt=content.model_dump(mode="json"),
        package=run.packages[1].model_dump(mode="json"),
    )
    add("broadcast-correspondence", "correspondence", value, True)
    for field, replacement in (
        ("operation", run.proposals[3].binding().model_dump(mode="json")),
        ("campaign_release", x.ref("another-release").model_dump(mode="json")),
    ):
        bad = copy.deepcopy(value)
        bad["receipt"].pop("content_digest")
        bad["receipt"][field] = replacement
        add(f"broadcast-wrong-{field}", "correspondence", bad, False)
    extend_cases(cases, run, family)
    documents = {
        "result": result_schema(),
        "receipt": EmailRemoteReceipt.model_json_schema(),
        "intent": EmailOperationIntent.model_json_schema(),
        "proposal": ProposedEmailOperation.model_json_schema(),
        "package": EmailDeliveryPackage.model_json_schema(),
    }
    return dict(
        format_version=2,
        email_artifact_version="4.0.0",
        canonicalization="RFC8785 with Creator UTC datetime and artifact digest rules",
        schemas=documents,
        schema_digests={name: canonical_digest(schema) for name, schema in documents.items()},
        cases=cases,
        cases_digest=canonical_digest(cases),
        authentication_proven=False,
    )


def creator_validators() -> dict[str, Validator]:
    def correspondence(value: JsonObject) -> EmailRemoteReceipt:
        package = value.get("package")
        return validate_operation_receipt(
            ProposedEmailOperation.model_validate(value["proposal"]),
            EmailRemoteReceipt.model_validate(value["receipt"]),
            package=EmailDeliveryPackage.model_validate(package) if package is not None else None,
        )

    return dict(
        result=TypeAdapter(EmailRemoteResult).validate_python,
        receipt=EmailRemoteReceipt.model_validate,
        intent=EmailOperationIntent.model_validate,
        correspondence=correspondence,
    )


def verify_cases(bundle: JsonObject, validators: Mapping[str, Validator]) -> tuple[str, ...]:
    """Run every case against a consumer's validators, reporting only safe case IDs.

    A JSON Schema implementation alone is insufficient: after-model semantics,
    canonical digest checks and proposal correspondence are part of conformance.
    Missing validators or a changed corpus fail closed rather than skipping cases.
    """
    if (
        bundle.get("format_version") not in {1, 2}
        or canonical_digest(bundle["cases"]) != bundle["cases_digest"]
    ):
        raise ValueError("receipt conformance corpus digest mismatch")
    for name, schema in bundle["schemas"].items():
        if canonical_digest(schema) != bundle["schema_digests"][name]:
            raise ValueError("receipt conformance schema digest mismatch")
    required = {case["target"] for case in bundle["cases"]}
    if required != set(validators):
        raise ValueError("receipt conformance requires every declared validator")
    names = [case["name"] for case in bundle["cases"]]
    if not names or len(set(names)) != len(names):
        raise ValueError("receipt conformance requires unique nonempty case identities")
    failures = []
    for case in bundle["cases"]:
        try:
            validators[case["target"]](copy.deepcopy(case["input"]))
            valid = True
        except ValueError, TypeError:
            valid = False
        if valid != case["valid"]:
            failures.append(case["name"])
    return tuple(failures)


def packaged_cases(version: int = 2) -> JsonObject:
    if version not in {1, 2}:
        raise ValueError("unsupported receipt corpus version")
    result: JsonObject = json.loads(
        files("zeo_creator")
        .joinpath(f"reference_artifacts/email-receipt-conformance-v{version}.json")
        .read_text()
    )
    return result


if __name__ == "__main__":
    bundle = packaged_cases()
    failures = verify_cases(bundle, creator_validators())
    if failures:
        raise SystemExit(f"Receipt conformance failed: {failures}")
    print(
        f"Verified {len(bundle['cases'])} portable receipt cases; issuer authentication not established"
    )
