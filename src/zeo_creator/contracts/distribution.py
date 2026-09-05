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

ProviderKind = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$", min_length=1)]


class ChannelDestination(CreatorModel):
    channel: str = Field(min_length=1)
    provider_kind: ProviderKind
    connection_ref: str = Field(min_length=1)
    destination_account_ref: str = Field(min_length=1)
    scheduled_for: UtcDatetime | None = None


class ChannelPlan(DurableArtifact):
    channel_plan_id: str = Field(min_length=1)
    destinations: tuple[ChannelDestination, ...] = Field(min_length=1)


class PublicationPayload(CreatorModel):
    title: str = Field(min_length=1)
    caption: str = Field(min_length=1)
    description: str = Field(min_length=1)
    alt_text: str = Field(min_length=1)

    @model_validator(mode="after")
    def secret_safe(self) -> PublicationPayload:
        assert_secret_safe(self)
        return self


class ProposedPublicationOperation(DurableArtifact):
    operation_id: str = Field(min_length=1)
    artifact_manifest_ref: str = Field(min_length=1)
    artifact_manifest_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_artifact_refs: tuple[str, ...] = Field(min_length=1)
    provider_kind: ProviderKind
    connection_ref: str = Field(min_length=1)
    destination_account_ref: str = Field(min_length=1)
    payload: PublicationPayload
    scheduled_for: UtcDatetime | None = None
    required_effects: tuple[EffectKind, ...] = (
        EffectKind.WRITE,
        EffectKind.EXTERNAL_COMMUNICATION,
    )
    approval_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def proposal_is_secret_safe(self) -> ProposedPublicationOperation:
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
