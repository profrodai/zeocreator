# Capability catalog

All capability IDs are stable at `1.0.0`. Each manifest includes JSON request
and response schemas, effects, requirements, examples, projections, and typed
error codes.

| Capability | Input focus | Output | Effect |
|---|---|---|---|
| `creator.research_synthesis@1.0.0` | Publication, research window, evidence queries | `ResearchSynthesis` | Read |
| `creator.plan_content_portfolio@1.0.0` | Syntheses, objectives, history, requirements, planning window | `ContentPortfolioPlan` | None |
| `creator.create_content_brief@1.0.0` | Assignment, synthesis, profile, creative direction | `ContentBrief` | None |
| `creator.validate_delivery@1.0.0` | Brief, artifact manifest, profile, synthesis, channel plan | `DeliveryReviewBundle` | None |
| `creator.prepare_distribution@1.0.0` | Accepted review and exact channel plan | Publication proposals | None |
| `creator.assess_performance@1.0.0` | Profile, metric queries, objective | Performance assessment | Read |

Use `zeo-creator capabilities --json` for canonical manifests or
`zeo-creator capabilities --projection openai` for function-tool projections.

Zeocore 0.6 requires every manifest to carry at least one effect kind. The four
pure transformations therefore conservatively declare `read` and additionally
publish `execution: pure-deterministic`; they do not read external state. This
compatibility boundary can be removed if Zeocore gains an explicit pure effect.

Composition, scheduling, retries, approval waits, and effect authorization are
runtime concerns; the package deliberately exposes no monolithic workflow.
