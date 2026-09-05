"""Ducktyper render bindings and digest-bound delivery review contracts."""

from enum import StrEnum

from pydantic import Field

from zeo_creator.contracts.common import CreatorModel, DurableArtifact
from zeo_creator.contracts.distribution import ChannelDestination, PublicationPayload


class RenderedArtifact(DurableArtifact):
    artifact_ref: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    brief_id: str = Field(min_length=1)
    content_revision: int = Field(ge=1)
    brief_content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    media_type: str = Field(min_length=1)
    storage_ref: str = Field(min_length=1)
    extracted_text: str = ""


class RenderManifest(DurableArtifact):
    manifest_id: str = Field(min_length=1)
    brief_id: str = Field(min_length=1)
    content_revision: int = Field(ge=1)
    brief_content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifact_ref: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    brand_profile_ref: str = Field(min_length=1)
    included_elements: tuple[str, ...] = ()
    rendered_claim_ids: tuple[str, ...] = ()
    technical_checks: dict[str, bool] = Field(default_factory=dict)


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
