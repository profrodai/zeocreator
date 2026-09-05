"""Deterministic construction of a producer-neutral creative brief."""

import re
from datetime import datetime

from zeo_creator.contracts.common import digest_is_current, stable_id
from zeo_creator.contracts.editorial import EditorialAssignment
from zeo_creator.contracts.evidence import ResearchSynthesis
from zeo_creator.contracts.production import (
    AttestationRequirement,
    ContentBrief,
    ContentDocument,
    ExtensionPayload,
)
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError


def _slug_hint(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "content"


def create_brief(
    *,
    assignment: EditorialAssignment,
    publication: PublicationProfile,
    synthesis: ResearchSynthesis,
    creative_direction: str,
    delivery_requirements: tuple[AttestationRequirement, ...],
    producer_extension: ExtensionPayload | None,
    created_at: datetime,
    content_revision: int,
) -> ContentBrief:
    if not all(digest_is_current(item) for item in (assignment, publication, synthesis)):
        raise CreatorDomainError("ZEO_CREATOR_STALE_INPUT", "brief input digest is stale")
    expected_scope = (publication.organization_id, publication.publication_id)
    if (assignment.organization_id, assignment.publication_id) != expected_scope or (
        synthesis.organization_id,
        synthesis.publication_id,
    ) != expected_scope:
        raise CreatorDomainError(
            "ZEO_CREATOR_PUBLICATION_LEAKAGE", "brief inputs cross publications"
        )
    if assignment.brand_profile_ref != publication.reference:
        raise CreatorDomainError(
            "ZEO_CREATOR_BRAND_MISMATCH", "assignment profile reference is stale"
        )

    evidence_refs = set(assignment.evidence_refs)
    if not evidence_refs.issubset(synthesis.evidence_refs):
        raise CreatorDomainError(
            "ZEO_CREATOR_UNSUPPORTED_CLAIM",
            "assignment evidence references must belong to the accepted synthesis",
        )
    claims = tuple(
        claim
        for claim in synthesis.candidate_claims
        if set(claim.evidence_refs).issubset(evidence_refs)
    )
    if not claims or {ref for claim in claims for ref in claim.evidence_refs} != evidence_refs:
        raise CreatorDomainError(
            "ZEO_CREATOR_UNSUPPORTED_CLAIM",
            "every assignment evidence reference must resolve in its synthesis",
        )

    source_content = ContentDocument(
        media_type="text/markdown",
        content=(
            f"# {assignment.hook}\n\n"
            f"{assignment.thesis}\n\n"
            f"## Intended action\n\n{assignment.desired_audience_action}\n\n"
            f"## Call to action\n\n{publication.cta_policy}"
        ),
    )
    brief_id = stable_id(
        "brief", assignment.assignment_id, str(content_revision), publication.reference
    )
    return ContentBrief(
        brief_id=brief_id,
        created_at=created_at,
        organization_id=assignment.organization_id,
        publication_id=assignment.publication_id,
        input_refs=(assignment.assignment_id, synthesis.synthesis_id, publication.reference),
        revision=content_revision,
        assignment_id=assignment.assignment_id,
        content_kind=assignment.content_kind,
        working_title=assignment.hook,
        slug_hint=_slug_hint(assignment.topic),
        objective=assignment.objective,
        audience=assignment.audience,
        desired_audience_action=assignment.desired_audience_action,
        core_message=assignment.thesis,
        creative_direction=creative_direction,
        source_content=source_content,
        participant_refs=publication.participant_refs,
        evidence_claims=claims,
        source_refs=tuple(sorted(evidence_refs)),
        brand_profile_ref=publication.reference,
        style_ref=publication.style_ref,
        prohibited_claims=publication.prohibited_claims,
        target_channels=assignment.target_channels,
        delivery_requirements=delivery_requirements,
        producer_extension=producer_extension,
        content_revision=content_revision,
    )
