"""Small schema-valid examples used by capability manifests."""

import hashlib
from datetime import UTC, datetime, timedelta

from zeo_creator.contracts.delivery import (
    ArtifactDigestProof,
    RenderAttestation,
    RenderedArtifact,
    RenderManifest,
)
from zeo_creator.contracts.distribution import (
    ChannelDestination,
    ChannelPlan,
    ProviderKind,
)
from zeo_creator.contracts.ducktyper import (
    AnimatedEpisodePayload,
    DucktyperBrief,
    required_render_elements,
)
from zeo_creator.contracts.editorial import (
    DeliverableKind,
    EditorialAssignment,
    PortfolioConstraints,
    PublicationObjective,
)
from zeo_creator.contracts.evidence import (
    EvidenceClaim,
    EvidenceQuery,
    ResearchSynthesis,
    ResearchWindow,
)
from zeo_creator.contracts.performance import MetricsQuery
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.services.validation import validate_delivery_bundle

NOW = datetime(2026, 9, 5, 8, 0, tzinfo=UTC)
WINDOW = ResearchWindow(starts_at=NOW - timedelta(days=1), ends_at=NOW)


def publication() -> PublicationProfile:
    return PublicationProfile(
        profile_id="profile_example",
        created_at=NOW,
        organization_id="org_example",
        publication_id="example.org",
        display_name="Example Publication",
        audience_definition="Practitioners building reliable systems",
        editorial_pillars=("evidence", "operations"),
        voice_rules=("Be concrete",),
        visual_style_ref="style_example@1",
        character_refs=("ducktyper",),
        default_channels=("website", "linkedin"),
        prohibited_topics=("rumour",),
        prohibited_claims=("guaranteed results",),
        cta_policy="Invite the reader to test the idea.",
        approval_policy_ref="approval_example@1",
    )


def synthesis() -> ResearchSynthesis:
    return ResearchSynthesis(
        synthesis_id="synthesis_example",
        created_at=NOW,
        organization_id="org_example",
        publication_id="example.org",
        research_window=WINDOW,
        themes=("Agent reliability", "Typed briefs", "Approval integrity"),
        opportunities=("Agent reliability", "Typed briefs", "Approval integrity"),
        candidate_claims=tuple(
            EvidenceClaim(
                claim_id=f"claim_{index}",
                text=text,
                evidence_refs=(f"evidence_{index}",),
            )
            for index, text in enumerate(
                ("Retries need bounds", "Briefs improve handoffs", "Digests bind approval"),
                start=1,
            )
        ),
        evidence_refs=("evidence_1", "evidence_2", "evidence_3"),
    )


def assignment() -> EditorialAssignment:
    profile = publication()
    return EditorialAssignment(
        assignment_id="assignment_example",
        created_at=NOW,
        organization_id=profile.organization_id,
        publication_id=profile.publication_id,
        deliverable_kind=DeliverableKind.ANIMATED_EPISODE,
        objective="Teach reliable creator operations",
        audience=profile.audience_definition,
        desired_audience_action="Try a bounded workflow",
        topic="Agent reliability",
        thesis="Retries need bounds",
        hook="What makes an agent reliable?",
        evidence_refs=("evidence_1",),
        novelty_rationale="Not in recent history.",
        relationship_to_other_daily_assignments="Introduces the portfolio theme.",
        target_channels=profile.default_channels,
        brand_profile_ref=profile.reference,
        due_at=NOW + timedelta(hours=8),
    )


def brief() -> DucktyperBrief:
    profile = publication()
    item = assignment()
    claim = synthesis().candidate_claims[0]
    return DucktyperBrief(
        brief_id="brief_example",
        created_at=NOW,
        organization_id=item.organization_id,
        publication_id=item.publication_id,
        assignment_id=item.assignment_id,
        deliverable_kind=item.deliverable_kind,
        objective=item.objective,
        audience=item.audience,
        desired_audience_action=item.desired_audience_action,
        topic=item.topic,
        thesis=item.thesis,
        hook=item.hook,
        evidence_claims=(claim,),
        source_refs=claim.evidence_refs,
        brand_profile_ref=profile.reference,
        character_refs=profile.character_refs,
        visual_style_ref=profile.visual_style_ref,
        cta=profile.cta_policy,
        prohibited_claims=profile.prohibited_claims,
        target_channels=profile.default_channels,
        content_revision=1,
        format_payload=AnimatedEpisodePayload(
            script="A short evidence-backed script.",
            scene_beats=("Problem", "Evidence", "Action"),
            dialogue=("What makes an agent reliable?",),
            voice_over=("Retries need bounds",),
            on_screen_text=("Bound the retry",),
            character_actions=("Ducktyper points to the evidence",),
            setting=profile.visual_style_ref,
            duration_seconds=60,
            audio_direction="Clear narration",
            ending=profile.cta_policy,
        ),
    )


def render() -> tuple[RenderedArtifact, RenderManifest]:
    item = brief()
    artifact_bytes = f"synthetic render for {item.brief_id}".encode()
    artifact_digest = f"sha256:{hashlib.sha256(artifact_bytes).hexdigest()}"
    artifact = RenderedArtifact(
        artifact_ref="artifact_example",
        artifact_digest=artifact_digest,
        brief_id=item.brief_id,
        content_revision=item.content_revision,
        brief_content_digest=item.content_digest,
        created_at=NOW,
        organization_id=item.organization_id,
        publication_id=item.publication_id,
        media_type="video/mp4",
        storage_ref="artifact://synthetic/example",
        byte_length=len(artifact_bytes),
        extracted_text=item.thesis,
    )
    check_ids = (
        *(f"element.{element}" for element in required_render_elements(item)),
        "content.extracted_text",
        "media.decode",
        "video.duration",
        "audio.track",
        "destination.website.constraints",
    )
    manifest = RenderManifest(
        manifest_id="manifest_example",
        created_at=NOW,
        organization_id=item.organization_id,
        publication_id=item.publication_id,
        brief_id=item.brief_id,
        content_revision=item.content_revision,
        brief_content_digest=item.content_digest,
        artifact_ref=artifact.artifact_ref,
        artifact_digest=artifact.artifact_digest,
        brand_profile_ref=item.brand_profile_ref,
        artifact_digest_proof=ArtifactDigestProof(
            algorithm="sha256",
            digest=artifact.artifact_digest,
            byte_length=artifact.byte_length,
            storage_ref=artifact.storage_ref,
            retrieved_at=NOW,
            evidence_ref="retrieval://synthetic/example",
            tool_identity="ducktyper.synthetic-verifier",
            tool_version="1.0.0",
        ),
        rendered_claim_ids=(item.evidence_claims[0].claim_id,),
        attestations=tuple(
            RenderAttestation(
                check_id=check_id,
                check_version="1.0.0",
                result=True,
                evidence_ref=f"attestation://{check_id}",
                tool_identity="ducktyper.synthetic-verifier",
                observed_value="verified",
                expected_constraint="must pass",
            )
            for check_id in check_ids
        ),
    )
    return artifact, manifest


def channel_plan() -> ChannelPlan:
    profile = publication()
    return ChannelPlan(
        channel_plan_id="channels_example",
        created_at=NOW,
        organization_id=profile.organization_id,
        publication_id=profile.publication_id,
        destinations=(
            ChannelDestination(
                channel="website",
                provider_kind=ProviderKind.WEBSITE,
                connection_ref="connection_website_example",
                destination_account_ref="destination_example",
            ),
        ),
    )


def research_request() -> dict[str, object]:
    profile = publication()
    return {
        "organization_id": profile.organization_id,
        "publication": profile.model_dump(mode="json"),
        "research_window": WINDOW.model_dump(mode="json"),
        "queries": [
            EvidenceQuery(
                query_id="query_example",
                source_kind="web_archive",
                connection_ref="connection_archive_example",
                research_window=WINDOW,
                terms=("agents",),
            ).model_dump(mode="json")
        ],
        "content_history_refs": [],
        "created_at": NOW.isoformat(),
        "revision": 1,
    }


def plan_request() -> dict[str, object]:
    profile = publication()
    return {
        "organization_id": profile.organization_id,
        "profiles": [profile.model_dump(mode="json")],
        "syntheses": [synthesis().model_dump(mode="json")],
        "content_history": [],
        "objectives": [
            PublicationObjective(
                publication_id=profile.publication_id,
                objective="Teach reliable creator operations",
                desired_audience_action="Try a bounded workflow",
            ).model_dump(mode="json")
        ],
        "constraints": PortfolioConstraints().model_dump(mode="json"),
        "plan_date": "2026-09-05",
        "due_at": (NOW + timedelta(hours=8)).isoformat(),
        "created_at": NOW.isoformat(),
        "revision": 1,
    }


def brief_request() -> dict[str, object]:
    return {
        "assignment": assignment().model_dump(mode="json"),
        "publication": publication().model_dump(mode="json"),
        "synthesis": synthesis().model_dump(mode="json"),
        "created_at": NOW.isoformat(),
        "content_revision": 1,
    }


def delivery_request() -> dict[str, object]:
    artifact, manifest = render()
    return {
        "brief": brief().model_dump(mode="json"),
        "artifact": artifact.model_dump(mode="json"),
        "manifest": manifest.model_dump(mode="json"),
        "publication": publication().model_dump(mode="json"),
        "synthesis": synthesis().model_dump(mode="json"),
        "channel_plan": channel_plan().model_dump(mode="json"),
        "created_at": NOW.isoformat(),
        "revision": 1,
    }


def distribution_request() -> dict[str, object]:
    item = brief()
    artifact, manifest = render()
    channels = channel_plan()
    review = validate_delivery_bundle(
        brief=item,
        artifact=artifact,
        manifest=manifest,
        publication=publication(),
        synthesis=synthesis(),
        channel_plan=channels,
        created_at=NOW,
        revision=1,
    )
    return {
        "brief": item.model_dump(mode="json"),
        "artifact": artifact.model_dump(mode="json"),
        "manifest": manifest.model_dump(mode="json"),
        "review": review.model_dump(mode="json"),
        "channel_plan": channels.model_dump(mode="json"),
        "created_at": NOW.isoformat(),
        "revision": 1,
    }


def performance_request() -> dict[str, object]:
    profile = publication()
    return {
        "publication": profile.model_dump(mode="json"),
        "queries": [
            MetricsQuery(
                query_id="metrics_example",
                publication_id=profile.publication_id,
                provider_kind=ProviderKind.WEBSITE,
                connection_ref="connection_website_example",
                destination_account_ref="destination_example",
                observation_window=WINDOW,
                operation_refs=("operation_example",),
            ).model_dump(mode="json")
        ],
        "objective": "Teach reliable creator operations",
        "created_at": NOW.isoformat(),
        "revision": 1,
    }
