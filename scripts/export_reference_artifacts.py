"""Export deterministic schemas and credential-free neutral reference artifacts."""

import json
from pathlib import Path
from typing import Any

from tests.fixtures.reference import (
    build_reference_snapshot,
    evidence_fixture,
    recent_history,
)
from zeo_creator.contracts.delivery import ArtifactManifest, DeliveryReviewBundle
from zeo_creator.contracts.distribution import ProposedPublicationOperation, PublicationReceipt
from zeo_creator.contracts.editorial import ContentPortfolioPlan, EditorialAssignment
from zeo_creator.contracts.evidence import EvidenceItem, ResearchSynthesis
from zeo_creator.contracts.performance import DailyPerformanceAssessment, MetricObservation
from zeo_creator.contracts.production import ContentBrief
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.registry import CAPABILITIES

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"
PACKAGED_SCHEMAS = ROOT / "src" / "zeo_creator" / "schemas"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def export_schemas() -> None:
    contract_models = (
        ("publication-profile", "1", PublicationProfile),
        ("evidence-item", "1", EvidenceItem),
        ("research-synthesis", "1", ResearchSynthesis),
        ("editorial-assignment", "1", EditorialAssignment),
        ("content-portfolio-plan", "1", ContentPortfolioPlan),
        ("content-brief", "1", ContentBrief),
        ("artifact-manifest", "1", ArtifactManifest),
        ("delivery-review-bundle", "1", DeliveryReviewBundle),
        ("proposed-publication-operation", "1", ProposedPublicationOperation),
        ("publication-receipt", "1", PublicationReceipt),
        ("metric-observation", "1", MetricObservation),
        ("daily-performance-assessment", "1", DailyPerformanceAssessment),
    )
    catalog = []
    for name, version, model in contract_models:
        filename = f"{name}.v{version}.schema.json"
        schema = model.model_json_schema()
        _write(REFERENCE / "schemas" / filename, schema)
        _write(PACKAGED_SCHEMAS / filename, schema)
        catalog.append({"name": name, "version": version, "filename": filename})
    _write(PACKAGED_SCHEMAS / "catalog.json", {"contracts": catalog})
    for capability in CAPABILITIES:
        name = capability.definition.projection_name
        _write(
            REFERENCE / "schemas" / f"{name}.request.schema.json",
            capability.request_model.model_json_schema(),
        )
        _write(
            REFERENCE / "schemas" / f"{name}.response.schema.json",
            capability.definition.response_schema,
        )


def export_examples() -> None:
    snapshot = build_reference_snapshot()
    evidence_by_query, _ = evidence_fixture()
    values = {
        "publication-profiles.json": snapshot.profiles,
        "evidence.json": tuple(item for rows in evidence_by_query.values() for item in rows),
        "recent-content-history.json": recent_history(),
        "content-portfolio-plan.json": snapshot.plan,
        "content-briefs.json": snapshot.briefs,
        "artifact-manifests.json": snapshot.manifests,
        "delivery-reviews.json": snapshot.reviews,
        "publication-proposals.json": snapshot.operations,
        "performance-assessments.json": snapshot.assessments,
    }
    for filename, value in values.items():
        if isinstance(value, tuple):
            payload = [item.model_dump(mode="json") for item in value]
        else:
            payload = value.model_dump(mode="json")
        _write(REFERENCE / "examples" / filename, payload)


if __name__ == "__main__":
    export_schemas()
    export_examples()
