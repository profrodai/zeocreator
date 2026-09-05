# Getting started

You can adopt ZEO Creator incrementally. Start with a deterministic local
capability, then inject read connectors, and only introduce a managed runtime
when you need recurring commitments and authorized provider effects.

## Choose your path

=== "I am evaluating the package"

    1. [Install from Git](installation.md).
    2. [Invoke your first capability](first-capability.md).
    3. Run `make examples` in a clone.

=== "I am building a creator workflow"

    1. Read the [daily portfolio tutorial](../tutorials/daily-portfolio.md).
    2. Implement an [evidence source port](../guides/connectors.md).
    3. Hand accepted briefs to [Ducktyper](../guides/ducktyper.md).

=== "I am integrating a managed runtime"

    1. Learn the [architecture boundary](../concepts/architecture.md).
    2. Follow the [runner integration guide](../guides/runner-integration.md).
    3. Keep effect authorization outside ZEO Creator.

## What you need

- Python 3.14 or newer
- `uv` or another Python package installer
- Zeocore 0.6.0, installed automatically and pinned exactly
- No credentials for the quickstart or examples

When you introduce real sources, your runner—not the capability request—must own
connections and credentials.
