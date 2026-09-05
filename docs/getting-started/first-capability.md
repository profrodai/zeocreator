# Your first capability

This example invokes `creator.create_ducktyper_brief@1.0.0`. It is deterministic,
requires no connector, performs no I/O, and produces a fully typed brief.

## Run it

```console
uv run python examples/create_brief.py
```

The complete example is short enough to read in one pass:

```python
--8<-- "examples/create_brief.py"
```

You should receive identifiers like:

```json
{
  "brief_id": "brief_…",
  "publication_id": "example.org",
  "deliverable_kind": "animated_episode",
  "content_digest": "sha256:…"
}
```

## What happened?

1. `capability_registry()` returned the explicit six-capability registry.
2. `registry.get(...)` resolved a stable, versioned capability ID.
3. The manifest's example became a validated request model.
4. `invoke_sync` ran the capability through Zeocore's runner-neutral invocation.
5. The response carried a `DucktyperBrief`, including its discriminated format
   payload, source references, brand reference, revision, and canonical digest.

## Inspect before invoking

Every capability publishes its contract metadata:

```python
definition = create_brief.definition
print(definition.request_schema)
print(definition.response_schema)
print(definition.effects)
print(definition.error_codes)
```

Or use the CLI:

```console
zeo-creator capabilities --json
zeo-creator capabilities --projection openai
```

Next, learn how to [inject a read connector](../guides/connectors.md) or follow
the [complete daily-loop tutorial](../tutorials/daily-portfolio.md).
