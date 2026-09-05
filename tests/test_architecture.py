"""Dependency and secret-boundary enforcement."""

import ast
from pathlib import Path

SOURCE_ROOT = Path("src/zeo_creator")
DOMAIN_ROOTS = tuple(SOURCE_ROOT / name for name in ("capabilities", "contracts", "services"))
FORBIDDEN_IMPORT_PREFIXES = (
    "tweepy",
    "linkedin",
    "googleapiclient",
    "google.auth",
    "github",
    "requests_oauthlib",
    "zeo_runtime",
    "zeoconnect",
)


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_domain_layers_do_not_import_providers_or_runtime_products() -> None:
    violations: list[str] = []
    for root in DOMAIN_ROOTS:
        for path in root.rglob("*.py"):
            for imported in _imports(path):
                if imported.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    violations.append(f"{path}: {imported}")
    assert violations == []


def test_creator_source_has_no_ambient_credentials_or_provider_write_endpoints() -> None:
    forbidden = ("os.environ", "getenv(", "api.twitter.com", "api.linkedin.com", "access_token")
    violations: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        text = path.read_text().lower()
        for needle in forbidden:
            if needle.lower() in text:
                violations.append(f"{path}: {needle}")
    assert violations == []
