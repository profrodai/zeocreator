"""Shared immutable identity, timestamp, revision, and digest contracts."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, Self

import rfc8785
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"
FORBIDDEN_SECRET_TERMS = frozenset(
    {"api_key", "authorization", "credential", "password", "secret", "token"}
)


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a UTC offset")
    return value.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_utc_datetime)]


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python", exclude={"content_digest"})
    if isinstance(value, datetime):
        return _utc_datetime(value).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _canonical_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(child) for child in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    """Serialize contract content with RFC 8785/JCS and UTC timestamps."""
    return rfc8785.dumps(_canonical_value(value))


def canonical_digest(value: Any) -> str:
    """Return an RFC 8785/JCS SHA-256 digest for contract content."""
    return f"sha256:{hashlib.sha256(canonical_bytes(value)).hexdigest()}"


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

    @model_validator(mode="after")
    def normalize_direct_timestamps(self) -> Self:
        """Reject naïve datetimes and persist direct timestamp fields as UTC."""
        for field_name in type(self).model_fields:
            value = getattr(self, field_name)
            if isinstance(value, datetime):
                object.__setattr__(self, field_name, _utc_datetime(value))
        return self


class DurableArtifact(CreatorModel):
    """Fields common to durable, revisioned creator-domain artifacts."""

    schema_version: str = SCHEMA_VERSION
    created_at: UtcDatetime
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
