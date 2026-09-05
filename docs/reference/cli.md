# CLI reference

The CLI is intentionally small. It supports discovery and diagnostics, not
production workflow orchestration.

## `zeo-creator capabilities`

List the six capability manifests:

```console
zeo-creator capabilities
```

Emit canonical JSON:

```console
zeo-creator capabilities --json
```

Emit OpenAI-compatible function projections:

```console
zeo-creator capabilities --projection openai
```

## `zeo-creator doctor`

Check the interpreter, exact Zeocore version, manifest discovery, and projection
compatibility:

```console
zeo-creator doctor --json
```

## `zeo-creator --version`

```console
zeo-creator --version
```

## What is intentionally absent

There is no daily-run, schedule, approve, publish, OAuth, credential, or daemon
command. Those operations belong to Sovereign Agent, a ZEO runtime, or managed
connection infrastructure.
