"""Input-only receipt consumption shared by hosts; never execution or authentication."""

from zeo_creator.contracts.email_marketing import (
    EmailContentResult,
    EmailDeliveryPackage,
    EmailEffectIntent,
    EmailRemoteReceipt,
    EmailSequenceResult,
    ProposedEmailOperation,
)
from zeo_creator.services.email_marketing import current, refuse


def validate_operation_receipt(
    proposal: ProposedEmailOperation,
    receipt: EmailRemoteReceipt,
    *,
    package: EmailDeliveryPackage | None = None,
) -> EmailRemoteReceipt:
    """Bind supplied normalized evidence to its exact proposal and creative material.

    The host authenticates the issuer, receipt contract, remote ownership and current
    state before calling. This function verifies correspondence, not host authority,
    delivery, consent, or the truth of any provider claim. It preserves ambiguous and
    needs_review outcomes; it never upgrades them to confirmed or retries an effect.
    Historical package/proof expiry does not prevent consuming a later receipt.
    """
    current(proposal, receipt, package)
    material = proposal.material
    if (
        (receipt.organization_id, receipt.publication_id)
        != (proposal.organization_id, proposal.publication_id)
        or receipt.operation != proposal.binding()
        or receipt.campaign_release != material.campaign_release
        or receipt.execution != material.execution
        or receipt.result.intent != material.intent
        or receipt.created_at < proposal.created_at
    ):
        refuse("receipt_proposal_binding_mismatch")
    if isinstance(receipt.result, EmailContentResult):
        if material.intent == EmailEffectIntent.CANCEL:
            prior = material.prior_receipt
            if prior is None or prior.delivery != material.target_delivery:
                refuse("receipt_cancellation_target_missing")
            expected_delivery = material.target_delivery
            expected_message = prior.message_plan
            expected_audience = prior.result.audience
            if package is not None and package.binding() != expected_delivery:
                refuse("receipt_delivery_package_mismatch")
        else:
            if package is None:
                refuse("receipt_delivery_package_required")
            if (
                package.binding() != material.delivery
                or package.approval_digest != material.delivery_approval_digest
                or package.material.campaign_release != material.campaign_release
                or package.material.execution != material.execution
                or (
                    material.audience is not None
                    and package.material.audience_snapshot != material.audience
                )
            ):
                refuse("receipt_delivery_package_mismatch")
            expected_delivery = package.binding()
            expected_message = package.material.draft.message_plan
            expected_audience = package.material.audience_snapshot
        if (
            receipt.delivery != expected_delivery
            or receipt.message_plan != expected_message
            or receipt.result.audience != expected_audience
        ):
            refuse("receipt_content_binding_mismatch")
    elif isinstance(receipt.result, EmailSequenceResult):
        if package is not None:
            refuse("receipt_unexpected_delivery_package")
        if receipt.sequence != material.sequence or receipt.result.audience != material.audience:
            refuse("receipt_sequence_binding_mismatch")
    expected_remote = material.target_remote_ref
    if material.intent == EmailEffectIntent.MIGRATE:
        if material.migration is None:
            refuse("receipt_migration_target_missing")
        expected_remote = material.migration.target_receipt.remote_ref
    if expected_remote is not None and receipt.remote_ref != expected_remote:
        refuse("receipt_remote_target_mismatch")
    return receipt
