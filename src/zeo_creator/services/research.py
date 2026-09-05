"""Deterministic publication-scoped evidence synthesis."""

from datetime import datetime

from zeo_creator.contracts.common import digest_is_current, stable_id
from zeo_creator.contracts.evidence import (
    EvidenceClaim,
    EvidenceItem,
    EvidenceQuery,
    ResearchSynthesis,
    ResearchWindow,
)
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError
from zeo_creator.ports.evidence_sources import EvidenceSourcePort


def synthesize_research(
    *,
    organization_id: str,
    publication: PublicationProfile,
    research_window: ResearchWindow,
    queries: tuple[EvidenceQuery, ...],
    content_history_refs: tuple[str, ...],
    created_at: datetime,
    revision: int,
    source: EvidenceSourcePort,
) -> ResearchSynthesis:
    if publication.organization_id != organization_id:
        raise CreatorDomainError("ZEO_CREATOR_SCOPE_MISMATCH", "publication organization mismatch")
    if not digest_is_current(publication):
        raise CreatorDomainError("ZEO_CREATOR_STALE_INPUT", "publication profile digest is stale")

    by_id: dict[str, EvidenceItem] = {}
    risks: list[str] = []
    for query in queries:
        if query.research_window != research_window:
            raise CreatorDomainError(
                "ZEO_CREATOR_WINDOW_MISMATCH", "query research window mismatch"
            )
        for item in source.retrieve(query, publication):
            if not digest_is_current(item):
                raise CreatorDomainError("ZEO_CREATOR_STALE_INPUT", "evidence item digest is stale")
            if item.organization_id != organization_id:
                raise CreatorDomainError(
                    "ZEO_CREATOR_SCOPE_MISMATCH", "evidence organization mismatch"
                )
            if item.publication_scope != publication.publication_id:
                raise CreatorDomainError(
                    "ZEO_CREATOR_PUBLICATION_LEAKAGE",
                    "evidence is not explicitly scoped to this publication",
                )
            if item.connection_ref != query.connection_ref or item.source_kind != query.source_kind:
                raise CreatorDomainError(
                    "ZEO_CREATOR_PROVENANCE_MISMATCH",
                    "connector observation does not match the requested provenance",
                )
            by_id.setdefault(item.evidence_id, item)

    evidence = tuple(sorted(by_id.values(), key=lambda item: item.evidence_id))
    if not evidence:
        raise CreatorDomainError("ZEO_CREATOR_NO_EVIDENCE", "no permitted evidence was returned")

    prohibited = tuple(term.casefold() for term in publication.prohibited_topics)
    usable: list[EvidenceItem] = []
    for item in evidence:
        candidate = f"{item.title} {item.excerpt_or_summary}".casefold()
        matched = next((term for term in prohibited if term in candidate), None)
        if matched:
            risks.append(f"Excluded evidence {item.evidence_id}: prohibited topic {matched}")
        else:
            usable.append(item)
    if not usable:
        raise CreatorDomainError(
            "ZEO_CREATOR_NO_USABLE_EVIDENCE", "all evidence was excluded by policy"
        )

    claims = tuple(
        EvidenceClaim(
            claim_id=stable_id("claim", publication.publication_id, item.evidence_id),
            text=item.excerpt_or_summary,
            evidence_refs=(item.evidence_id,),
        )
        for item in usable
    )
    evidence_refs = tuple(item.evidence_id for item in usable)
    return ResearchSynthesis(
        synthesis_id=stable_id(
            "synthesis",
            organization_id,
            publication.publication_id,
            research_window.starts_at.isoformat(),
            research_window.ends_at.isoformat(),
            str(revision),
        ),
        created_at=created_at,
        organization_id=organization_id,
        publication_id=publication.publication_id,
        input_refs=(publication.reference, *(query.query_id for query in queries), *evidence_refs),
        revision=revision,
        research_window=research_window,
        themes=tuple(item.title for item in usable),
        opportunities=tuple(item.title for item in usable),
        risks=tuple(risks),
        candidate_claims=claims,
        evidence_refs=evidence_refs,
        coverage_gaps=() if len(usable) >= 3 else ("Fewer than three independent evidence items",),
        content_history_refs=content_history_refs,
    )
