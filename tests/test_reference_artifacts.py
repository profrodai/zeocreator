"""Committed schemas and dogfood samples remain aligned with typed contracts."""

import json
from pathlib import Path

from tests.fixtures.dogfood import build_dogfood_snapshot
from zeo_creator.contracts.ducktyper import DucktyperBrief
from zeo_creator.contracts.editorial import DailyEditorialPlan
from zeo_creator.contracts.performance import DailyPerformanceAssessment

REFERENCE = Path("reference")


def _load(relative: str):
    return json.loads((REFERENCE / relative).read_text())


def test_reference_dogfood_artifacts_validate_and_have_exact_counts() -> None:
    plan = DailyEditorialPlan.model_validate(_load("dogfood/daily-editorial-plan.json"))
    briefs = [
        DucktyperBrief.model_validate(item) for item in _load("dogfood/ducktyper-briefs.json")
    ]
    assessments = [
        DailyPerformanceAssessment.model_validate(item)
        for item in _load("dogfood/performance-assessments.json")
    ]

    assert len(plan.assignments) == 6
    assert len(briefs) == 6
    assert len(assessments) == 2
    assert {item.publication_id for item in assessments} == {"profrod.ai", "zeroemployee.org"}


def test_reference_briefs_match_the_deterministic_fixture() -> None:
    expected = [item.model_dump(mode="json") for item in build_dogfood_snapshot().briefs]
    assert _load("dogfood/ducktyper-briefs.json") == expected


def test_reference_contract_schemas_are_present() -> None:
    schemas = tuple((REFERENCE / "schemas").glob("*.schema.json"))
    assert len(schemas) == 25
    assert all(_load(str(path.relative_to(REFERENCE)))["type"] == "object" for path in schemas)
