"""Provider-neutral publication proposals and secret-safe receipt contracts."""

from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator
from zeo_core.contracts import EffectKind

from zeo_creator.contracts.common import (
    CreatorModel,
    DurableArtifact,
    UtcDatetime,
    assert_secret_safe,
)
from zeo_creator.contracts.production import ContentDocument, ExtensionPayload

ProviderKind = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$", min_length=1)]


class ChannelDestination(CreatorModel):
    channel: str = Field(min_length=1)
    provider_kind: ProviderKind
    connection_ref: str = Field(min_length=1)
    destination_account_ref: str = Field(min_length=1)
    scheduled_for: UtcDatetime | None = None


class DistributionVariant(CreatorModel):
    destination: ChannelDestination
    selected_artifact_refs: tuple[str, ...] = Field(min_length=1)
    content: ContentDocument
    accessibility_text: str | None = None
    extension: ExtensionPayload | None = None

    @model_validator(mode="after")
    def unique_artifacts(self) -> DistributionVariant:
        if len(self.selected_artifact_refs) != len(set(self.selected_artifact_refs)):
            raise ValueError("selected artifact references must be unique")
        return self


class ChannelPlan(DurableArtifact):
    channel_plan_id: str = Field(min_length=1)
    variants: tuple[DistributionVariant, ...] = Field(min_length=1)


class ProposedPublicationOperation(DurableArtifact):
    operation_id: str = Field(min_length=1)
    artifact_manifest_ref: str = Field(min_length=1)
    artifact_manifest_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    channel: str = Field(min_length=1)
    destination: ChannelDestination
    selected_artifact_refs: tuple[str, ...] = Field(min_length=1)
    content: ContentDocument
    accessibility_text: str | None = None
    extension: ExtensionPayload | None = None
    scheduled_for: UtcDatetime | None = None
    required_effects: tuple[EffectKind, ...] = (
        EffectKind.WRITE,
        EffectKind.EXTERNAL_COMMUNICATION,
    )
    approval_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def proposal_is_secret_safe(self) -> ProposedPublicationOperation:
        if self.channel != self.destination.channel:
            raise ValueError("operation channel must match its destination")
        if self.scheduled_for != self.destination.scheduled_for:
            raise ValueError("operation schedule must match its destination")
        assert_secret_safe(self)
        return self


class ReconciliationState(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    NEEDS_REVIEW = "needs_review"


class PublicationReceipt(DurableArtifact):
    receipt_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    provider_kind: ProviderKind
    connection_ref: str = Field(min_length=1)
    provider_operation_ref: str = Field(min_length=1)
    executed_at: UtcDatetime
    outcome: str = Field(min_length=1)
    reconciliation_state: ReconciliationState

    @model_validator(mode="after")
    def receipt_is_secret_safe(self) -> PublicationReceipt:
        assert_secret_safe(self)
        return self
