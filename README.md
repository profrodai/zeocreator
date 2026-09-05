# ZEO Creator

ZEO Creator is a provider-neutral creator-operations capability package built on
Zeocore. It turns publication-scoped evidence into governed editorial plans and
typed Ducktyper briefs, validates Ducktyper renders, prepares digest-bound
distribution proposals, and assesses performance through injected read ports.

It does not schedule work, own credentials, implement OAuth, render media, or
execute provider writes. Sovereign Agent or a ZEO runtime constructs each
invocation, injects authorized connectors through `ToolContext`, owns approvals
and state, and authorizes any later external effect.

Canonical public repository: <https://github.com/profrodai/zeocreator>

## Supported boundary

- Distribution: `zeo-creator`
- Import package: `zeo_creator`
- Python: 3.14 or newer
- Zeocore: exactly 0.6.0
- Ducktyper: external typed brief/render contract; no internal imports

The Zeocore decision and runtime boundary are recorded in
[`docs/adr/0001-zeocore-version-and-runtime-boundary.md`](docs/adr/0001-zeocore-version-and-runtime-boundary.md).

## Capabilities

- `creator.research_synthesis@1.0.0`
- `creator.plan_daily_portfolio@1.0.0`
- `creator.create_ducktyper_brief@1.0.0`
- `creator.validate_delivery@1.0.0`
- `creator.prepare_distribution@1.0.0`
- `creator.assess_performance@1.0.0`

There is deliberately no `run_daily` capability. Scheduling, retry, approval
waits, resumption, effect authorization, and receipt reconciliation belong to
the controlling runtime.

## Local verification

```bash
make setup
make verify
make doctor
make capabilities
```

`zeo-creator capabilities --json` emits canonical manifests. Use
`--projection openai` for runner-compatible function projections. The CLI is a
diagnostic and discovery surface only.

## Dogfood contract

The deterministic acceptance fixture creates two independent research
syntheses and exactly six assignments: one animated episode, one HUD, and one
comic-slides deliverable for each of `profrod.ai` and `zeroemployee.org`. It
then produces six typed briefs, accepts six synthetic Ducktyper render pairs,
validates them, fans them out into provider-neutral proposals, and creates two
separate performance assessments.

All fixture identifiers and evidence are synthetic. No live provider operation
is performed by the fixture or by ZEO Creator.

## Runtime integration

Read capabilities declare required provider-neutral services in their Zeocore
requirements. A runner supplies those services in `ToolContext.services`:

- `creator.evidence_source` implements the evidence-source port.
- `creator.metrics_source` implements the metrics-source port.

Absence fails closed. Connector implementations and credentials remain owned by
the runner, local Zeocore integration, or ZEOconnect. Distribution output is
only a `ProposedPublicationOperation`; a runtime must approve, authorize, and
execute it elsewhere.

## Development status

Repository visibility and placement are operator-owned concerns. Do not publish
the Python distribution or perform live provider writes as part of verification.
See the release-readiness report for the remaining product-release gates.
