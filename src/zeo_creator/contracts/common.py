"""Shared immutable identity, timestamp, revision, and digest contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"
FORBIDDEN_SECRET_TERMS = frozenset(
    {"api_key", "authorization", "credential", "password", "secret", "token"}
)


def canonical_digest(value: Any) -> str:
    """Return a deterministic SHA-256 digest for JSON-safe contract content."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude={"content_digest"})
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"sha256:{hashlib.sha256(payload.encode()).hexdigest()}"


def stable_id(prefix: str, *parts: str) -> str:
    """Derive a readable stable identifier from immutable input identity."""
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:20]
    return f"{prefix}_{digest}"


def assert_secret_safe(value: Any, path: str = "$") -> None:
    """Reject credential-shaped keys recursively without inspecting secret stores."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if any(term in lowered for term in FORBIDDEN_SECRET_TERMS):
                raise ValueError(f"credential-shaped field is forbidden at {path}.{key}")
            assert_secret_safe(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple, set, frozenset)):
        for index, child in enumerate(value):
            assert_secret_safe(child, f"{path}[{index}]")


class CreatorModel(BaseModel):
    """Strict immutable base for public ZEO Creator contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class DurableArtifact(CreatorModel):
    """Fields common to durable, revisioned creator-domain artifacts."""

    schema_version: str = SCHEMA_VERSION
    created_at: datetime
    organization_id: str = Field(min_length=1)
    publication_id: str = Field(min_length=1)
    input_refs: tuple[str, ...] = ()
    revision: int = Field(default=1, ge=1)
    content_digest: str = ""

    @model_validator(mode="after")
    def bind_content_digest(self) -> Self:
        expected = canonical_digest(self)
        if self.content_digest and self.content_digest != expected:
            raise ValueError("content_digest does not match canonical contract content")
        object.__setattr__(self, "content_digest", expected)
        return self


def digest_is_current(value: DurableArtifact) -> bool:
    """Detect stale artifacts, including unsafe model_copy mutations."""
    return value.content_digest == canonical_digest(value)
