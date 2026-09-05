"""Assert that built distributions expose only the intentional package surface."""

import tarfile
import zipfile
from pathlib import Path


def main() -> None:
    wheel = next(Path("dist").glob("*.whl"))
    sdist = next(Path("dist").glob("*.tar.gz"))

    with zipfile.ZipFile(wheel) as archive:
        wheel_names = set(archive.namelist())
    assert "zeo_creator/py.typed" in wheel_names
    assert not any("tests/" in name or ".claude/" in name for name in wheel_names)

    with tarfile.open(sdist) as archive:
        names = [Path(name).parts[1:] for name in archive.getnames() if len(Path(name).parts) > 1]
    forbidden = {
        ".claude",
        ".github",
        "tests",
        "examples",
        "docs",
        "reference",
        "uv.lock",
        "Makefile",
        "AGENTS.md",
        "CLAUDE.md",
    }
    assert not any(parts and parts[0] in forbidden for parts in names)

    print(f"verified {wheel.name} and {sdist.name}")


if __name__ == "__main__":
    main()
