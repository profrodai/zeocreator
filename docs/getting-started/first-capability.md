# Your first capability

This example invokes `creator.create_content_brief@1.0.0`. It is deterministic,
credential-free, and uses the capability's own schema-valid example request.

```console
python -m zeo_creator.examples.create_content_brief
```

After [installation](installation.md), the command above works from any directory.
In a uv project, use `uv run python`. You can also save the complete code below as
`first_capability.py` and run it with your environment’s Python.

```python
--8<-- "examples/create_content_brief.py"
```

The response contains a producer-neutral `ContentBrief` with an extensible
`content_kind`, evidence claims, creative direction, delivery requirements, and
a canonical digest.

Next, follow the [content portfolio tutorial](../tutorials/content-portfolio.md)
or learn how to [integrate a production engine](../guides/production-adapters.md).
