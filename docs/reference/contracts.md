# Contract API

ZEO Creator ships its versioned JSON Schemas inside the wheel and commits copies
under [`reference/schemas`](https://github.com/profrodai/zeocreator/tree/main/reference/schemas).

```console
zeo-creator contracts list --json
zeo-creator contracts export --output=./schemas
zeo-creator contract-schema --name=content-brief --version=1
```

Every catalog entry contains the stable name, contract major, filename, and RFC
8785 canonical SHA-256 digest. Consumers should pin both the contract name and
major, then verify the digest before accepting an exported schema.

## Compatibility and version axes

ZEO Creator versions three surfaces independently:

| Axis | Example | Changes when |
|---|---|---|
| Package | `0.2.0.dev0` | Code, documentation, or bundled contracts are released |
| Capability | `creator.create_content_brief@1.0.0` | Request/response behavior or orchestration-facing semantics change |
| Contract schema | `content-brief@1` | Serialized contract compatibility changes |

Package releases may add implementations or documentation without changing a
capability or schema version. Backward-compatible schema additions remain within
the same major only when existing strict consumers can accept them; otherwise a
new schema major and filename are required. Capability IDs change independently
when the invocation contract or observable behavior is incompatible. During the
pre-release line, removed names receive no compatibility aliases.

## Publication and evidence

::: zeo_creator.contracts.publications

::: zeo_creator.contracts.evidence

## Editorial planning

::: zeo_creator.contracts.editorial

## Production boundary

::: zeo_creator.contracts.production

## Delivery and distribution

::: zeo_creator.contracts.delivery

::: zeo_creator.contracts.distribution

## Performance

::: zeo_creator.contracts.performance

## Common identity and canonicalization

::: zeo_creator.contracts.common
