"""Export deterministic schemas and credential-free dogfood reference artifacts."""

import json
from pathlib import Path
from typing import Any

from tests.fixtures.dogfood import (
    build_dogfood_snapshot,
    evidence_fixture,
    recent_history,
)
from zeo_creator.contracts.delivery import DeliveryReviewBundle, RenderedArtifact, RenderManifest
from zeo_creator.contracts.distribution import ProposedPublicationOperation, PublicationReceipt
from zeo_creator.contracts.ducktyper import DucktyperBrief
from zeo_creator.contracts.editorial import DailyEditorialPlan, EditorialAssignment
from zeo_creator.contracts.evidence import EvidenceItem, ResearchSynthesis
from zeo_creator.contracts.performance import DailyPerformanceAssessment, MetricObservation
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.registry import CAPABILITIES

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def export_schemas() -> None:
    contract_models = (
        PublicationProfile,
        EvidenceItem,
        ResearchSynthesis,
        EditorialAssignment,
        DailyEditorialPlan,
        DucktyperBrief,
        RenderedArtifact,
        RenderManifest,
        DeliveryReviewBundle,
        ProposedPublicationOperation,
        PublicationReceipt,
        MetricObservation,
        DailyPerformanceAssessment,
    )
    for model in contract_models:
        _write(REFERENCE / "schemas" / f"{model.__name__}.schema.json", model.model_json_schema())
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


def export_dogfood() -> None:
    snapshot = build_dogfood_snapshot()
    evidence_by_query, _ = evidence_fixture()
    values = {
        "publication-profiles.json": snapshot.profiles,
        "evidence.json": tuple(item for rows in evidence_by_query.values() for item in rows),
        "recent-content-history.json": recent_history(),
        "daily-editorial-plan.json": snapshot.plan,
        "ducktyper-briefs.json": snapshot.briefs,
        "rendered-artifacts.json": snapshot.artifacts,
        "render-manifests.json": snapshot.manifests,
        "delivery-reviews.json": snapshot.reviews,
        "publication-proposals.json": snapshot.operations,
        "performance-assessments.json": snapshot.assessments,
    }
    for filename, value in values.items():
        if isinstance(value, tuple):
            payload = [item.model_dump(mode="json") for item in value]
        else:
            payload = value.model_dump(mode="json")
        _write(REFERENCE / "dogfood" / filename, payload)


if __name__ == "__main__":
    export_schemas()
    export_dogfood()
