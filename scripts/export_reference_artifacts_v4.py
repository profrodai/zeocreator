"""Export explicit email v3 while retaining the immutable v1 and v2 schemas."""

import json
from pathlib import Path

from pydantic import BaseModel

from scripts.export_reference_artifacts import export_examples, export_schemas
from zeo_creator.contracts import email_marketing as email
from zeo_creator.contracts.common import canonical_bytes, canonical_digest
from zeo_creator.reference.email_program_suite import effect_family, publication_suite
from zeo_creator.reference.email_workflow import three_publications
from zeo_creator.registry import CAPABILITIES

ROOT = Path(__file__).resolve().parents[1]
PACKAGED = ROOT / "src/zeo_creator"
MODELS: tuple[tuple[str, type[BaseModel]], ...] = (
    ("email-measurement-population", email.EmailMeasurementPopulation),
    ("email-campaign-release", email.EmailCampaignRelease),
    ("email-execution-context", email.EmailExecutionContext),
    ("email-lowering-evidence", email.EmailLoweringEvidence),
    ("email-remote-receipt", email.EmailRemoteReceipt),
    ("email-migration-plan", email.EmailMigrationPlan),
    ("email-migration-step", email.EmailMigrationStep),
    ("email-stopping-condition-finding", email.EmailStoppingConditionFinding),
    ("audience-intent", email.AudienceIntent),
    ("audience-snapshot-summary", email.AudienceSnapshotSummary),
    ("email-artifact-ref", email.EmailArtifactRef),
    ("email-campaign-plan", email.EmailCampaignPlan),
    ("email-sequence-plan", email.EmailSequencePlan),
    ("email-sequence-step-plan", email.EmailSequenceStepPlan),
    ("email-message-plan", email.EmailMessagePlan),
    ("email-message-draft", email.EmailMessageDraft),
    ("email-editorial-review", email.EmailEditorialReview),
    ("email-review-evidence", email.EmailReviewEvidence),
    ("email-proof-receipt", email.EmailProofReceipt),
    ("email-delivery-material", email.EmailDeliveryMaterial),
    ("email-delivery-package", email.EmailDeliveryPackage),
    ("email-operation-intent", email.EmailOperationIntent),
    ("proposed-email-operation", email.ProposedEmailOperation),
    ("email-metric-observation", email.EmailMetricObservation),
    ("email-program-assessment", email.EmailProgramAssessment),
)


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    export_schemas()
    export_examples()
    catalog_path = PACKAGED / "schemas/catalog.json"
    catalog = json.loads(catalog_path.read_text())
    for version in ("1", "2"):
        frozen = json.loads((ROOT / f"reference/email-v{version}-frozen.json").read_text())
        for path, schema in frozen["schemas"].items():
            write(ROOT / path, schema)
            if path.startswith("src/zeo_creator/schemas/"):
                filename = Path(path).name
                catalog["contracts"].append(
                    dict(
                        name=filename.split(f".v{version}.")[0],
                        version=version,
                        filename=filename,
                        schema_digest=canonical_digest(schema),
                    )
                )
    for name, model in MODELS:
        schema = model.model_json_schema()
        filename = f"{name}.v3.schema.json"
        for root in (ROOT / "reference/schemas", PACKAGED / "schemas"):
            write(root / filename, schema)
        catalog["contracts"].append(
            dict(name=name, version="3", filename=filename, schema_digest=canonical_digest(schema))
        )
    write(catalog_path, catalog)
    runs = three_publications()
    values = [run.model_dump(mode="json") for run in runs]
    write(ROOT / "reference/examples/email-marketing.json", values)
    write(PACKAGED / "reference_artifacts/email-marketing.json", values)
    programs = publication_suite()
    suite = [row.model_dump(mode="json") for row in programs]
    families = [
        effect_family(
            next(row for row in programs if row.publication.publication_id == pub)
        ).model_dump(mode="json")
        for pub in ("publication-a", "publication-b", "publication-c")
    ]
    for root in (ROOT / "reference/examples", PACKAGED / "reference_artifacts"):
        write(root / "email-program-suite-v3.json", suite)
        write(root / "email-effect-family-v3.json", families)
    vectors = []
    for run in runs:
        for name, artifact in (
            ("campaign", run.campaign),
            ("sequence", run.sequence),
            ("draft", run.drafts[0]),
            ("package", run.packages[1]),
            ("proposal", run.proposals[1]),
            ("assessment", run.assessment),
        ):
            vectors.append(
                dict(
                    name=f"{run.publication.publication_id}-{name}",
                    canonical_json=canonical_bytes(artifact).decode(),
                    sha256=canonical_digest(artifact),
                )
            )
    write(ROOT / "reference/email-digest-vectors.json", vectors)
    write(PACKAGED / "reference_artifacts/email-digest-vectors.json", vectors)
    for bound in CAPABILITIES:
        if "email" in bound.definition.tags:
            name = bound.definition.projection_name
            for kind, schema in (
                ("request", bound.request_model.model_json_schema()),
                ("response", bound.definition.response_schema),
            ):
                write(PACKAGED / f"reference_artifacts/{name}.{kind}.schema.json", schema)
    # Documentation ships in the wheel as inspectable resources; consumers need no checkout.
    for source in (ROOT / "docs").rglob("*.md"):
        target = PACKAGED / "reference_artifacts/docs" / source.relative_to(ROOT / "docs")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text())


if __name__ == "__main__":
    main()
