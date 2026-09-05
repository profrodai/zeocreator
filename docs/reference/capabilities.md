# Capability catalog

The registry contains exactly six public capabilities. IDs are stable and
versioned; runners should resolve the full canonical ID.

## Discover the catalog

```python
--8<-- "examples/inspect_capabilities.py"
```

## `creator.research_synthesis@1.0.0`

Retrieves permitted observations through `creator.evidence_source` and produces
one `ResearchSynthesis`.

- **Input:** organization, `PublicationProfile`, research window, evidence
  queries, content-history references
- **Output:** one publication-scoped synthesis
- **Effects:** read, external communication
- **Requirement:** `creator.evidence_source`
- **Deterministic after observations:** yes

## `creator.plan_daily_portfolio@1.0.0`

Plans a format-balanced portfolio from profiles, syntheses, objectives, history,
and constraints.

- **Input:** matching profiles/syntheses/objectives, recent history, constraints
- **Output:** `DailyEditorialPlan`
- **Effects:** local deterministic transform
- **Dogfood invariant:** three formats × two publications = six assignments

## `creator.create_ducktyper_brief@1.0.0`

Converts one assignment into one renderer-independent `DucktyperBrief`.

- **Input:** assignment, matching profile and synthesis, content revision
- **Output:** discriminated animated, HUD, or comic brief
- **Effects:** local deterministic transform

## `creator.validate_delivery@1.0.0`

Validates Ducktyper's artifact and render manifest against the accepted brief,
evidence, brand profile, technical checks, and channel plan.

- **Input:** brief, artifact, manifest, profile, synthesis, channel plan
- **Output:** `DeliveryReviewBundle` and approval digest
- **Effects:** local deterministic transform

## `creator.prepare_distribution@1.0.0`

Creates provider-neutral publication proposals without executing them.

- **Input:** accepted delivery chain and unchanged channel plan
- **Output:** one `ProposedPublicationOperation` per destination
- **Effects:** local deterministic transform; no provider write
- **Later runtime effects:** write and external communication

## `creator.assess_performance@1.0.0`

Retrieves permitted metrics through `creator.metrics_source` and interprets them
against one publication objective.

- **Input:** publication, metrics queries, objective
- **Output:** one `DailyPerformanceAssessment`
- **Effects:** read, external communication
- **Requirement:** `creator.metrics_source`

## Machine-readable forms

```console
zeo-creator capabilities --json
zeo-creator capabilities --projection openai
```

Committed request and response schemas live in the
[`reference/schemas`](https://github.com/profrodai/zeocreator/tree/main/reference/schemas)
directory.

!!! info "Pure effects on Zeocore 0.6"

    Zeocore 0.6 requires a non-empty effect set and has no `pure` effect kind.
    Local transforms therefore declare `read` with
    `metadata.execution=pure-deterministic`; they request no service and perform
    no I/O. This compatibility boundary is tested and documented in the ADR.
