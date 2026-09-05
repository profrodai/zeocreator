"""Load and validate the complete neutral two-publication reference portfolio."""

import json
from collections import Counter
from pathlib import Path

from pydantic import TypeAdapter

from zeo_creator.contracts.delivery import ArtifactManifest, DeliveryReviewBundle
from zeo_creator.contracts.distribution import ProposedPublicationOperation
from zeo_creator.contracts.editorial import ContentPortfolioPlan
from zeo_creator.contracts.performance import DailyPerformanceAssessment
from zeo_creator.contracts.production import ContentBrief

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference" / "examples"


def _load(name: str) -> object:
    return json.loads((REFERENCE / name).read_text())


def main() -> None:
    plan = ContentPortfolioPlan.model_validate(_load("content-portfolio-plan.json"))
    briefs = TypeAdapter(tuple[ContentBrief, ...]).validate_python(_load("content-briefs.json"))
    manifests = TypeAdapter(tuple[ArtifactManifest, ...]).validate_python(
        _load("artifact-manifests.json")
    )
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
        "artifact_manifests": len(manifests),
        "approved_deliveries": sum(item.ready_for_approval for item in reviews),
        "publication_proposals": len(proposals),
        "executed_operations": 0,
        "assessments": [item.publication_id for item in assessments],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
