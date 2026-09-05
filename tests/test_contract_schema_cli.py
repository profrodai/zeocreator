"""Installed consumers can discover and export versioned contract schemas."""

import json
from pathlib import Path

from typer.testing import CliRunner

from zeo_creator.cli import app

runner = CliRunner()


def test_contract_catalog_and_single_schema() -> None:
    listing = runner.invoke(app, ["contracts", "list", "--json"])
    assert listing.exit_code == 0
    rows = json.loads(listing.stdout)
    assert {item["name"] for item in rows} >= {"content-brief", "artifact-manifest"}

    schema = runner.invoke(app, ["contract-schema", "--name", "content-brief", "--version", "1"])
    assert schema.exit_code == 0
    assert json.loads(schema.stdout)["title"] == "ContentBrief"


def test_contract_export(tmp_path: Path) -> None:
    result = runner.invoke(app, ["contracts", "export", f"--output={tmp_path}"])
    assert result.exit_code == 0
    assert (tmp_path / "catalog.json").is_file()
    assert (tmp_path / "content-brief.v1.schema.json").is_file()
