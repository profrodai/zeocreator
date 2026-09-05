"""Schema, dependency, and cross-publication guard tests."""

import pytest
from pydantic import ValidationError
from zeo_core.tools import invoke_sync

from tests.fixtures.reference import (
    NOW,
    REQUIREMENTS,
    build_reference_snapshot,
    publication_profiles,
)
from zeo_creator.capabilities.create_content_brief import CreateContentBriefRequest
from zeo_creator.contracts.distribution import PublicationReceipt, ReconciliationState
from zeo_creator.contracts.production import ExtensionPayload
from zeo_creator.registry import capability_registry
from zeo_creator.runtime import make_context


def test_extension_payload_rejects_credential_shaped_data() -> None:
    with pytest.raises(ValidationError):
        ExtensionPayload(
            namespace="example.extension",
            schema_id="example",
            schema_version="1",
            schema_digest="sha256:" + "0" * 64,
            payload={"access_token": "forbidden"},
        )


def test_brief_capability_rejects_cross_publication_inputs() -> None:
    snapshot = build_reference_snapshot()
    request = CreateContentBriefRequest(
        assignment=snapshot.plan.assignments[0],
        publication=publication_profiles()[1],
        synthesis=snapshot.syntheses[0],
        creative_direction="Create a useful explainer.",
        delivery_requirements=REQUIREMENTS,
        created_at=NOW,
    )
    result = invoke_sync(
        capability_registry().get("creator.create_content_brief@1.0.0"),
        request,
        make_context(capability_name="create_content_brief"),
    )
    assert result.machine_message == "ZEO_CREATOR_PUBLICATION_LEAKAGE"


def test_missing_connector_dependency_fails_closed() -> None:
    capability = capability_registry().get("creator.research_synthesis@1.0.0")
    request = capability.request_model.model_validate(capability.definition.examples[0].request)
    context = make_context(capability_name="research_synthesis")
    assert capability.is_available(context) is False
    assert invoke_sync(capability, request, context).machine_message == "ZEO_CAP_UNAVAILABLE"


def test_receipt_contract_rejects_credential_fields() -> None:
    with pytest.raises(ValidationError):
        PublicationReceipt.model_validate(
            {
                "receipt_id": "receipt_fixture",
                "created_at": NOW,
                "organization_id": "org",
                "publication_id": "publication-a.example",
                "operation_id": "operation_fixture",
                "provider_kind": "example.provider",
                "connection_ref": "connection_fixture",
                "provider_operation_ref": "provider_fixture",
                "executed_at": NOW,
                "outcome": "accepted",
                "reconciliation_state": ReconciliationState.CONFIRMED,
                "access_token": "must-not-enter-contracts",
            }
        )
