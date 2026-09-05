"""Invoke a pure capability and receive a typed Ducktyper brief."""

import json

from zeo_core.tools import invoke_sync

from zeo_creator.capabilities.create_ducktyper_brief import CreateDucktyperBriefResponse
from zeo_creator.registry import capability_registry
from zeo_creator.runtime import make_context


def main() -> None:
    capability = capability_registry().get("creator.create_ducktyper_brief@1.0.0")
    request = capability.request_model.model_validate(capability.definition.examples[0].request)
    result = invoke_sync(
        capability,
        request,
        make_context(capability_name="create_ducktyper_brief"),
    )
    if not isinstance(result.data, CreateDucktyperBriefResponse):
        raise RuntimeError(result.human_message)

    brief = result.data.brief
    print(
        json.dumps(
            {
                "brief_id": brief.brief_id,
                "publication_id": brief.publication_id,
                "deliverable_kind": brief.deliverable_kind,
                "content_digest": brief.content_digest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
