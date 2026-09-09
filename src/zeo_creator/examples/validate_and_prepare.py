"""Validate a synthetic artifact bundle, then prepare—but do not execute—distribution."""

import json

from zeo_core.tools import invoke_sync

from zeo_creator.capabilities.prepare_distribution import (
    PrepareDistributionRequest,
    PrepareDistributionResponse,
)
from zeo_creator.capabilities.validate_delivery import (
    ValidateDeliveryRequest,
    ValidateDeliveryResponse,
)
from zeo_creator.registry import capability_registry
from zeo_creator.runtime import make_context


def main() -> None:
    registry = capability_registry()
    validate = registry.get("creator.validate_delivery@1.0.0")
    validate_request = ValidateDeliveryRequest.model_validate(
        validate.definition.examples[0].request
    )
    validation = invoke_sync(
        validate,
        validate_request,
        make_context(capability_name="validate_delivery"),
    )
    if not isinstance(validation.data, ValidateDeliveryResponse):
        raise RuntimeError(validation.human_message)

    review = validation.data.review
    if not review.ready_for_approval:
        raise RuntimeError("example artifact unexpectedly failed validation")

    prepare = registry.get("creator.prepare_distribution@1.0.0")
    preparation = invoke_sync(
        prepare,
        PrepareDistributionRequest(
            brief=validate_request.brief,
            manifest=validate_request.manifest,
            review=review,
            channel_plan=validate_request.channel_plan,
            created_at=validate_request.created_at,
        ),
        make_context(capability_name="prepare_distribution"),
    )
    if not isinstance(preparation.data, PrepareDistributionResponse):
        raise RuntimeError(preparation.human_message)

    print(
        json.dumps(
            {
                "ready_for_approval": review.ready_for_approval,
                "approval_digest": review.approval_digest,
                "proposals": [
                    {
                        "operation_id": item.operation_id,
                        "channel": item.channel,
                        "provider_kind": item.destination.provider_kind,
                        "selected_artifact_refs": item.selected_artifact_refs,
                        "idempotency_key": item.idempotency_key,
                    }
                    for item in preparation.data.operations
                ],
                "executed_operations": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
