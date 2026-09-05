# Installation

ZEO Creator currently ships from Git while the Python distribution remains
pre-release.

## Add it to a project

=== "uv"

    ```console
    uv add "zeo-creator @ git+https://github.com/profrodai/zeocreator.git"
    ```

=== "pip"

    ```console
    python -m pip install "git+https://github.com/profrodai/zeocreator.git"
    ```

For a reproducible deployment, pin the reviewed commit you want to deploy. Your
lockfile will retain that immutable revision:

```console
ZEO_CREATOR_REV=replace-with-the-reviewed-full-commit-sha
uv add "zeo-creator @ git+https://github.com/profrodai/zeocreator.git@$ZEO_CREATOR_REV"
```

## Work from source

```console
git clone https://github.com/profrodai/zeocreator.git
cd zeocreator
uv sync --frozen
uv run zeo-creator doctor --json
```

Expected doctor checks:

```json
{
  "ok": true,
  "checks": {
    "python_3_14_or_newer": true,
    "zeocore_0_6_0": true,
    "six_manifests": true,
    "six_openai_projections": true
  }
}
```

!!! note "Why exactly Zeocore 0.6.0?"

    ZEO Creator consumes a released, immutable contract boundary. It does not
    claim parity with an unreleased branch. Read the
    [architecture decision](../adr/0001-zeocore-version-and-runtime-boundary.md).

## Verify the installation

```console
uv run zeo-creator --version
uv run zeo-creator capabilities
```

Next, [invoke your first capability](first-capability.md).
