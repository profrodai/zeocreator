"""Schema, dependency, and cross-property guard tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError
from zeo_core.tools import invoke_sync

from tests.fixtures.dogfood import NOW, build_dogfood_snapshot, publication_profiles
from zeo_creator.capabilities.create_ducktyper_brief import CreateDucktyperBriefRequest
from zeo_creator.contracts.distribution import ProviderKind, PublicationReceipt, ReconciliationState
from zeo_creator.contracts.ducktyper import DucktyperBrief
from zeo_creator.registry import capability_registry
from zeo_creator.runtime import make_context


def test_format_payload_is_a_discriminated_union() -> None:
    brief = build_dogfood_snapshot().briefs[0]
    invalid = brief.model_dump(mode="json")
    invalid["format_payload"]["kind"] = "hud"

    with pytest.raises(ValidationError):
        DucktyperBrief.model_validate(invalid)


def test_brief_capability_rejects_cross_property_inputs() -> None:
    snapshot = build_dogfood_snapshot()
    request = CreateDucktyperBriefRequest(
        assignment=snapshot.plan.assignments[0],
        publication=publication_profiles()[1],
        synthesis=snapshot.syntheses[0],
        created_at=NOW,
    )
    result = invoke_sync(
        capability_registry().get("creator.create_ducktyper_brief@1.0.0"),
        request,
        make_context(capability_name="create_ducktyper_brief"),
    )

    assert result.status.value == "error"
    assert result.machine_message == "ZEO_CREATOR_PUBLICATION_LEAKAGE"


def test_missing_connector_dependency_fails_closed() -> None:
    capability = capability_registry().get("creator.research_synthesis@1.0.0")
    request = capability.request_model.model_validate(capability.definition.examples[0].request)
    context = make_context(capability_name="research_synthesis")

    assert capability.is_available(context) is False
    result = invoke_sync(capability, request, context)
    assert result.status.value == "skipped"
    assert result.outcome.value == "unavailable"
    assert result.machine_message == "ZEO_CAP_UNAVAILABLE"


def test_receipt_contract_rejects_credential_fields() -> None:
    with pytest.raises(ValidationError):
        PublicationReceipt.model_validate(
            {
                "receipt_id": "receipt_fixture",
                "created_at": NOW,
                "organization_id": "org",
                "publication_id": "profrod.ai",
                "operation_id": "operation_fixture",
                "provider_kind": ProviderKind.WEBSITE,
                "connection_ref": "connection_fixture",
                "provider_operation_ref": "provider_fixture",
                "executed_at": NOW,
                "outcome": "accepted",
                "reconciliation_state": ReconciliationState.CONFIRMED,
                "access_token": "must-not-enter-contracts",
            }
        )


def test_legacy_import_package_is_absent() -> None:
    assert not any(Path("quackresearch").rglob("*.py"))
