"""Add the exact v4 result union and portable receipt cases without changing old schemas."""

import json

from scripts.export_reference_artifacts_v5 import PACKAGED, ROOT, write
from scripts.export_reference_artifacts_v5 import main as previous_export
from zeo_creator.contracts.common import canonical_digest
from zeo_creator.reference.email_receipt_conformance import build_cases, result_schema


def main() -> None:
    previous_export()
    schema = result_schema()
    filename = "email-remote-result.v4.schema.json"
    for root in (ROOT / "reference/schemas", PACKAGED / "schemas"):
        write(root / filename, schema)
    path = PACKAGED / "schemas/catalog.json"
    catalog = json.loads(path.read_text())
    catalog["contracts"].append(
        dict(
            name="email-remote-result",
            version="4",
            filename=filename,
            schema_digest=canonical_digest(schema),
        )
    )
    write(path, catalog)
    corpus = build_cases()
    for root in (ROOT / "reference", PACKAGED / "reference_artifacts"):
        write(root / "email-receipt-conformance-v2.json", corpus)


if __name__ == "__main__":
    main()
