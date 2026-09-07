"""Fake third-party runtime and lowering conformance. No provider execution is implemented.

These example operation identities are NOT Zeocore's forthcoming email vocabulary.
The in-memory journal illustrates host obligations and is not production persistence.
"""

from datetime import datetime
from typing import Literal

from zeo_core.contracts import CapabilityId

from zeo_creator.contracts.common import canonical_digest, stable_id
from zeo_creator.contracts.email_marketing import (
    Digest,
    EmailArtifactRef,
    EmailCampaignRelease,
    EmailDeliveryPackage,
    EmailEffectIntent,
    EmailModel,
    EmailSequencePlan,
    OpaqueRef,
    ProposedEmailOperation,
)
from zeo_creator.services.email_marketing import current, propose_operation, refuse, scope

Shape = Literal["hubspot-shaped", "kit-shaped"]
Outcome = Literal["accepted", "ambiguous", "needs_review"]


def operation_identity(intent: EmailEffectIntent) -> CapabilityId:
    return CapabilityId(namespace="example.email", name=intent.value, version="1.0.0")


def operation_contract_digest(intent: EmailEffectIntent) -> str:
    return canonical_digest(
        {"simulation": True, "intent": intent, "operation": operation_identity(intent)}
    )


class SimulatedLoweringReceipt(EmailModel):
    simulation: Literal[True] = True
    receipt_id: OpaqueRef
    creator_artifact: EmailArtifactRef
    provider_shape: Shape
    connector_revision: Literal["simulation-1"] = "simulation-1"
    submitted_payload_digest: Digest
    provider_observed_payload_digest: Digest | None
    transformation: Literal["none", "material", "unknown"]
    remote_ref: OpaqueRef
    idempotency_identity: OpaqueRef
    outcome: Outcome


def lower(package: EmailDeliveryPackage, shape: Shape) -> dict[str, object]:
    """Consume the same neutral material into two deliberately fake wire shapes."""
    current(package)
    draft = package.material.draft
    if (
        draft.personalization
        or "{{" in draft.html + draft.plain_text + draft.subject + draft.preheader
    ):
        refuse("simulation_personalization_renderer_unavailable")
    if shape == "hubspot-shaped":
        return {
            "subject": draft.subject,
            "previewText": draft.preheader,
            "content": {"html": draft.html, "plainText": draft.plain_text},
            "senderRef": draft.sender_identity.model_dump(mode="json"),
            "replyToRef": draft.reply_to_identity.model_dump(mode="json"),
            "links": [row.model_dump(mode="json") for row in draft.links],
            "materialDigest": package.approval_digest,
        }
    return {
        "subject": draft.subject,
        "preview_text": draft.preheader,
        "content_html": draft.html,
        "content_text": draft.plain_text,
        "sender_ref": draft.sender_identity.model_dump(mode="json"),
        "reply_to_ref": draft.reply_to_identity.model_dump(mode="json"),
        "links": [row.model_dump(mode="json") for row in draft.links],
        "material_digest": package.approval_digest,
    }


class SimulatedEmailHost:
    """Illustrative, process-local approval/idempotency/reconciliation harness."""

    def __init__(self, shape: Shape) -> None:
        self.shape = shape
        self.submissions = 0
        self._journal: dict[str, tuple[str, SimulatedLoweringReceipt]] = {}

    def simulate(
        self,
        proposal: ProposedEmailOperation,
        approved_digest: str,
        at: datetime,
        *,
        package: EmailDeliveryPackage | None = None,
        release: EmailCampaignRelease | None = None,
        source_sequence: EmailSequencePlan | None = None,
        sequence: EmailSequencePlan | None = None,
        supported_semantics: tuple[str, ...] = (),
        outcome: Outcome = "accepted",
    ) -> SimulatedLoweringReceipt:
        current(proposal)
        material = proposal.material
        if approved_digest != proposal.approval_digest:
            refuse("simulation_approval_mismatch")
        if material.operation != operation_identity(
            material.intent
        ) or material.operation_contract_digest != operation_contract_digest(material.intent):
            refuse("simulation_operation_contract_mismatch")
        # A retry returns the existing logical operation, even after snapshot expiry.
        key = f"{proposal.organization_id}/{proposal.publication_id}/{canonical_digest(proposal.material.execution)}/{proposal.idempotency_key}"
        previous = self._journal.get(key)
        if previous:
            if previous[0] != proposal.approval_digest:
                refuse("simulation_conflicting_idempotency_reuse")
            return previous[1]
        if material.audience and (
            not material.audience.resolved_at <= at < material.audience.expires_at
            or material.audience.drift_status != "unchanged"
            or material.audience.eligible_count == 0
        ):
            refuse("simulation_snapshot_not_current")
        expected_shape = (
            "hubspot-shaped"
            if material.execution.provider_kind == "hubspot-marketing"
            else "kit-shaped"
        )
        if self.shape != expected_shape:
            refuse("simulation_execution_provider_mismatch")
        if release is None:
            refuse("simulation_campaign_release_required")
        propose_operation(
            material,
            at,
            proposal.idempotency_key,
            release=release,
            package=package,
            sequence=sequence,
            source_sequence=source_sequence,
        )
        payload: dict[str, object] = {
            "intent": material.intent,
            "material": material.model_dump(mode="json"),
        }
        artifact: EmailArtifactRef | None = None
        if material.delivery:
            if not package:
                refuse("simulation_delivery_required")
            scope(proposal, package)
            if (
                package.binding() != material.delivery
                or package.approval_digest != material.delivery_approval_digest
                or (material.audience and material.audience != package.material.audience_snapshot)
            ):
                refuse("simulation_delivery_or_audience_changed")
            if material.intent == EmailEffectIntent.SCHEDULE and (
                package.material.schedule_intent is None or package.material.schedule_intent <= at
            ):
                refuse("simulation_schedule_not_future")
            if (
                material.intent == EmailEffectIntent.SEND
                and package.material.schedule_intent is not None
            ):
                refuse("simulation_immediate_send_cannot_reuse_schedule")
            payload["delivery"] = lower(package, self.shape)
            artifact = package.binding()
        if material.sequence:
            if not sequence:
                refuse("simulation_sequence_required")
            scope(proposal, sequence)
            if sequence.binding() != material.sequence:
                refuse("simulation_sequence_revision_changed")
            if not set(sequence.required_provider_semantics) <= set(supported_semantics):
                refuse("simulation_provider_semantics_unsupported")
            artifact = sequence.binding()
        if artifact is None:
            artifact = proposal.binding()
        digest = canonical_digest(payload)
        receipt = SimulatedLoweringReceipt(
            receipt_id=stable_id("simulated_receipt", proposal.approval_digest),
            creator_artifact=artifact,
            provider_shape=self.shape,
            submitted_payload_digest=digest,
            provider_observed_payload_digest=digest if outcome == "accepted" else None,
            transformation="none"
            if outcome == "accepted"
            else "material"
            if outcome == "needs_review"
            else "unknown",
            remote_ref=stable_id("simulated_remote", proposal.approval_digest),
            idempotency_identity=proposal.idempotency_key,
            outcome=outcome,
        )
        self.submissions += 1
        self._journal[key] = (proposal.approval_digest, receipt)
        return receipt

    def reconcile(
        self, proposal: ProposedEmailOperation, observed_payload_digest: str
    ) -> SimulatedLoweringReceipt:
        current(proposal)
        key = f"{proposal.organization_id}/{proposal.publication_id}/{canonical_digest(proposal.material.execution)}/{proposal.idempotency_key}"
        entry = self._journal.get(key)
        if not entry or entry[0] != proposal.approval_digest:
            refuse("simulation_reconciliation_operation_mismatch")
        previous = entry[1]
        matched = observed_payload_digest == previous.submitted_payload_digest
        data = previous.model_dump(mode="python")
        data.update(
            provider_observed_payload_digest=observed_payload_digest,
            transformation="none" if matched else "material",
            outcome="accepted" if matched else "needs_review",
        )
        receipt = SimulatedLoweringReceipt.model_validate(data)
        self._journal[key] = (proposal.approval_digest, receipt)
        return receipt
