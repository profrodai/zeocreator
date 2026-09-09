"""Install the exact indexed release with PyPI-only dependency resolution and test it."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen


def main() -> None:
    index, version, floor = sys.argv[1:]
    if index not in {"pypi", "testpypi"}:
        raise ValueError("unsupported index")
    host = "pypi.org" if index == "pypi" else "test.pypi.org"
    with urlopen(f"https://{host}/pypi/zeocreator/{version}/json", timeout=30) as response:
        data = json.load(response)
    if data["info"]["version"] != version:
        raise ValueError("index returned a different version")
    filename = f"zeocreator-{version}-py3-none-any.whl"
    matches = [item for item in data["urls"] if item["filename"] == filename]
    if len(matches) != 1:
        raise ValueError("index must expose exactly one expected wheel")
    item = matches[0]
    files_host = "files.pythonhosted.org" if index == "pypi" else "test-files.pythonhosted.org"
    if not item["url"].startswith(f"https://{files_host}/") or not item["url"].endswith(
        "/" + filename
    ):
        raise ValueError("unexpected wheel origin or filename")
    wheel = item["url"] + "#sha256=" + item["digests"]["sha256"]
    smoke = Path(__file__).with_name("smoke_installed_v1.py").resolve()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        subprocess.run(["uv", "venv", "--python", floor, str(root / "venv")], check=True)
        python = root / "venv/bin/python"
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--no-cache",
                "--default-index",
                "https://pypi.org/simple/",
                wheel,
            ],
            check=True,
        )
        subprocess.run(
            [str(root / "venv/bin/zeo-creator"), "doctor", "--json"], cwd=root, check=True
        )
        subprocess.run([str(python), str(smoke), version], cwd=root, check=True)


if __name__ == "__main__":
    main()
