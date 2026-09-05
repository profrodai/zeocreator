<div align="center">

# ZEO Creator

**The open protocol for continuous editorial and creator operations.**

Turn source observations into evolving stories, frozen dossiers, editorial agendas,
editions, production briefs, reviewed artifacts, commentary, newsletters and corrections.

[![CI](https://github.com/profrodai/zeocreator/actions/workflows/ci.yml/badge.svg)](https://github.com/profrodai/zeocreator/actions/workflows/ci.yml)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Zeocore 0.6](https://img.shields.io/badge/Zeocore-0.6.0-087f75)](https://pypi.org/project/zeocore/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Documentation](docs/index.md) · [Quickstart](docs/getting-started/first-capability.md) · [Examples](examples/README.md) · [API reference](docs/reference/contracts.md)

</div>

---

ZEO Creator is an open-source, typed contract and transformation layer for newsrooms,
independent publications and creator teams. It supports live, daily, periodic and
evergreen work without storing newsroom memory, scheduling jobs, possessing
credentials or publishing behind an editor's back.

```mermaid
flowchart LR
    S[Source observations] --> G[Signals and story revisions]
    G --> D[Publication-scoped dossiers]
    D --> A[Agendas and editions]
    A --> B[Briefs, articles, commentary, newsletters]
    B --> X[External producers]
    X --> V[Artifact and editorial review]
    V --> O[Digest-bound proposals]
    O -. runtime approval .-> P[Provider execution]
    P --> M[Performance and corrections]
```

## Why ZEO Creator?

- **Evidence-backed.** Every material brief claim resolves to explicit provenance.
- **Continuous.** Stories evolve across live, daily, periodic, and evergreen windows.
- **Editorially coherent.** Dossiers, agendas, and editions prevent every producer from researching alone.
- **Integrity-aware.** Commentary, journalism, corrections, and qualified-human requirements fail closed.
- **Producer-neutral.** Public briefs express creative intent; adapters own production-specific lowering.
- **Publication-safe.** Organization and publication scope follow every durable artifact.
- **Approval-safe.** Artifact, payload, destination, or schedule changes invalidate approval.
- **Provider-neutral.** Creator code uses injected ports and never owns provider credentials.
- **Runner-ready.** The same capabilities work in a bounded agent workflow or managed runtime.
- **Portable.** RFC 8785 digests and packaged JSON Schemas support Python, TypeScript, and Go consumers.

## Install

The distribution is currently pre-release and installs from Git:

```console
uv add "zeo-creator @ git+https://github.com/profrodai/zeocreator.git"
```

or:

```console
python -m pip install "git+https://github.com/profrodai/zeocreator.git"
```

ZEO Creator requires Python 3.14+ and Zeocore 0.6.0.

## First capability

Every capability publishes typed request and response schemas, effects,
requirements, examples, projections, and enumerated errors.

```python
from zeo_core.tools import invoke_sync

from zeo_creator.capabilities.create_content_brief import CreateContentBriefResponse
from zeo_creator.registry import capability_registry
from zeo_creator.runtime import make_context

capability = capability_registry().get("creator.create_content_brief@1.0.0")
request = capability.request_model.model_validate(capability.definition.examples[0].request)
result = invoke_sync(
    capability,
    request,
    make_context(capability_name="create_content_brief"),
)

if not isinstance(result.data, CreateContentBriefResponse):
    raise RuntimeError(result.human_message)

print(result.data.brief.content_kind)    # article
print(result.data.brief.content_digest)  # sha256:...
```

Run it locally:

```console
git clone https://github.com/profrodai/zeocreator.git
cd zeocreator
uv sync --frozen
uv run python examples/create_content_brief.py
```

## Capability families

| Family | Capabilities | Responsibility |
|---|---|---|
| Research and story | `research_synthesis`, `extract_editorial_signals`, `update_story_revisions`, `build_story_dossier` | Normalize evidence into evolving, frozen editorial knowledge |
| Agenda and production | `plan_editorial_agenda`, `plan_edition`, `plan_content_portfolio`, `create_content_brief` | Select publication work and express producer-neutral intent |
| Commentary | `identify_engagement_opportunities`, `compose_commentary`, `review_commentary` | Participate selectively with context, stance, expiry and human approval |
| Newsletters | `plan_newsletter_issue`, `compose_newsletter_issue`, `review_newsletter_issue` | Produce HTML/plain-text issues from editions and dossiers |
| Journalism | `compose_news_article`, `review_news_article`, `prepare_correction` | Draft attributed reporting and represent corrections with risk gates |
| Delivery and learning | `validate_delivery`, `prepare_distribution`, `assess_performance` | Validate bytes and claims, propose effects, and interpret outcomes |

All 20 capability IDs are independently composable. There is intentionally no
monolithic workflow capability. Scheduling, retries,
approval state, persistence, provider execution, and reconciliation belong to
the controlling runtime.

## Producer contract

`ContentBrief` carries creator intent in a public envelope: content kind,
objective, audience, source document, evidence claims, brand references, target
channels, and declarative delivery requirements. Qualified content kinds are
extensible—`article`, `video.short`, `image.carousel`, or a private namespace.

A producer returns an `ArtifactManifest` containing one or more artifact
descriptors, byte-digest proofs, claim references, and typed attestations. ZEO
Creator validates the envelope and preserves opaque `ExtensionPayload` data but
does not interpret a producer's private schema.

## The editorial kernel

`SourceObservation` records what was retrieved and how complete it was.
`EditorialSignal` explains why it may matter. `StoryRevision` preserves a story's
verified facts, disputed claims, unknowns and status through time. `StoryDossier`
freezes that state for one publication, and `EditorialAgenda` plus `EditionPlan`
turn dossiers into coherent publication decisions.

One dossier can support a breaking update, a daily briefing, a video brief, a
social reply and a later newsletter section without silently sharing voice,
policy or approval across publications. See the
[continuous editorial model](docs/concepts/continuous-editorial-operations.md).

```mermaid
flowchart LR
    C[ZEO Creator] --> B[ContentBrief]
    B --> A[Your adapter]
    A --> P[Your production engine]
    P --> M[ArtifactManifest]
    M --> C
```

## Export schemas

Schemas ship inside the wheel, so non-Python consumers do not need the source tree:

```console
zeo-creator contracts list --json
zeo-creator contract-schema --name=content-brief --version=1
zeo-creator contracts export --output=./schemas
```

Each catalog entry includes the schema's RFC 8785 canonical SHA-256 digest.
Package, capability, and contract versions evolve independently; the
[compatibility policy](docs/reference/contracts.md#compatibility-and-version-axes)
defines when each one changes.

## The authority boundary

ZEO Creator proposes destination-specific operations; each binds an explicit
channel and destination, selected artifacts, content document, optional
accessibility text and extension, and schedule. It never executes them. A
runner resolves connection references, checks policy, obtains approval, mints
bounded effect authority, executes through an authorized connector, and retains
a secret-safe receipt.

## Reference workflow

Credential-free examples model two isolated publications and a caller-defined
portfolio containing articles, short video, image carousels, and newsletter
issues. The fixture proves research, planning, briefs, artifact bundles, reviews,
multi-channel proposals, and separate performance assessments without encoding
any private production taxonomy.

```console
uv run python examples/complete_content_portfolio.py
```

Explore [`reference/examples`](reference/examples), follow the
[portfolio tutorial](docs/tutorials/content-portfolio.md), or read the
[production adapter guide](docs/guides/production-adapters.md).

## Development

```console
make setup       # install the locked environment
make verify      # lint, strict typing, tests, references, docs, package checks
make examples    # run every credential-free example
make docs-serve  # serve documentation locally
make doctor      # verify Python, Zeocore, manifests, and projections
```

The repository enforces architectural import boundaries and tests installed
wheel behavior. See [architecture](docs/concepts/architecture.md),
[canonical digests](docs/concepts/canonical-digests.md), and
[contributing](docs/contributing.md).

## Status

ZEO Creator is a pre-release contract and reference package. PyPI publication
and live provider effects require separate operator approval and have not occurred.

MIT licensed.
