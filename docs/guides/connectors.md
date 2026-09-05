# Inject research connectors

ZEO Creator defines small consumer ports. Your runner supplies implementations
using local Zeocore connectors, hosted ZEOconnect proxies, or deterministic test
adapters.

## Implement the evidence port

```python
from zeo_creator.contracts.evidence import EvidenceItem, EvidenceQuery
from zeo_creator.contracts.publications import PublicationProfile


class MyEvidenceSource:
    def retrieve(
        self,
        query: EvidenceQuery,
        publication: PublicationProfile,
    ) -> tuple[EvidenceItem, ...]:
        observations = my_authorized_connector.read(
            connection_ref=query.connection_ref,
            terms=query.terms,
            starts_at=query.research_window.starts_at,
            ends_at=query.research_window.ends_at,
        )
        return tuple(to_evidence_item(item, publication) for item in observations)
```

The port does not prescribe a provider SDK. It only defines what creator-domain
logic needs from an authorized read.

## Inject it through `ToolContext`

```python
context = make_context(
    capability_name="research_synthesis",
    services={"creator.evidence_source": MyEvidenceSource()},
)
result = invoke_sync(research_capability, request, context)
```

If `creator.evidence_source` is absent, Zeocore reports the capability as
unavailable before creator logic executes.

## Runnable example

```python
--8<-- "examples/research_connector.py"
```

Run it with:

```console
uv run python examples/research_connector.py
```

## Adapter responsibilities

Your adapter must:

- honor the query's connection reference and research window;
- create one `EvidenceItem` per durable observation;
- preserve source kind, source reference, origin, observation time, and URL;
- set `publication_scope` explicitly;
- return no reusable credential material; and
- allow provider failures to become runner-visible typed failures.

ZEO Creator verifies organization scope, publication scope, query provenance, and
canonical digests before synthesizing evidence.

!!! warning "References are not secrets"

    `connection_ref` identifies a runner-owned connection. It must be safe to
    store in an artifact. Never put an access token, cookie, API key, OAuth code,
    or credential serialization in that field.
