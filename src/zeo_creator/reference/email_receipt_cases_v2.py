"""Authored cross-implementation counterexamples supplementing the preserved v1 cases."""

import copy
from datetime import timedelta
from typing import Any

from zeo_creator.contracts.email_marketing import EmailEffectIntent as Intent
from zeo_creator.contracts.email_marketing import EmailRemoteReceipt
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_program_suite import EmailEffectFamilyRun
from zeo_creator.reference.email_workflow import EmailReferenceRun, remote_from_simulation
from zeo_creator.services.email_marketing import prepare_delivery

JsonObject = dict[str, Any]


def extend_cases(
    cases: list[JsonObject], run: EmailReferenceRun, family: EmailEffectFamilyRun
) -> None:
    """Add all effect variants and well-formed, freshly digested binding substitutions.

    Model construction here only checks that a correspondence counterexample is
    valid evidence in isolation. The rejection verdict is authored independently;
    the correspondence validator under test is never asked for an expected result.
    """

    def add(name: str, target: str, value: JsonObject, expected: bool) -> None:
        cases.append(dict(name=name, target=target, input=copy.deepcopy(value), valid=expected))

    def changed(value: JsonObject, updates: JsonObject) -> JsonObject:
        result = copy.deepcopy(value)
        payload = result["receipt"]
        payload.pop("content_digest")
        payload.update(updates)
        result["receipt"] = EmailRemoteReceipt.model_validate(payload).model_dump(mode="json")
        return result

    production = run.packages[1]
    scheduled = prepare_delivery(
        run.plans[0],
        run.drafts[0],
        run.reviews[0],
        x.snapshot(run.publication.publication_id),
        production.material.proofs,
        x.NOW,
        x.NOW + timedelta(hours=1),
        release=run.release,
        execution=production.material.execution,
        template_mapping_digest=x.mapping_digest(run.publication.publication_id),
    )
    packages = (*run.packages, scheduled)
    values: dict[Intent, JsonObject] = {}
    for index, proposal in enumerate(family.proposals):
        intent = proposal.material.intent
        if intent in values:
            continue  # The second provisioning target has separate migration provenance cases.
        package = next((p for p in packages if p.binding() == proposal.material.delivery), None)
        if proposal.material.delivery is not None and package is None:
            raise ValueError("conformance fixture requires its exact delivery package")
        receipt = remote_from_simulation(proposal, family.receipts[index], package=package)
        value: JsonObject = dict(
            proposal=proposal.model_dump(mode="json"),
            receipt=receipt.model_dump(mode="json"),
            package=package.model_dump(mode="json") if package else None,
        )
        values[intent] = value
        prefix = intent.value
        add(f"effect/{prefix}/result", "result", value["receipt"]["result"], True)
        add(f"effect/{prefix}/receipt", "receipt", value["receipt"], True)
        add(f"effect/{prefix}/correspondence", "correspondence", value, True)

        # A shape-valid receipt can still contradict the exact approved effect.
        wrong = copy.deepcopy(value["receipt"]["result"])
        if wrong["kind"] == "sequence_revision":
            wrong.update(
                intent=Intent.PAUSE.value if intent == Intent.RETIRE else Intent.RETIRE.value,
                lifecycle_state="paused" if intent == Intent.RETIRE else "retired",
                audience=None,
            )
        else:
            wrong.update(
                kind="draft",
                intent=Intent.UPDATE_DRAFT.value
                if intent == Intent.CREATE_DRAFT
                else Intent.CREATE_DRAFT.value,
            )
        add(
            f"effect/{prefix}/wrong-intent",
            "correspondence",
            changed(value, dict(result=wrong)),
            False,
        )

        # All six discriminators must reject an incompatible effect independently.
        invalid = copy.deepcopy(value["receipt"]["result"])
        invalid["intent"] = Intent.SEND.value if intent != Intent.SEND else Intent.TEST.value
        add(f"effect/{prefix}/incompatible-result-intent", "result", invalid, False)

        if proposal.material.sequence is not None:
            wrong = copy.deepcopy(value["receipt"]["result"])
            wrong["sequence"] = x.ref("different-sequence").model_dump(mode="json")
            add(
                f"effect/{prefix}/wrong-sequence",
                "correspondence",
                changed(value, dict(result=wrong)),
                False,
            )
            wrong = copy.deepcopy(value["receipt"]["result"])
            wrong["lifecycle_state"] = (
                "active" if wrong["lifecycle_state"] != "active" else "retired"
            )
            add(f"effect/{prefix}/contradictory-state", "result", wrong, False)
            if receipt.result.audience is not None:
                wrong = copy.deepcopy(value["receipt"]["result"])
                wrong["audience"]["eligible_count"] += 1
                add(
                    f"effect/{prefix}/larger-audience",
                    "correspondence",
                    changed(value, dict(result=wrong)),
                    False,
                )
                wrong["audience"] = None
                add(f"effect/{prefix}/missing-audience", "result", wrong, False)
        if proposal.material.target_remote_ref is not None:
            add(
                f"effect/{prefix}/wrong-remote-target",
                "correspondence",
                changed(value, dict(remote_ref="publication-a/different-remote")),
                False,
            )

    send = values[Intent.SEND]
    for field, replacement in (
        ("operation", values[Intent.CREATE_DRAFT]["proposal"]["material"]["campaign_release"]),
        ("campaign_release", x.ref("different-release").model_dump(mode="json")),
        ("created_at", (x.NOW - timedelta(seconds=1)).isoformat()),
    ):
        add(f"binding/{field}", "correspondence", changed(send, {field: replacement}), False)
    for field, replacement in (
        ("account_ref", "publication-a/different-account"),
        ("connector_revision", "different-revision"),
    ):
        execution = copy.deepcopy(send["receipt"]["execution"])
        execution[field] = replacement
        add(f"binding/{field}", "correspondence", changed(send, dict(execution=execution)), False)
    for field, replacement in (
        ("message_plan", run.plans[1].binding().model_dump(mode="json")),
        ("delivery", run.packages[3].binding().model_dump(mode="json")),
    ):
        result = copy.deepcopy(send["receipt"]["result"])
        result[field] = replacement
        add(f"binding/{field}", "correspondence", changed(send, dict(result=result)), False)
    result = copy.deepcopy(send["receipt"]["result"])
    result["audience"]["eligible_count"] += 1
    add("binding/larger-audience", "correspondence", changed(send, dict(result=result)), False)
    for name, raw_package in (
        ("missing-package", None),
        ("different-package", run.packages[3].model_dump(mode="json")),
    ):
        value = copy.deepcopy(send)
        value["package"] = raw_package
        add(f"binding/{name}", "correspondence", value, False)
    for outcome in ("ambiguous", "needs_review"):
        add(f"historical/{outcome}", "correspondence", changed(send, dict(outcome=outcome)), True)
    add(
        "historical/expired-package",
        "correspondence",
        changed(send, dict(created_at=(x.LATER + timedelta(days=30)).isoformat())),
        True,
    )

    cancel = values[Intent.CANCEL]
    wrong = copy.deepcopy(cancel["receipt"]["result"])
    wrong["delivery"] = run.packages[3].binding().model_dump(mode="json")
    add(
        "cancel/wrong-historical-delivery",
        "correspondence",
        changed(cancel, dict(result=wrong)),
        False,
    )
    add(
        "cancel/expired-historical-evidence",
        "correspondence",
        changed(cancel, dict(created_at=(x.LATER + timedelta(days=30)).isoformat())),
        True,
    )
    sequence = copy.deepcopy(values[Intent.PROVISION])
    sequence["package"] = production.model_dump(mode="json")
    add("sequence/unexpected-package", "correspondence", sequence, False)
