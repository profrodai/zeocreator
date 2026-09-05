"""Provider-neutral publication proposals and secret-safe receipt contracts."""

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator
from zeo_core.contracts import EffectKind

from zeo_creator.contracts.common import CreatorModel, DurableArtifact, assert_secret_safe


class ProviderKind(StrEnum):
    WEBSITE = "website"
    NEWSLETTER = "newsletter"
    X = "x"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"


class ChannelDestination(CreatorModel):
    channel: str = Field(min_length=1)
    provider_kind: ProviderKind
    connection_ref: str = Field(min_length=1)
    destination_account_ref: str = Field(min_length=1)
    scheduled_for: datetime | None = None


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
    artifact_ref: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provider_kind: ProviderKind
    connection_ref: str = Field(min_length=1)
    destination_account_ref: str = Field(min_length=1)
    payload: PublicationPayload
    scheduled_for: datetime | None = None
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
    executed_at: datetime
    outcome: str = Field(min_length=1)
    reconciliation_state: ReconciliationState

    @model_validator(mode="after")
    def receipt_is_secret_safe(self) -> PublicationReceipt:
        assert_secret_safe(self)
        return self
