"""Export current contracts plus runnable wheel examples and their offline resources."""

from scripts.export_reference_artifacts_v5 import PACKAGED, ROOT
from scripts.export_reference_artifacts_v8 import main as previous_export


def main() -> None:
    previous_export()
    target = PACKAGED / "examples"
    target.mkdir(exist_ok=True)
    for source in (ROOT / "examples").glob("*.py"):
        (target / source.name).write_bytes(source.read_bytes())
    for source in (ROOT / "reference/examples").glob("*.json"):
        (PACKAGED / "reference_artifacts" / source.name).write_bytes(source.read_bytes())


if __name__ == "__main__":
    main()
