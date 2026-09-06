# ADR 0001: Zeocore version and runtime boundary

- Status: Accepted
- Date: 2026-09-06
- Decision owners: ZEO Creator principal

## Context

The Phase 0 capability migration pinned Zeocore 0.5.0 and Python 3.13, and the
first public Creator boundary moved to Zeocore 0.6.0 and Python 3.14. On
2026-09-06 Zeocore 0.9.0 became the released contract boundary, including the
hosted integration profile and Supabase integration needed by deployed Zeocore
applications.

ZEO Creator needs the stable capability authoring, manifest, effects,
requirements, guard, projection, and `ToolContext` service contracts. It does
not need to own or duplicate runtime authorization, connector custody, or
provider execution.

## Decision

ZEO Creator consumes exactly `zeocore==0.9.0` from the released Python
distribution and requires Python 3.14 or newer.

No floating Git branch, local editable checkout, or unreleased contract is a
supported dependency. The controlling runtime owns connection lookup,
credential custody, policy, authorization, retries, execution, receipts and
reconciliation. Stateful applications acquire provider observations before
invoking Creator; they must not pass connector or ZEOconnect proxies through
Creator's `ToolContext`.

ZEO Creator capabilities may request read observations through injected ports.
They may only construct proposed external-write operations. They never resolve
credentials or call provider SDKs.

Zeocore 0.9 requires every capability manifest to declare at least one
`EffectKind`; it has no explicit pure/local kind. Creator's four deterministic
transformations therefore declare the conservative `read` kind and add
`execution: pure-deterministic` metadata. Those functions do not access external
state. Creator will not change Zeocore's public contract to work around this
limitation.

## Compatibility boundary

CI verifies:

- the interpreter is Python 3.14 or newer;
- installed Zeocore is exactly 0.9.0;
- all registered manifests and OpenAI-compatible projections render;
- missing context services fail closed; and
- creator domain modules do not import provider SDKs or runtime products.

Adopting a later Zeocore release requires a separate reviewed dependency
change, contract tests against that release, and an amendment or successor ADR.
