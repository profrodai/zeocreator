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

## Contract schemas

List the stable contract catalog:

```console
zeo-creator contracts list --json
```

Export the schemas bundled in the installed wheel:

```console
zeo-creator contracts export --output=./schemas
```

Print one named contract version:

```console
zeo-creator contract-schema --name=content-brief --version=1
```

## `zeo-creator --version`

```console
zeo-creator --version
```

## What is intentionally absent

There is no daily-run, schedule, approve, publish, OAuth, credential, or daemon
command. Those operations belong to Sovereign Agent, a ZEO runtime, or managed
connection infrastructure.
