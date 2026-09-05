"""Producer-neutral creative brief and extension contracts."""

from enum import StrEnum

from pydantic import Field, JsonValue, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact, assert_secret_safe
from zeo_creator.contracts.editorial import ContentKind
from zeo_creator.contracts.evidence import EvidenceClaim


class ContentDocument(CreatorModel):
    media_type: str = Field(min_length=1)
    content: str = Field(min_length=1)


class AttestationPolicy(StrEnum):
    REQUIRED = "required"
    ADVISORY = "advisory"


class AttestationRequirement(CreatorModel):
    check_id: str = Field(min_length=1)
    policy: AttestationPolicy
    check_version: str | None = None


class ExtensionPayload(CreatorModel):
    namespace: str = Field(min_length=1)
    schema_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    schema_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    payload: JsonValue

    @model_validator(mode="after")
    def extension_is_secret_safe(self) -> ExtensionPayload:
        assert_secret_safe(self.payload)
        return self


class ContentBrief(DurableArtifact):
    brief_id: str = Field(min_length=1)
    assignment_id: str = Field(min_length=1)
    content_kind: ContentKind
    working_title: str = Field(min_length=1)
    slug_hint: str | None = None
    objective: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    desired_audience_action: str = Field(min_length=1)
    core_message: str = Field(min_length=1)
    creative_direction: str = Field(min_length=1)
    source_content: ContentDocument
    participant_refs: tuple[str, ...] = ()
    evidence_claims: tuple[EvidenceClaim, ...] = Field(min_length=1)
    source_refs: tuple[str, ...] = Field(min_length=1)
    brand_profile_ref: str = Field(min_length=1)
    style_ref: str | None = None
    prohibited_claims: tuple[str, ...] = ()
    target_channels: tuple[str, ...] = Field(min_length=1)
    delivery_requirements: tuple[AttestationRequirement, ...] = Field(min_length=1)
    producer_extension: ExtensionPayload | None = None
    content_revision: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def unique_delivery_requirements(self) -> ContentBrief:
        keys = [(item.check_id, item.check_version) for item in self.delivery_requirements]
        if len(keys) != len(set(keys)):
            raise ValueError("delivery attestation requirements must be unique")
        return self
