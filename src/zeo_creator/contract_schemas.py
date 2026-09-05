"""Discovery and export of JSON Schemas bundled with the distribution."""

import json
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, cast

from zeo_creator.contracts.common import canonical_digest


@dataclass(frozen=True)
class ContractSchema:
    """One stable public contract schema."""

    name: str
    version: str
    filename: str
    schema_digest: str


def _schema_root() -> Traversable:
    return files("zeo_creator").joinpath("schemas")


def list_contract_schemas() -> tuple[ContractSchema, ...]:
    """Return the stable schema catalog shipped in the installed package."""
    payload = json.loads(_schema_root().joinpath("catalog.json").read_text(encoding="utf-8"))
    return tuple(ContractSchema(**item) for item in payload["contracts"])


def read_contract_schema(name: str, version: str) -> dict[str, Any]:
    """Read one schema by stable contract name and major version."""
    match = next(
        (item for item in list_contract_schemas() if item.name == name and item.version == version),
        None,
    )
    if match is None:
        raise KeyError(f"unknown contract schema: {name}@{version}")
    schema = cast(
        dict[str, Any],
        json.loads(_schema_root().joinpath(match.filename).read_text(encoding="utf-8")),
    )
    if canonical_digest(schema) != match.schema_digest:
        raise RuntimeError(f"packaged schema digest mismatch: {name}@{version}")
    return schema


def export_contract_schemas(output: Path) -> tuple[Path, ...]:
    """Copy every packaged schema and its catalog to ``output``."""
    output.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for resource in _schema_root().iterdir():
        if resource.name.endswith(".json"):
            target = output / resource.name
            target.write_text(resource.read_text(encoding="utf-8"), encoding="utf-8")
            written.append(target)
    return tuple(sorted(written))
