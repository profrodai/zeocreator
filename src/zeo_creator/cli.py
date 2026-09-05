"""Diagnostics and discovery only; workflow orchestration belongs to a runner."""

import importlib.metadata
import json
import sys
from enum import StrEnum
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from zeo_creator import __version__
from zeo_creator.contract_schemas import (
    export_contract_schemas,
    list_contract_schemas,
    read_contract_schema,
)
from zeo_creator.registry import capability_manifests, openai_tool_projections

app = typer.Typer(
    name="zeo-creator",
    help="Inspect ZEO Creator contracts and local compatibility.",
    no_args_is_help=True,
)
console = Console()
contracts_app = typer.Typer(help="Discover and export packaged public contract schemas.")
app.add_typer(contracts_app, name="contracts")


class ProjectionFormat(StrEnum):
    MANIFEST = "manifest"
    OPENAI = "openai"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"zeo-creator {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed version.",
    ),
) -> None:
    del version


@app.command()
def capabilities(
    projection: ProjectionFormat = typer.Option(
        ProjectionFormat.MANIFEST,
        "--projection",
        help="Render canonical manifests or OpenAI-compatible function tools.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """List the six stable business capabilities."""
    if projection == ProjectionFormat.OPENAI:
        rows = [item.model_dump(mode="json") for item in openai_tool_projections()]
        typer.echo(json.dumps(rows, indent=2))
        return
    manifests = capability_manifests()
    if json_output:
        typer.echo(json.dumps([item.model_dump(mode="json") for item in manifests], indent=2))
        return
    table = Table(title="ZEO Creator capabilities")
    table.add_column("Capability ID")
    table.add_column("Effects")
    table.add_column("Required services")
    for manifest in manifests:
        table.add_row(
            manifest.id.canonical(),
            ", ".join(sorted(item.value for item in manifest.effects.kinds)),
            ", ".join(sorted(manifest.requirements.services)) or "none",
        )
    console.print(table)


@contracts_app.command("list")
def contracts_list(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """List versioned contracts included in this installation."""
    entries = list_contract_schemas()
    rows = [
        {
            "name": item.name,
            "version": item.version,
            "filename": item.filename,
            "schema_digest": item.schema_digest,
        }
        for item in entries
    ]
    if json_output:
        typer.echo(json.dumps(rows, indent=2))
        return
    table = Table(title="ZEO Creator contracts")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Schema")
    table.add_column("Digest")
    for item in entries:
        table.add_row(item.name, item.version, item.filename, item.schema_digest)
    console.print(table)


@contracts_app.command("export")
def contracts_export(
    output: Path = typer.Option(..., "--output", help="Destination directory."),
) -> None:
    """Export packaged schemas without importing source checkout files."""
    written = export_contract_schemas(output)
    typer.echo(json.dumps({"output": str(output), "files": len(written)}, indent=2))


@app.command("contract-schema")
def contract_schema(
    name: str = typer.Option(..., "--name", help="Stable contract name."),
    version: str = typer.Option(..., "--version", help="Contract major version."),
) -> None:
    """Print one packaged JSON Schema."""
    try:
        schema = read_contract_schema(name, version)
    except KeyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc
    typer.echo(json.dumps(schema, indent=2))


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json")) -> None:
    """Check the declared Python, Zeocore, manifest, and projection boundary."""
    zeocore_version = importlib.metadata.version("zeocore")
    checks = {
        "python_3_14_or_newer": sys.version_info >= (3, 14),
        "zeocore_0_6_0": zeocore_version == "0.6.0",
        "six_manifests": len(capability_manifests()) == 6,
        "six_openai_projections": len(openai_tool_projections()) == 6,
    }
    payload = {
        "ok": all(checks.values()),
        "python": ".".join(str(item) for item in sys.version_info[:3]),
        "zeocore": zeocore_version,
        "checks": checks,
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
    else:
        for name, passed in checks.items():
            console.print(f"{'ready' if passed else 'failed':>6}  {name}")
    if not payload["ok"]:
        raise typer.Exit(1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
