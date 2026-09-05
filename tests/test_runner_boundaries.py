"""Proofs for Sovereign-style invocation and a fake governed runtime boundary."""

from dataclasses import dataclass, field

import pytest
from zeo_core.contracts import EffectKind

from tests.fixtures.dogfood import NOW, build_dogfood_snapshot
from zeo_creator.contracts.common import stable_id
from zeo_creator.contracts.distribution import (
    ProposedPublicationOperation,
    PublicationReceipt,
    ReconciliationState,
)


@dataclass
class FakeZeoRuntime:
    """Test-only authority holder; no provider API is contacted."""

    authorized_approval_digests: set[str] = field(default_factory=set)

    def authorize(self, operation: ProposedPublicationOperation) -> None:
        assert operation.required_effects == (
            EffectKind.WRITE,
            EffectKind.EXTERNAL_COMMUNICATION,
        )
        self.authorized_approval_digests.add(operation.approval_digest)

    def execute_with_fake_connector(
        self, operation: ProposedPublicationOperation
    ) -> PublicationReceipt:
        if operation.approval_digest not in self.authorized_approval_digests:
            raise PermissionError("exact approval digest has not been authorized")
        return PublicationReceipt(
            receipt_id=stable_id("receipt", operation.operation_id),
            created_at=NOW,
            organization_id=operation.organization_id,
            publication_id=operation.publication_id,
            input_refs=(operation.operation_id,),
            operation_id=operation.operation_id,
            provider_kind=operation.provider_kind,
            connection_ref=operation.connection_ref,
            provider_operation_ref=stable_id("provider", operation.operation_id),
            executed_at=NOW,
            outcome="accepted by fake connector",
            reconciliation_state=ReconciliationState.CONFIRMED,
        )


def test_sovereign_style_bounded_invocations_produce_complete_chain() -> None:
    snapshot = build_dogfood_snapshot()

    assert len(snapshot.evidence_calls) == 6
    assert len(snapshot.metrics_calls) == 2
    assert all(review.ready_for_approval for review in snapshot.reviews)


def test_fake_runtime_owns_approval_and_effect_execution() -> None:
    operation = build_dogfood_snapshot().operations[0]
    runtime = FakeZeoRuntime()

    with pytest.raises(PermissionError):
        runtime.execute_with_fake_connector(operation)
    runtime.authorize(operation)
    receipt = runtime.execute_with_fake_connector(operation)

    assert receipt.operation_id == operation.operation_id
    assert receipt.publication_id == operation.publication_id
    assert "token" not in receipt.model_dump_json().lower()
