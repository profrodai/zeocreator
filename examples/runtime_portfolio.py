"""Print the real portfolio invocation for a trusted Runtime to admit.

No handler, session, artifact publication or provider effect is executed here.
The output is an InvocationRequest, suitable for the shared host's stdin AFTER
Runtime supplies a separately authenticated LaunchContext and private channel.
"""

from zeo_core.adapters.runtime_host.canonical import canonical_bytes

from zeo_creator.provider import prepare_invocation
from zeo_creator.registry import capability_registry


def main() -> None:
    capability_id = "creator.plan_content_portfolio@1.0.0"
    capability = capability_registry().get(capability_id)
    prepared = prepare_invocation(
        canonical_bytes(
            {
                "protocol_version": 1,
                "capability_id": capability_id,
                "arguments": capability.definition.examples[0].request,
            }
        )
    )
    print(canonical_bytes(prepared.request.model_dump(mode="json")).decode())


if __name__ == "__main__":
    main()
