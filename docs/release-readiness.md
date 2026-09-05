# ZEO Creator release-readiness report

Date: 2026-09-05
Decision: **Repository-ready; Python distribution not yet approved for publication**

## Implemented evidence

- The distribution/import/CLI surfaces are `zeo-creator`, `zeo_creator`, and
  `zeo-creator` respectively.
- Python is declared as 3.14+ and released `zeocore==0.6.0` is locked and checked
  by the offline doctor.
- Six stable, versioned capabilities expose typed request/response schemas,
  requirements, examples, projections, and enumerated errors.
- Provider-neutral read ports fail closed when runner context omits a required
  service.
- The deterministic dogfood fixture produces two property syntheses, six
  assignments, six format-valid Ducktyper briefs, six synthetic artifact/manifest
  pairs, six delivery reviews, twelve multi-channel proposals, and two separate
  performance assessments.
- Validation covers wrong brand, unsupported claim, stale brief digest, and
  missing format elements. Distribution coverage proves schedule mutation
  invalidates approval and fixed inputs preserve idempotency keys.
- A test-only fake ZEO runtime owns exact approval and simulated effect execution;
  ZEO Creator only constructs proposals.
- Architecture tests reject provider/runtime imports and ambient credential or
  direct provider-write strings in creator source.
- JSON schemas and credential-free reference artifacts are committed under
  `reference/` and regenerated with `make reference`.

Zeocore 0.6 has no `pure` effect kind and requires a non-empty effect set. The
four deterministic local transforms therefore declare `read` plus
`metadata.execution=pure-deterministic`; they request no service and perform no
I/O. Research and assessment additionally declare external communication and
the exact injected read-service requirement. This is a documented 0.6 taxonomy
boundary, not a claim that local transforms contact a provider.

## Explicit publication gates

1. PyPI publication and live provider effects require separate approval and have
   not occurred.
2. Ducktyper must confirm the external JSON brief/render boundary during
   dogfooding before a distribution release decision.

The operator owns GitHub visibility and repository placement. The canonical
public source repository is `profrodai/zeocreator`; the private historical source
repository remains a separate implementation record.

## Remaining risks

- Real connector implementations may expose provenance or pagination behaviours
  not represented by the fake ports; integration must occur in an authorized
  runner without widening creator contracts.
- A later Zeocore release may add a pure-effect representation or different
  connection conventions. Adoption requires a reviewed dependency change and
  an ADR update.
- The synthetic render checks prove binding and policy mechanics, not media
  quality; Ducktyper integration must provide its own deterministic technical
  checks and manifests.

## Publication decision

The repository code may land. Before publishing the Python distribution, conduct
the Ducktyper boundary dogfood and make a separate release ruling. No current
approval authorizes PyPI publication, remote rename, repository transfer, or
provider writes.
