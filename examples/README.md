# Runnable examples

Every example is credential-free, deterministic, and exercised by CI.

| Example | Demonstrates |
|---|---|
| [`inspect_capabilities.py`](inspect_capabilities.py) | Manifest discovery, effects, and required services |
| [`create_content_brief.py`](create_content_brief.py) | Pure capability invocation and a typed producer-neutral brief |
| [`research_connector.py`](research_connector.py) | Runtime injection of a provider-neutral evidence source |
| [`validate_and_prepare.py`](validate_and_prepare.py) | Artifact validation and write-free distribution preparation |
| [`assess_performance.py`](assess_performance.py) | Legacy v1 injection of already-collected metrics |
| [`email_marketing.py`](email_marketing.py) | Three isolated publications, campaigns, sequences, fake lowering and input-only assessment |
| [`complete_content_portfolio.py`](complete_content_portfolio.py) | Validation of the neutral two-publication reference portfolio |

From the repository root:

```console
uv sync --frozen
make examples
```

The examples deliberately use in-memory ports and synthetic observations. A
production runner acquires observations through Zeocore/ZEOconnect before Creator
invocation. Canonical email capabilities receive input artifacts without connectors.
