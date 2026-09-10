# zeocreator 0.5.4

**Source candidate — not yet published.** Creator now consumes
`zeocore[runtime-host]==0.11.0` and exposes its complete provider inventory and
canonical request preparation for Runtime. The shared Core host invokes the
existing factory `zeo_creator.registry:capability_registry`.

The installed `runtime_portfolio` example emits the real planner request. The
Creator/Core subprocess conformance gate exercises actual planner invocation,
artifact acceptance and negative paths with a labelled test IPC peer. Runtime's
Go supervisor, durable operation recovery and managed-agent proof remain its
integration acceptance work. Two acquisition capabilities require service ports
not injected by Core's first host and correctly remain unavailable.

All 29 capability IDs, business schemas and email receipt corpus remain compatible.
Build/install the candidate wheel as described in
[the integration guide](docs/guides/runtime-host.md); publication is a separate act.

The previous release notes are retained below as historical release evidence.

# zeocreator 0.5.3

**The first PyPI release brings independently reviewed, provider-neutral email
campaigns, newsletters and linear sequences to ZEO Creator.**

## Get started

```console
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python "zeocreator==0.5.3"
.venv/bin/zeo-creator doctor --json
.venv/bin/python -m zeo_creator.examples.create_content_brief
.venv/bin/python -m zeo_creator.examples.email_marketing
```

With pip, install `zeocreator==0.5.3` in a Python 3.14+ virtual environment.
The distribution is `zeocreator`, the import is `zeo_creator`, and the CLI is
`zeo-creator`. Zeocore 0.9.0 is installed automatically. Remove the older Git-only
`zeo-creator` distribution first, or start in a fresh environment.

## What ships

- 29 independently composable capabilities, including nine input-only email v4
  capabilities for campaigns, releases, sequences, messages, review, exact
  delivery preparation, operation proposals and aggregate assessment.
- Immutable publication-scoped artifacts with RFC 8785 digests; distinct test,
  broadcast, activation, enrolment, cancellation and migration proposals.
- Exact normalized receipt validation and 135 portable conformance cases covering
  all six result kinds and twelve effects, with lifecycle and binding negatives.
- Seven runnable installed examples, including eight email programs across three
  isolated publications, producing 104 simulated proposals without credentials.
- Packaged JSON Schemas, reference data, digest vectors, documentation and typed APIs.
- An OIDC publish workflow with verification, exact-version index smoke tests and
  GitHub release notes, following Zeocore's release pattern.

The final email implementation and follow-ups received independent approval with
no remaining findings. All prior schema and corpus bytes remain preserved.

## Compatibility and boundaries

This is an early 0.x release, not a 1.x stability commitment. Existing non-email
v1 capabilities remain available. Email preparation uses v4; historical v1/v2/v3
schemas are retained for audit, not approval reuse. The package rename changes
installer metadata only; Python imports and CLI spelling are preserved.

Creator plans, composes, validates and evaluates supplied artifacts. It does not
send mail, authenticate accounts, authorize effects or schedule workflows.
HubSpot-shaped and Kit-shaped examples are offline conformance hosts. Live
HubSpot Marketing/Kit interoperability still requires Zeocore/ZEOconnect/Runtime
integration and qualification; installing this release does not establish it.

[Documentation](https://profrodai.github.io/zeocreator/) ·
[Installation](https://profrodai.github.io/zeocreator/getting-started/installation/) ·
[Email guide](https://profrodai.github.io/zeocreator/guides/email-marketing/) ·
[Changelog](https://github.com/profrodai/zeocreator/blob/v0.5.3/CHANGELOG.md)
