"""Committed schemas and neutral examples remain aligned with typed contracts."""

import json
from pathlib import Path

from tests.fixtures.reference import build_reference_snapshot
from zeo_creator.contracts.editorial import ContentPortfolioPlan
from zeo_creator.contracts.performance import DailyPerformanceAssessment
from zeo_creator.contracts.production import ContentBrief

REFERENCE = Path("reference")


def _load(relative: str):
    return json.loads((REFERENCE / relative).read_text())


def test_reference_examples_validate() -> None:
    plan = ContentPortfolioPlan.model_validate(_load("examples/content-portfolio-plan.json"))
    briefs = [ContentBrief.model_validate(item) for item in _load("examples/content-briefs.json")]
    assessments = [
        DailyPerformanceAssessment.model_validate(item)
        for item in _load("examples/performance-assessments.json")
    ]
    assert len(plan.assignments) == len(briefs) == 8
    assert {item.publication_id for item in assessments} == {
        "publication-a.example",
        "publication-b.example",
    }


def test_reference_briefs_match_deterministic_fixture() -> None:
    expected = [item.model_dump(mode="json") for item in build_reference_snapshot().briefs]
    assert _load("examples/content-briefs.json") == expected


def test_reference_contract_schemas_are_objects() -> None:
    schemas = tuple((REFERENCE / "schemas").glob("*.schema.json"))
    assert len(schemas) >= 20
    assert all(_load(str(path.relative_to(REFERENCE)))["type"] == "object" for path in schemas)
