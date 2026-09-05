"""Deterministic construction of Ducktyper's external typed brief."""

from datetime import datetime

from zeo_creator.contracts.common import digest_is_current, stable_id
from zeo_creator.contracts.ducktyper import (
    AnimatedEpisodePayload,
    ComicSlidesPayload,
    DucktyperBrief,
    FormatPayload,
    HudPayload,
)
from zeo_creator.contracts.editorial import DeliverableKind, EditorialAssignment
from zeo_creator.contracts.evidence import ResearchSynthesis
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.errors import CreatorDomainError


def create_brief(
    *,
    assignment: EditorialAssignment,
    publication: PublicationProfile,
    synthesis: ResearchSynthesis,
    created_at: datetime,
    content_revision: int,
) -> DucktyperBrief:
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
    if not claims or set(ref for claim in claims for ref in claim.evidence_refs) != evidence_refs:
        raise CreatorDomainError(
            "ZEO_CREATOR_UNSUPPORTED_CLAIM",
            "every assignment evidence reference must resolve in its synthesis",
        )

    payload: FormatPayload
    if assignment.deliverable_kind == DeliverableKind.ANIMATED_EPISODE:
        payload = AnimatedEpisodePayload(
            script=f"{assignment.hook}\n\n{assignment.thesis}\n\n{publication.cta_policy}",
            scene_beats=("Establish the problem", "Show the evidence", "Resolve with the thesis"),
            dialogue=(assignment.hook, assignment.thesis),
            voice_over=(assignment.thesis,),
            on_screen_text=(assignment.topic, assignment.desired_audience_action),
            character_actions=("Ducktyper enters", "Ducktyper points to evidence"),
            setting=publication.visual_style_ref,
            duration_seconds=60,
            audio_direction="Clear spoken delivery with restrained music.",
            ending=publication.cta_policy,
        )
    elif assignment.deliverable_kind == DeliverableKind.HUD:
        payload = HudPayload(
            information_hierarchy=(assignment.topic, assignment.thesis),
            metrics=("evidence count", "source coverage"),
            labels=("Signal", "Evidence", "Action"),
            motion_sequence=("Reveal signal", "Connect evidence", "Highlight action"),
            visual_metaphor="A navigable evidence radar",
            screen_regions=("header", "primary evidence", "action rail"),
            narration=(assignment.hook, assignment.thesis),
            highlight_events=("theme reveal", "claim trace", "CTA"),
        )
    else:
        payload = ComicSlidesPayload(
            panel_count=3,
            panel_beats=("Set up the tension", "Reveal the evidence", "Land the action"),
            dialogue_captions=(assignment.hook, assignment.thesis, publication.cta_policy),
            poses=("curious", "explaining", "decisive"),
            continuity_requirements=("Preserve character and palette across panels",),
            slide_headlines=(assignment.topic, "What the evidence says", "What to do next"),
            final_cta=publication.cta_policy,
        )

    brief_id = stable_id(
        "brief",
        assignment.assignment_id,
        str(content_revision),
        publication.reference,
    )
    return DucktyperBrief(
        brief_id=brief_id,
        created_at=created_at,
        organization_id=assignment.organization_id,
        publication_id=assignment.publication_id,
        input_refs=(assignment.assignment_id, synthesis.synthesis_id, publication.reference),
        revision=content_revision,
        assignment_id=assignment.assignment_id,
        deliverable_kind=assignment.deliverable_kind,
        objective=assignment.objective,
        audience=assignment.audience,
        desired_audience_action=assignment.desired_audience_action,
        topic=assignment.topic,
        thesis=assignment.thesis,
        hook=assignment.hook,
        evidence_claims=claims,
        source_refs=tuple(sorted(evidence_refs)),
        brand_profile_ref=publication.reference,
        character_refs=publication.character_refs,
        visual_style_ref=publication.visual_style_ref,
        cta=publication.cta_policy,
        prohibited_claims=publication.prohibited_claims,
        target_channels=assignment.target_channels,
        content_revision=content_revision,
        format_payload=payload,
    )
