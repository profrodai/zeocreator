# Legacy removal report

Date: 2026-09-05

The Phase 0 mechanical Zeocore migration exposed ten capabilities. The product
conversion resolves each one as follows; none remains a public API.

| Phase 0 capability | Disposition | ZEO Creator boundary |
|---|---|---|
| `quackresearch.ingest_gmail@1.0.0` | Replaced | Gmail-shaped evidence arrives through the injected evidence read port. |
| `quackresearch.ingest_x@1.0.0` | Replaced | Social evidence arrives through the injected evidence read port. |
| `quackresearch.ingest_reddit@1.0.0` | Replaced | Social evidence arrives through the injected evidence read port. |
| `quackresearch.ingest_github@1.0.0` | Replaced | Repository evidence arrives through the injected evidence read port. |
| `quackresearch.ingest_inbox@1.0.0` | Removed | The Chrome/inbox daemon and capture protocol are outside the first release. |
| `quackresearch.compress@1.0.0` | Absorbed | Provider-neutral normalization and synthesis live behind `creator.research_synthesis`. |
| `quackresearch.analyze@1.0.0` | Absorbed | Theme and opportunity selection support research and portfolio planning services. |
| `quackresearch.plan@1.0.0` | Replaced | `creator.plan_daily_portfolio` and `creator.create_ducktyper_brief` replace ContentPack planning. |
| `quackresearch.review@1.0.0` | Replaced | `creator.validate_delivery` emits a digest-bound review bundle; runtime owns approval state. |
| `quackresearch.publish@1.0.0` | Removed | `creator.prepare_distribution` emits proposals only; runtime-authorized connectors execute elsewhere. |

Removed implementation surfaces:

- the old import package, CLI, database/store, hidden workflow state, and local configuration;
- direct X and LinkedIn HTTP publication and environment-token reads;
- provider SDK ingestion and Gmail OAuth/token-file handling;
- the Chrome capture extension and local inbox server;
- dry-run outbox and live-publish commands;
- autonomous daily workflow commands and friend-facing operator skills; and
- archived newsletter, historic-post, and Quackchat experiments.

No compatibility aliases, old capability IDs, or deprecation shims were kept.
Repository history remains available in Git and in the separately reviewed Phase
0 commit.
