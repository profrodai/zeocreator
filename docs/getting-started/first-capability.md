# Your first capability

This example invokes `creator.create_content_brief@1.0.0`. It is deterministic,
credential-free, and uses the capability's own schema-valid example request.

```console
uv run python examples/create_content_brief.py
```

```python
--8<-- "examples/create_content_brief.py"
```

The response contains a producer-neutral `ContentBrief` with an extensible
`content_kind`, evidence claims, creative direction, delivery requirements, and
a canonical digest.

Next, follow the [content portfolio tutorial](../tutorials/content-portfolio.md)
or learn how to [integrate a production engine](../guides/production-adapters.md).
