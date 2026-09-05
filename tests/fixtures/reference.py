"""Deterministic producer-neutral reference portfolio."""

import hashlib
from datetime import UTC, datetime, timedelta

from zeo_creator.contracts.common import CreatorModel, stable_id
from zeo_creator.contracts.delivery import (
    ArtifactAttestation,
    ArtifactDescriptor,
    ArtifactDigestProof,
    ArtifactManifest,
    DeliveryReviewBundle,
)
from zeo_creator.contracts.distribution import (
    ChannelDestination,
    ChannelPlan,
    ProposedPublicationOperation,
)
from zeo_creator.contracts.editorial import (
    ContentHistoryEntry,
    ContentPortfolioPlan,
    ContentRequirement,
    PortfolioConstraints,
    PublicationObjective,
)
from zeo_creator.contracts.evidence import (
    EvidenceItem,
    EvidenceQuery,
    ResearchSynthesis,
    ResearchWindow,
)
from zeo_creator.contracts.performance import (
    DailyPerformanceAssessment,
    MetricAggregation,
    MetricObservation,
    MetricsQuery,
)
from zeo_creator.contracts.production import (
    AttestationPolicy,
    AttestationRequirement,
    ContentBrief,
)
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.services.assessment import assess_publication_performance
from zeo_creator.services.briefing import create_brief
from zeo_creator.services.distribution import prepare_distribution_operations
from zeo_creator.services.planning import plan_portfolio
from zeo_creator.services.research import synthesize_research
from zeo_creator.services.validation import validate_delivery_bundle

ORGANIZATION_ID = "example-organization"
NOW = datetime(2026, 9, 5, 8, tzinfo=UTC)
DUE_AT = NOW + timedelta(hours=10)
RESEARCH_WINDOW = ResearchWindow(starts_at=NOW - timedelta(days=2), ends_at=NOW)
PLANNING_WINDOW = ResearchWindow(starts_at=NOW, ends_at=NOW + timedelta(days=7))
PERFORMANCE_WINDOW = ResearchWindow(starts_at=NOW - timedelta(days=7), ends_at=NOW)
CONTENT_KINDS = ("article", "video.short", "image.carousel", "newsletter.issue")
REQUIREMENTS = (
    AttestationRequirement(check_id="artifact.readable", policy=AttestationPolicy.REQUIRED),
    AttestationRequirement(check_id="content.claims-traceable", policy=AttestationPolicy.REQUIRED),
    AttestationRequirement(check_id="channel.constraints", policy=AttestationPolicy.REQUIRED),
)


class FakeEvidenceSource:
    def __init__(self, rows: dict[str, tuple[EvidenceItem, ...]]) -> None:
        self.rows = rows

    def retrieve(
        self, query: EvidenceQuery, publication: PublicationProfile
    ) -> tuple[EvidenceItem, ...]:
        del publication
        return self.rows.get(query.query_id, ())


class FakeMetricsSource:
    def __init__(self, rows: dict[str, tuple[MetricObservation, ...]]) -> None:
        self.rows = rows

    def retrieve(self, query: MetricsQuery) -> tuple[MetricObservation, ...]:
        return self.rows.get(query.query_id, ())


class ReferenceSnapshot(CreatorModel):
    profiles: tuple[PublicationProfile, ...]
    syntheses: tuple[ResearchSynthesis, ...]
    plan: ContentPortfolioPlan
    briefs: tuple[ContentBrief, ...]
    manifests: tuple[ArtifactManifest, ...]
    reviews: tuple[DeliveryReviewBundle, ...]
    operations: tuple[ProposedPublicationOperation, ...]
    assessments: tuple[DailyPerformanceAssessment, ...]


def publication_profiles() -> tuple[PublicationProfile, PublicationProfile]:
    return (
        PublicationProfile(
            profile_id="profile_publication_a",
            created_at=NOW,
            organization_id=ORGANIZATION_ID,
            publication_id="publication-a.example",
            display_name="Example Publication A",
            audience_definition="Independent builders improving reliable workflows",
            editorial_pillars=("practice", "evidence", "craft"),
            voice_rules=("Be concrete", "Show provenance"),
            style_ref="style_publication_a@1",
            participant_refs=("host.a",),
            default_channels=("website", "social.network-a"),
            prohibited_topics=("private correspondence",),
            prohibited_claims=("guaranteed outcomes",),
            cta_policy="Invite the audience to test one bounded technique.",
            approval_policy_ref="approval_publication_a@1",
        ),
        PublicationProfile(
            profile_id="profile_publication_b",
            created_at=NOW,
            organization_id=ORGANIZATION_ID,
            publication_id="publication-b.example",
            display_name="Example Publication B",
            audience_definition="Teams governing dependable automation",
            editorial_pillars=("governance", "operations", "measurement"),
            voice_rules=("Name uncertainty", "Separate evidence from hypotheses"),
            style_ref="style_publication_b@1",
            participant_refs=("host.b",),
            default_channels=("newsletter", "video.platform-b"),
            prohibited_topics=("unverified personnel claims",),
            prohibited_claims=("fully autonomous",),
            cta_policy="Invite the audience to define an explicit approval boundary.",
            approval_policy_ref="approval_publication_b@1",
        ),
    )


def evidence_fixture() -> tuple[
    dict[str, tuple[EvidenceItem, ...]], dict[str, tuple[EvidenceQuery, ...]]
]:
    rows: dict[str, tuple[EvidenceItem, ...]] = {}
    queries: dict[str, tuple[EvidenceQuery, ...]] = {}
    topics = {
        "publication-a.example": (
            "Bounded retries",
            "Typed handoffs",
            "Evidence-led explanations",
            "Reusable content atoms",
        ),
        "publication-b.example": (
            "Explicit approvals",
            "Digest-bound decisions",
            "Reconciliation evidence",
            "Normalized performance",
        ),
    }
    for profile in publication_profiles():
        query = EvidenceQuery(
            query_id=f"query_{profile.publication_id}",
            source_kind="web.archive",
            connection_ref=f"connection_{profile.publication_id}",
            research_window=RESEARCH_WINDOW,
            terms=("creator operations",),
        )
        queries[profile.publication_id] = (query,)
        rows[query.query_id] = tuple(
            EvidenceItem(
                evidence_id=stable_id("evidence", profile.publication_id, str(index)),
                created_at=NOW,
                organization_id=ORGANIZATION_ID,
                publication_id=profile.publication_id,
                source_kind=query.source_kind,
                source_ref=f"document_{index}",
                connection_ref=query.connection_ref,
                observed_at=NOW - timedelta(hours=index),
                author_or_origin="Example Research Archive",
                title=topic,
                excerpt_or_summary=f"Evidence supporting {topic.casefold()} in creator operations.",
                canonical_url=f"https://research.example/{profile.publication_id}/{index}",
                publication_scope=profile.publication_id,
            )
            for index, topic in enumerate(topics[profile.publication_id], start=1)
        )
    return rows, queries


def recent_history() -> tuple[ContentHistoryEntry, ...]:
    return tuple(
        ContentHistoryEntry(
            history_id=f"history_{profile.publication_id}",
            created_at=NOW,
            organization_id=ORGANIZATION_ID,
            publication_id=profile.publication_id,
            content_kind="article",
            topic="A previously published topic",
            published_at=NOW - timedelta(days=3),
            artifact_ref=f"artifact_history_{profile.publication_id}",
        )
        for profile in publication_profiles()
    )


def _manifest(brief: ContentBrief) -> ArtifactManifest:
    roles = {
        "article": (("primary", "text/html"),),
        "video.short": (("primary", "video/mp4"), ("captions", "text/vtt")),
        "image.carousel": (("slide-1", "image/png"), ("slide-2", "image/png")),
        "newsletter.issue": (("html", "text/html"), ("plain-text", "text/plain")),
    }[brief.content_kind]
    artifacts: list[ArtifactDescriptor] = []
    for index, (role, media_type) in enumerate(roles, start=1):
        blob = f"{brief.brief_id}:{role}:{brief.core_message}".encode()
        artifacts.append(
            ArtifactDescriptor(
                artifact_ref=stable_id("artifact", brief.brief_id, str(index)),
                role=role,
                media_type=media_type,
                byte_length=len(blob),
                digest=f"sha256:{hashlib.sha256(blob).hexdigest()}",
                storage_ref=f"artifact://example/{brief.brief_id}/{index}",
            )
        )
    artifact_tuple = tuple(artifacts)
    return ArtifactManifest(
        manifest_id=stable_id("manifest", brief.brief_id),
        created_at=NOW,
        organization_id=brief.organization_id,
        publication_id=brief.publication_id,
        input_refs=(brief.brief_id,),
        brief_id=brief.brief_id,
        content_revision=brief.content_revision,
        brief_content_digest=brief.content_digest,
        producer_ref="example.local-producer",
        producer_version="1.0.0",
        brand_profile_ref=brief.brand_profile_ref,
        artifacts=artifact_tuple,
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
            for artifact in artifact_tuple
        ),
        attestations=tuple(
            ArtifactAttestation(
                check_id=requirement.check_id,
                check_version="1.0.0",
                result=True,
                artifact_refs=tuple(item.artifact_ref for item in artifact_tuple),
                evidence_ref=f"attestation://{brief.brief_id}/{requirement.check_id}",
                tool_identity="example.local-producer",
                observed_value="verified",
                expected_constraint="required by accepted brief",
            )
            for requirement in brief.delivery_requirements
        ),
        produced_claim_ids=tuple(claim.claim_id for claim in brief.evidence_claims),
        extracted_text=f"{brief.working_title} {brief.core_message}",
    )


def _channel_plan(brief: ContentBrief) -> ChannelPlan:
    return ChannelPlan(
        channel_plan_id=stable_id("channels", brief.brief_id),
        created_at=NOW,
        organization_id=brief.organization_id,
        publication_id=brief.publication_id,
        input_refs=(brief.brief_id,),
        destinations=tuple(
            ChannelDestination(
                channel=channel,
                provider_kind=f"example.{channel}",
                connection_ref=f"connection_{brief.publication_id}_{channel}",
                destination_account_ref=f"destination_{brief.publication_id}_{channel}",
                scheduled_for=NOW + timedelta(days=1),
            )
            for channel in brief.target_channels
        ),
    )


def build_reference_snapshot() -> ReferenceSnapshot:
    profiles = publication_profiles()
    rows, queries = evidence_fixture()
    evidence_source = FakeEvidenceSource(rows)
    syntheses = tuple(
        synthesize_research(
            organization_id=ORGANIZATION_ID,
            publication=profile,
            research_window=RESEARCH_WINDOW,
            queries=queries[profile.publication_id],
            content_history_refs=tuple(
                item.history_id
                for item in recent_history()
                if item.publication_id == profile.publication_id
            ),
            created_at=NOW,
            revision=1,
            source=evidence_source,
        )
        for profile in profiles
    )
    plan = plan_portfolio(
        organization_id=ORGANIZATION_ID,
        profiles=profiles,
        syntheses=syntheses,
        content_history=recent_history(),
        objectives=tuple(
            PublicationObjective(
                publication_id=profile.publication_id,
                objective=f"Teach {profile.editorial_pillars[0]} through useful content",
                desired_audience_action="Apply one bounded practice",
            )
            for profile in profiles
        ),
        constraints=PortfolioConstraints(
            requirements=tuple(
                ContentRequirement(content_kind=kind, quantity=1) for kind in CONTENT_KINDS
            )
        ),
        planning_window=PLANNING_WINDOW,
        due_at=DUE_AT,
        created_at=NOW,
        revision=1,
    )
    profile_by_id = {item.publication_id: item for item in profiles}
    synthesis_by_id = {item.publication_id: item for item in syntheses}
    briefs = tuple(
        create_brief(
            assignment=assignment,
            publication=profile_by_id[assignment.publication_id],
            synthesis=synthesis_by_id[assignment.publication_id],
            creative_direction="Create a clear, useful, evidence-led piece for the intended audience.",
            delivery_requirements=REQUIREMENTS,
            producer_extension=None,
            created_at=NOW,
            content_revision=1,
        )
        for assignment in plan.assignments
    )
    manifests = tuple(_manifest(brief) for brief in briefs)
    reviews: list[DeliveryReviewBundle] = []
    operations: list[ProposedPublicationOperation] = []
    for brief, manifest in zip(briefs, manifests, strict=True):
        channels = _channel_plan(brief)
        review = validate_delivery_bundle(
            brief=brief,
            manifest=manifest,
            publication=profile_by_id[brief.publication_id],
            synthesis=synthesis_by_id[brief.publication_id],
            channel_plan=channels,
            created_at=NOW,
            revision=1,
        )
        reviews.append(review)
        operations.extend(
            prepare_distribution_operations(
                brief=brief,
                manifest=manifest,
                review=review,
                channel_plan=channels,
                created_at=NOW,
                revision=1,
            )
        )

    observations: dict[str, tuple[MetricObservation, ...]] = {}
    query_by_profile: dict[str, MetricsQuery] = {}
    for profile in profiles:
        operation = next(
            item for item in operations if item.publication_id == profile.publication_id
        )
        query = MetricsQuery(
            query_id=f"metrics_{profile.publication_id}",
            publication_id=profile.publication_id,
            provider_kind=operation.provider_kind,
            connection_ref=operation.connection_ref,
            destination_account_ref=operation.destination_account_ref,
            observation_window=PERFORMANCE_WINDOW,
            operation_refs=(operation.operation_id,),
        )
        query_by_profile[profile.publication_id] = query
        observations[query.query_id] = (
            MetricObservation(
                observation_id=f"observation_{profile.publication_id}",
                created_at=NOW,
                organization_id=ORGANIZATION_ID,
                publication_id=profile.publication_id,
                provider_kind=query.provider_kind,
                connection_ref=query.connection_ref,
                destination_account_ref=query.destination_account_ref,
                observed_at=NOW,
                artifact_ref=operation.selected_artifact_refs[0],
                publication_operation_ref=operation.operation_id,
                metric_name="engagement_rate",
                metric_value=0.12,
                unit="ratio",
                aggregation=MetricAggregation.RATE,
                denominator="impressions",
                attribution_window=PERFORMANCE_WINDOW,
                objective_mapping="audience_engagement",
                baseline=0.08,
                target=0.1,
                normalized_rate=0.12,
                provider_definition="Example provider engagement rate",
                provider_definition_version="1",
            ),
        )
    metrics_source = FakeMetricsSource(observations)
    assessments = tuple(
        assess_publication_performance(
            publication=profile,
            queries=(query_by_profile[profile.publication_id],),
            objective="Teach one bounded creator practice",
            created_at=NOW,
            revision=1,
            source=metrics_source,
        )
        for profile in profiles
    )
    return ReferenceSnapshot(
        profiles=profiles,
        syntheses=syntheses,
        plan=plan,
        briefs=briefs,
        manifests=manifests,
        reviews=tuple(reviews),
        operations=tuple(operations),
        assessments=assessments,
    )
