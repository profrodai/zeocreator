# ADR 0001: Zeocore version and runtime boundary

- Status: Accepted
- Date: 2026-09-05
- Decision owners: ZEO Creator principal

## Context

The Phase 0 capability migration pinned Zeocore 0.5.0 and Python 3.13. On
2026-09-05, the public package index reports Zeocore 0.6.0 as the current
release and declares Python 3.14 or newer. The local Zeocore source checkout
also identifies as 0.6.0, but its `main` contains commits after the `v0.6.0`
tag, including unreleased connection-contract work. Its remote additionally
contains 0.7.0 release preparation.

ZEO Creator needs the stable capability authoring, manifest, effects,
requirements, guard, projection, and `ToolContext` service contracts. It does
not need to own or duplicate runtime authorization, connector custody, or
provider execution.

## Decision

ZEO Creator consumes exactly `zeocore==0.6.0` from the released Python
distribution and requires Python 3.14 or newer.

No floating Git branch, local editable checkout, post-tag 0.6 source state, or
unreleased 0.7 contract is a supported dependency. Provider-neutral creator
ports are injected as named `ToolContext.services`; they are deliberately small
consumer protocols, not a connector framework. A local Zeocore connector or a
ZEOconnect-backed proxy may implement those ports. The controlling runtime owns
connection lookup, credential custody, policy, authorization, retries,
execution, receipts, and reconciliation.

ZEO Creator capabilities may request read observations through injected ports.
They may only construct proposed external-write operations. They never resolve
credentials or call provider SDKs.

Zeocore 0.6 requires every capability manifest to declare at least one
`EffectKind`; it has no explicit pure/local kind. Creator's four deterministic
transformations therefore declare the conservative `read` kind and add
`execution: pure-deterministic` metadata. Those functions do not access external
state. Creator will not change Zeocore's public contract to work around this
limitation.

## Compatibility boundary

CI verifies:

- the interpreter is Python 3.14 or newer;
- installed Zeocore is exactly 0.6.0;
- all six manifests and OpenAI-compatible projections render;
- missing context services fail closed; and
- creator domain modules do not import provider SDKs or runtime products.

Adopting a later Zeocore release requires a separate reviewed dependency
change, contract tests against that release, and an amendment or successor ADR.
