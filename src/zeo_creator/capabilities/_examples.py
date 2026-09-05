"""Small producer-neutral examples used by capability manifests."""

import hashlib
from datetime import UTC, datetime, timedelta

from zeo_creator.contracts.delivery import (
    ArtifactAttestation,
    ArtifactDescriptor,
    ArtifactDigestProof,
    ArtifactManifest,
)
from zeo_creator.contracts.distribution import ChannelDestination, ChannelPlan
from zeo_creator.contracts.editorial import (
    ContentRequirement,
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
from zeo_creator.contracts.production import (
    AttestationPolicy,
    AttestationRequirement,
    ContentBrief,
    ContentDocument,
)
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.services.validation import validate_delivery_bundle

NOW = datetime(2026, 9, 5, 8, tzinfo=UTC)
WINDOW = ResearchWindow(starts_at=NOW - timedelta(days=1), ends_at=NOW)
REQUIREMENTS = (
    AttestationRequirement(check_id="artifact.readable", policy=AttestationPolicy.REQUIRED),
    AttestationRequirement(check_id="content.claims-traceable", policy=AttestationPolicy.REQUIRED),
    AttestationRequirement(check_id="channel.constraints", policy=AttestationPolicy.REQUIRED),
)


def publication() -> PublicationProfile:
    return PublicationProfile(
        profile_id="profile_example_a",
        created_at=NOW,
        organization_id="org_example",
        publication_id="publication-a.example",
        display_name="Example Publication A",
        audience_definition="Practitioners building reliable systems",
        editorial_pillars=("evidence", "operations"),
        voice_rules=("Be concrete",),
        style_ref="style_example_a@1",
        participant_refs=("host.example",),
        default_channels=("website",),
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
        publication_id="publication-a.example",
        research_window=WINDOW,
        themes=("Reliable workflows", "Typed handoffs", "Approval integrity"),
        opportunities=("Reliable workflows", "Typed handoffs", "Approval integrity"),
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
        content_kind="article",
        objective="Teach reliable creator operations",
        audience=profile.audience_definition,
        desired_audience_action="Try a bounded workflow",
        topic="Reliable workflows",
        thesis="Retries need bounds",
        hook="A bounded workflow is a reliable workflow",
        evidence_refs=("evidence_1",),
        novelty_rationale="Not present in supplied history.",
        relationship_to_other_assignments="Introduces the portfolio theme.",
        target_channels=profile.default_channels,
        brand_profile_ref=profile.reference,
        due_at=NOW + timedelta(hours=8),
    )


def brief() -> ContentBrief:
    item = assignment()
    profile = publication()
    claim = synthesis().candidate_claims[0]
    return ContentBrief(
        brief_id="brief_example",
        created_at=NOW,
        organization_id=item.organization_id,
        publication_id=item.publication_id,
        assignment_id=item.assignment_id,
        content_kind=item.content_kind,
        working_title=item.hook,
        slug_hint="reliable-workflows",
        objective=item.objective,
        audience=item.audience,
        desired_audience_action=item.desired_audience_action,
        core_message=item.thesis,
        creative_direction="Write a concise evidence-led explainer.",
        source_content=ContentDocument(media_type="text/markdown", content="# Reliable workflows"),
        participant_refs=profile.participant_refs,
        evidence_claims=(claim,),
        source_refs=claim.evidence_refs,
        brand_profile_ref=profile.reference,
        style_ref=profile.style_ref,
        prohibited_claims=profile.prohibited_claims,
        target_channels=item.target_channels,
        delivery_requirements=REQUIREMENTS,
        content_revision=1,
    )


def manifest() -> ArtifactManifest:
    item = brief()
    blobs = {
        "artifact_html": b"<article>Retries need bounds</article>",
        "artifact_text": b"Retries need bounds",
    }
    artifacts = tuple(
        ArtifactDescriptor(
            artifact_ref=reference,
            role="primary" if reference.endswith("html") else "plain-text",
            media_type="text/html" if reference.endswith("html") else "text/plain",
            byte_length=len(blob),
            digest=f"sha256:{hashlib.sha256(blob).hexdigest()}",
            storage_ref=f"artifact://example/{reference}",
        )
        for reference, blob in blobs.items()
    )
    return ArtifactManifest(
        manifest_id="manifest_example",
        created_at=NOW,
        organization_id=item.organization_id,
        publication_id=item.publication_id,
        brief_id=item.brief_id,
        content_revision=item.content_revision,
        brief_content_digest=item.content_digest,
        producer_ref="example.local-producer",
        producer_version="1.0.0",
        brand_profile_ref=item.brand_profile_ref,
        artifacts=artifacts,
        digest_proofs=tuple(
            ArtifactDigestProof(
                artifact_ref=artifact.artifact_ref,
                algorithm="sha256",
                digest=artifact.digest,
                byte_length=artifact.byte_length,
                storage_ref=artifact.storage_ref,
                retrieved_at=NOW,
                evidence_ref=f"retrieval://{artifact.artifact_ref}",
                tool_identity="example.byte-verifier",
                tool_version="1.0.0",
            )
            for artifact in artifacts
        ),
        attestations=tuple(
            ArtifactAttestation(
                check_id=requirement.check_id,
                check_version="1.0.0",
                result=True,
                artifact_refs=tuple(artifact.artifact_ref for artifact in artifacts),
                evidence_ref=f"attestation://{requirement.check_id}",
                tool_identity="example.local-producer",
                observed_value="verified",
                expected_constraint="required by accepted brief",
            )
            for requirement in REQUIREMENTS
        ),
        produced_claim_ids=(item.evidence_claims[0].claim_id,),
        extracted_text=item.core_message,
    )


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
                provider_kind="website",
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
                source_kind="web.archive",
                connection_ref="connection_archive_example",
                research_window=WINDOW,
                terms=("workflows",),
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
        "constraints": PortfolioConstraints(
            requirements=(ContentRequirement(content_kind="article", quantity=1),)
        ).model_dump(mode="json"),
        "planning_window": WINDOW.model_dump(mode="json"),
        "due_at": (NOW + timedelta(hours=8)).isoformat(),
        "created_at": NOW.isoformat(),
        "revision": 1,
    }


def brief_request() -> dict[str, object]:
    return {
        "assignment": assignment().model_dump(mode="json"),
        "publication": publication().model_dump(mode="json"),
        "synthesis": synthesis().model_dump(mode="json"),
        "creative_direction": "Write a concise evidence-led explainer.",
        "delivery_requirements": [item.model_dump(mode="json") for item in REQUIREMENTS],
        "created_at": NOW.isoformat(),
        "content_revision": 1,
    }


def delivery_request() -> dict[str, object]:
    item = brief()
    produced = manifest()
    channels = channel_plan()
    return {
        "brief": item.model_dump(mode="json"),
        "manifest": produced.model_dump(mode="json"),
        "publication": publication().model_dump(mode="json"),
        "synthesis": synthesis().model_dump(mode="json"),
        "channel_plan": channels.model_dump(mode="json"),
        "created_at": NOW.isoformat(),
        "revision": 1,
    }


def distribution_request() -> dict[str, object]:
    request = delivery_request()
    request["review"] = validate_delivery_bundle(
        brief=brief(),
        manifest=manifest(),
        publication=publication(),
        synthesis=synthesis(),
        channel_plan=channel_plan(),
        created_at=NOW,
        revision=1,
    ).model_dump(mode="json")
    request.pop("publication")
    request.pop("synthesis")
    return request


def performance_request() -> dict[str, object]:
    profile = publication()
    return {
        "publication": profile.model_dump(mode="json"),
        "queries": [
            MetricsQuery(
                query_id="metrics_example",
                publication_id=profile.publication_id,
                provider_kind="website.analytics",
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
