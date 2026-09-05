"""Invoke a pure capability and receive a typed, producer-neutral content brief."""

import json

from zeo_core.tools import invoke_sync

from zeo_creator.capabilities.create_content_brief import CreateContentBriefResponse
from zeo_creator.registry import capability_registry
from zeo_creator.runtime import make_context


def main() -> None:
    capability = capability_registry().get("creator.create_content_brief@1.0.0")
    request = capability.request_model.model_validate(capability.definition.examples[0].request)
    result = invoke_sync(
        capability,
        request,
        make_context(capability_name="create_content_brief"),
    )
    if not isinstance(result.data, CreateContentBriefResponse):
        raise RuntimeError(result.human_message)

    brief = result.data.brief
    print(
        json.dumps(
            {
                "brief_id": brief.brief_id,
                "publication_id": brief.publication_id,
                "content_kind": brief.content_kind,
                "content_digest": brief.content_digest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
