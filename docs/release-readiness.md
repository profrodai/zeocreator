# Release readiness

## Current status

ZEO Creator is a pre-release contract and reference package. The source exposes
six producer-neutral capabilities, strict domain contracts, RFC 8785 digests,
packaged JSON Schemas, neutral fixtures, and credential-free examples.

The deterministic reference workflow produces two publication syntheses, a
caller-defined portfolio, eight briefs across four public content kinds, eight
artifact bundles, eight delivery reviews, sixteen multi-channel proposals, and
two separate performance assessments.

## Proven gates

- Ruff and strict mypy pass.
- Unit, contract, invariant, example, and architecture tests pass.
- Reference schemas and examples regenerate deterministically.
- JavaScript verifies the canonical digest vectors.
- Documentation builds in strict mode.
- Wheel and source distribution checks install into a clean environment.
- Offline doctor verifies Python, Zeocore, manifests, and projections.
- CI performs no live provider write.

## Remaining product evidence

Before a stable package release, an external production adapter should consume
the exported `ContentBrief` schema, create a real artifact bundle, emit a
conforming `ArtifactManifest`, and pass validation against authorized read-only
evidence. This proof belongs in the integrating system and must not introduce
producer-specific contracts into the public package.

## Explicit blockers

PyPI publication, repository-history rewriting, live provider effects, and
production credential use each require a separate operator ruling. None is
authorized by this readiness report.
