"""Producer-neutral artifact bundles and digest-bound delivery reviews."""

from enum import StrEnum

from pydantic import Field, JsonValue, model_validator

from zeo_creator.contracts.common import (
    CreatorModel,
    DurableArtifact,
    UtcDatetime,
    assert_secret_safe,
)
from zeo_creator.contracts.distribution import DistributionVariant


class ArtifactDescriptor(CreatorModel):
    artifact_ref: str = Field(min_length=1)
    role: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    byte_length: int = Field(gt=0)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    storage_ref: str = Field(min_length=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def metadata_is_secret_safe(self) -> ArtifactDescriptor:
        assert_secret_safe(self.metadata)
        return self


class ArtifactAttestation(CreatorModel):
    check_id: str = Field(min_length=1)
    check_version: str = Field(min_length=1)
    result: bool
    artifact_refs: tuple[str, ...] = Field(min_length=1)
    evidence_ref: str = Field(min_length=1)
    tool_identity: str = Field(min_length=1)
    observed_value: str = Field(min_length=1)
    expected_constraint: str = Field(min_length=1)


class ArtifactDigestProof(CreatorModel):
    artifact_ref: str = Field(min_length=1)
    algorithm: str = Field(pattern=r"^sha256$")
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    byte_length: int = Field(gt=0)
    storage_ref: str = Field(min_length=1)
    retrieved_at: UtcDatetime
    evidence_ref: str = Field(min_length=1)
    tool_identity: str = Field(min_length=1)
    tool_version: str = Field(min_length=1)


class ArtifactManifest(DurableArtifact):
    manifest_id: str = Field(min_length=1)
    brief_id: str = Field(min_length=1)
    content_revision: int = Field(ge=1)
    brief_content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    producer_ref: str = Field(min_length=1)
    producer_version: str = Field(min_length=1)
    brand_profile_ref: str = Field(min_length=1)
    artifacts: tuple[ArtifactDescriptor, ...] = Field(min_length=1)
    digest_proofs: tuple[ArtifactDigestProof, ...] = Field(min_length=1)
    attestations: tuple[ArtifactAttestation, ...] = Field(min_length=1)
    produced_claim_ids: tuple[str, ...] = ()
    extracted_text: str = ""

    @model_validator(mode="after")
    def unique_and_bound_components(self) -> ArtifactManifest:
        artifact_refs = [item.artifact_ref for item in self.artifacts]
        if len(artifact_refs) != len(set(artifact_refs)):
            raise ValueError("artifact references must be unique")
        proof_refs = [item.artifact_ref for item in self.digest_proofs]
        if set(proof_refs) != set(artifact_refs) or len(proof_refs) != len(set(proof_refs)):
            raise ValueError("every artifact must have exactly one digest proof")
        checks = [(item.check_id, item.check_version) for item in self.attestations]
        if len(checks) != len(set(checks)):
            raise ValueError("artifact attestation identifiers must be unique per version")
        if any(not set(item.artifact_refs).issubset(artifact_refs) for item in self.attestations):
            raise ValueError("artifact attestations must reference manifest artifacts")
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
    manifest_id: str = Field(min_length=1)
    artifact_refs: tuple[str, ...] = Field(min_length=1)
    identity_match: bool
    required_attestations_pass: bool
    source_claim_traceability: bool
    brand_constraints_pass: bool
    artifact_integrity_pass: bool
    findings: tuple[DeliveryFinding, ...] = ()
    proposed_variants: tuple[DistributionVariant, ...] = Field(min_length=1)
    approval_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ready_for_approval: bool

    @property
    def blocking_findings(self) -> tuple[DeliveryFinding, ...]:
        return tuple(item for item in self.findings if item.severity == FindingSeverity.BLOCKING)
