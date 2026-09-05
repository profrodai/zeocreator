# Runnable examples

Every example is credential-free, deterministic, and exercised by CI.

| Example | Demonstrates |
|---|---|
| [`inspect_capabilities.py`](inspect_capabilities.py) | Manifest discovery, effects, and required services |
| [`create_brief.py`](create_brief.py) | Pure capability invocation and a typed Ducktyper brief |
| [`research_connector.py`](research_connector.py) | Runtime injection of a provider-neutral evidence source |
| [`validate_and_prepare.py`](validate_and_prepare.py) | Render validation and write-free distribution preparation |
| [`assess_performance.py`](assess_performance.py) | Runtime injection of read-only metrics |
| [`complete_daily_portfolio.py`](complete_daily_portfolio.py) | Validation of the six-deliverable reference portfolio |

From the repository root:

```console
uv sync --frozen
make examples
```

The examples deliberately use in-memory ports and synthetic observations. A
production runner supplies authorized Zeocore connectors or ZEOconnect-backed
proxies through `ToolContext.services`.
