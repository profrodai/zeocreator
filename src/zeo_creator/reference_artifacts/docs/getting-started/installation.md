# Installation

For the **0.5.4 source candidate with Zeocore 0.11.0**, follow the
[Runtime host integration guide](../guides/runtime-host.md). That candidate
is not yet on PyPI. The instructions below describe released 0.5.3.

Install `zeocreator==0.5.3` from PyPI with Python 3.14 or newer. Zeocore 0.9.0 is
installed automatically; no provider extras, credentials or accounts are needed.

## Fresh environment

=== "uv"

    ```console
    uv venv --python 3.14 .venv
    uv pip install --python .venv/bin/python "zeocreator==0.5.3"
    .venv/bin/zeo-creator doctor --json
    .venv/bin/python -m zeo_creator.examples.create_content_brief
    .venv/bin/python -m zeo_creator.examples.email_marketing
    ```

=== "pip"

    ```console
    python3.14 -m venv .venv
    .venv/bin/python -m pip install "zeocreator==0.5.3"
    .venv/bin/zeo-creator doctor --json
    .venv/bin/python -m zeo_creator.examples.create_content_brief
    .venv/bin/python -m zeo_creator.examples.email_marketing
    ```

On Windows, use `.venv\Scripts\python.exe` and `.venv\Scripts\zeo-creator.exe`
in place of `.venv/bin/python` and `.venv/bin/zeo-creator`. In an existing uv
project, use `uv add "zeocreator==0.5.3"`, then prefix commands with `uv run`.

The PyPI distribution is **zeocreator**; the Python import is **zeo_creator**;
the executable is **zeo-creator**. The earlier Git-only distribution was named
`zeo-creator`. These are different installer project names despite sharing an
import path: use a fresh environment, or uninstall `zeo-creator` with your installer
before installing `zeocreator`. Do not install both distributions together.

## Verify and explore

After activating your environment (or using the explicit executable paths above):

```console
zeo-creator --version
zeo-creator doctor --json
zeo-creator capabilities
python -m zeo_creator.examples.complete_content_portfolio
python -m zeo_creator.reference.email_receipt_conformance
zeo-creator contracts export --output=./schemas
```

Version reports `zeo-creator 0.5.3`. Doctor reports `ok: true`, Python 3.14+,
Zeocore 0.9.0, 29 manifests and 29 projections. The receipt command verifies 135
portable cases; it does not authenticate provider receipts. The email example
prints eight programs and 104 simulated proposals with partial assessments.
All seven public examples are packaged under `zeo_creator.examples` and work
outside the source checkout. Their in-memory hosts never send an email.

## Work from the release source

```console
git clone --branch v0.5.3 https://github.com/profrodai/zeocreator.git
cd zeocreator
uv sync --frozen
make doctor
make examples
make verify
```

The tag fixes the release source; `uv.lock` fixes its development environment.
Installed applications should retain their own lockfile as well.

!!! note "Why exactly Zeocore 0.9.0?"

    Creator consumes a released contract boundary. It does not claim parity
    with an unreleased provider branch. Read the
    [architecture decision](../adr/0001-zeocore-version-and-runtime-boundary.md).
    Live HubSpot/Kit lowering still needs independent host integration and qualification.

Next, [invoke your first capability](first-capability.md) or follow the
[email marketing guide](../guides/email-marketing.md).
