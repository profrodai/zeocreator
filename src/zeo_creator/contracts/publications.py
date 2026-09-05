"""Publication identity and brand isolation contracts."""

from pydantic import Field

from zeo_creator.contracts.common import DurableArtifact


class PublicationProfile(DurableArtifact):
    profile_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    audience_definition: str = Field(min_length=1)
    editorial_pillars: tuple[str, ...] = Field(min_length=1)
    voice_rules: tuple[str, ...] = Field(min_length=1)
    style_ref: str = Field(min_length=1)
    participant_refs: tuple[str, ...] = ()
    default_channels: tuple[str, ...] = Field(min_length=1)
    prohibited_topics: tuple[str, ...] = ()
    prohibited_claims: tuple[str, ...] = ()
    cta_policy: str = Field(min_length=1)
    approval_policy_ref: str = Field(min_length=1)

    @property
    def reference(self) -> str:
        return f"{self.profile_id}@{self.revision}:{self.content_digest}"
