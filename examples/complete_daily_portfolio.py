"""Load and validate the complete two-property dogfood portfolio."""

import json
from collections import Counter
from pathlib import Path

from pydantic import TypeAdapter

from zeo_creator.contracts.delivery import DeliveryReviewBundle
from zeo_creator.contracts.distribution import ProposedPublicationOperation
from zeo_creator.contracts.ducktyper import DucktyperBrief
from zeo_creator.contracts.editorial import DailyEditorialPlan
from zeo_creator.contracts.performance import DailyPerformanceAssessment

ROOT = Path(__file__).resolve().parents[1]
DOGFOOD = ROOT / "reference" / "dogfood"


def _load(name: str) -> object:
    return json.loads((DOGFOOD / name).read_text())


def main() -> None:
    plan = DailyEditorialPlan.model_validate(_load("daily-editorial-plan.json"))
    briefs = TypeAdapter(tuple[DucktyperBrief, ...]).validate_python(_load("ducktyper-briefs.json"))
    reviews = TypeAdapter(tuple[DeliveryReviewBundle, ...]).validate_python(
        _load("delivery-reviews.json")
    )
    proposals = TypeAdapter(tuple[ProposedPublicationOperation, ...]).validate_python(
        _load("publication-proposals.json")
    )
    assessments = TypeAdapter(tuple[DailyPerformanceAssessment, ...]).validate_python(
        _load("performance-assessments.json")
    )

    summary = {
        "assignments": len(plan.assignments),
        "briefs_by_publication": Counter(item.publication_id for item in briefs),
        "approved_renders": sum(item.ready_for_approval for item in reviews),
        "publication_proposals": len(proposals),
        "executed_operations": 0,
        "assessments": [item.publication_id for item in assessments],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
