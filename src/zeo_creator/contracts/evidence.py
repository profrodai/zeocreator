"""Evidence provenance and publication-scoped research synthesis contracts."""

from datetime import datetime

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact


class ResearchWindow(CreatorModel):
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def ordered(self) -> ResearchWindow:
        if self.ends_at <= self.starts_at:
            raise ValueError("research window must end after it starts")
        return self


class EvidenceQuery(CreatorModel):
    query_id: str = Field(min_length=1)
    source_kind: str = Field(min_length=1)
    connection_ref: str = Field(min_length=1)
    research_window: ResearchWindow
    terms: tuple[str, ...] = ()


class EvidenceItem(DurableArtifact):
    evidence_id: str = Field(min_length=1)
    source_kind: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    connection_ref: str = Field(min_length=1)
    observed_at: datetime
    author_or_origin: str = Field(min_length=1)
    title: str = Field(min_length=1)
    excerpt_or_summary: str = Field(min_length=1)
    canonical_url: str | None = None
    publication_scope: str = Field(min_length=1)


class EvidenceClaim(CreatorModel):
    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)


class ResearchSynthesis(DurableArtifact):
    synthesis_id: str = Field(min_length=1)
    research_window: ResearchWindow
    themes: tuple[str, ...] = ()
    opportunities: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    candidate_claims: tuple[EvidenceClaim, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    coverage_gaps: tuple[str, ...] = ()
    content_history_refs: tuple[str, ...] = ()
