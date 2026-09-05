# Legacy removal report

The conversion removed the former research CLI's public names and behavior.

| Area | Result |
|---|---|
| Provider-bound ingest | Replaced by injected, provider-neutral read ports |
| Direct social publishing | Removed; Creator emits proposals only |
| Ambient credentials | Removed from creator-domain code and public models |
| Monolithic workflow orchestration | Removed; controlling runtimes compose capabilities |
| Fixed content factory taxonomy | Replaced by qualified caller-supplied content kinds |
| Producer-specific brief and render schemas | Replaced by generic briefs and artifact bundles |
| Fixed cadence | Replaced by an explicit planning window and quantity requirements |
| Mutable outbox state | Replaced by revisioned, digest-bound proposals |
| Compatibility aliases | Not retained because no stable distribution existed |

Architecture tests prevent provider SDK and runtime-product imports in
capabilities, contracts, and services. Documentation tests keep neutral examples
and public boundaries aligned with the package.
