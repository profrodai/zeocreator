"""Ducktyper render bindings and digest-bound delivery review contracts."""

from enum import StrEnum

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact, UtcDatetime
from zeo_creator.contracts.distribution import ChannelDestination, PublicationPayload


class RenderedArtifact(DurableArtifact):
    artifact_ref: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    brief_id: str = Field(min_length=1)
    content_revision: int = Field(ge=1)
    brief_content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    media_type: str = Field(min_length=1)
    storage_ref: str = Field(min_length=1)
    byte_length: int = Field(gt=0)
    extracted_text: str = ""


class RenderAttestation(CreatorModel):
    check_id: str = Field(min_length=1)
    check_version: str = Field(min_length=1)
    result: bool
    evidence_ref: str = Field(min_length=1)
    tool_identity: str = Field(min_length=1)
    observed_value: str = Field(min_length=1)
    expected_constraint: str = Field(min_length=1)


class ArtifactDigestProof(CreatorModel):
    algorithm: str = Field(pattern=r"^sha256$")
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    byte_length: int = Field(gt=0)
    storage_ref: str = Field(min_length=1)
    retrieved_at: UtcDatetime
    evidence_ref: str = Field(min_length=1)
    tool_identity: str = Field(min_length=1)
    tool_version: str = Field(min_length=1)


class RenderManifest(DurableArtifact):
    manifest_id: str = Field(min_length=1)
    brief_id: str = Field(min_length=1)
    content_revision: int = Field(ge=1)
    brief_content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifact_ref: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    brand_profile_ref: str = Field(min_length=1)
    rendered_claim_ids: tuple[str, ...] = ()
    artifact_digest_proof: ArtifactDigestProof
    attestations: tuple[RenderAttestation, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_attestations(self) -> RenderManifest:
        ids = [item.check_id for item in self.attestations]
        if len(ids) != len(set(ids)):
            raise ValueError("render attestation check identifiers must be unique")
        return self


class FindingSeverity(StrEnum):
    BLOCKING = "blocking"
    ADVISORY = "advisory"


class DeliveryFinding(CreatorModel):
    code: str = Field(pattern=r"^ZEO_CREATOR_[A-Z0-9_]+$")
    severity: FindingSeverity
    category: str = Field(min_length=1)
    message: str = Field(min_length=1)


class DeliveryReviewBundle(DurableArtifact):
    review_id: str = Field(min_length=1)
    brief_id: str = Field(min_length=1)
    artifact_ref: str = Field(min_length=1)
    manifest_id: str = Field(min_length=1)
    identity_match: bool
    required_element_coverage: bool
    source_claim_traceability: bool
    brand_constraints_pass: bool
    technical_delivery_pass: bool
    findings: tuple[DeliveryFinding, ...] = ()
    proposed_payload: PublicationPayload
    proposed_destinations: tuple[ChannelDestination, ...]
    approval_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ready_for_approval: bool

    @property
    def blocking_findings(self) -> tuple[DeliveryFinding, ...]:
        return tuple(item for item in self.findings if item.severity == FindingSeverity.BLOCKING)
