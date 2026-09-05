"""Deterministic two-property, six-deliverable dogfood portfolio."""

import hashlib
from datetime import UTC, datetime, timedelta

from zeo_core.tools import invoke_sync

from zeo_creator.capabilities.assess_performance import (
    AssessPerformanceRequest,
    AssessPerformanceResponse,
)
from zeo_creator.capabilities.create_ducktyper_brief import (
    CreateDucktyperBriefRequest,
    CreateDucktyperBriefResponse,
)
from zeo_creator.capabilities.plan_daily_portfolio import (
    PlanDailyPortfolioRequest,
    PlanDailyPortfolioResponse,
)
from zeo_creator.capabilities.prepare_distribution import (
    PrepareDistributionRequest,
    PrepareDistributionResponse,
)
from zeo_creator.capabilities.research_synthesis import (
    ResearchSynthesisRequest,
    ResearchSynthesisResponse,
)
from zeo_creator.capabilities.validate_delivery import (
    ValidateDeliveryRequest,
    ValidateDeliveryResponse,
)
from zeo_creator.contracts.common import CreatorModel, stable_id
from zeo_creator.contracts.delivery import (
    ArtifactDigestProof,
    DeliveryReviewBundle,
    RenderAttestation,
    RenderedArtifact,
    RenderManifest,
)
from zeo_creator.contracts.distribution import (
    ChannelDestination,
    ChannelPlan,
    ProposedPublicationOperation,
    ProviderKind,
)
from zeo_creator.contracts.ducktyper import DucktyperBrief, required_render_elements
from zeo_creator.contracts.editorial import (
    ContentHistoryEntry,
    DailyEditorialPlan,
    DeliverableKind,
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
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.registry import capability_registry
from zeo_creator.runtime import make_context

ORGANIZATION_ID = "ducktyper-dogfood"
NOW = datetime(2026, 9, 5, 8, 0, tzinfo=UTC)
DUE_AT = NOW + timedelta(hours=10)
RESEARCH_WINDOW = ResearchWindow(starts_at=NOW - timedelta(days=1), ends_at=NOW)
PERFORMANCE_WINDOW = ResearchWindow(starts_at=NOW - timedelta(days=7), ends_at=NOW)


class FakeEvidenceSource:
    def __init__(self, evidence_by_query: dict[str, tuple[EvidenceItem, ...]]) -> None:
        self.evidence_by_query = evidence_by_query
        self.calls: list[str] = []

    def retrieve(
        self,
        query: EvidenceQuery,
        publication: PublicationProfile,
    ) -> tuple[EvidenceItem, ...]:
        del publication
        self.calls.append(query.query_id)
        return self.evidence_by_query.get(query.query_id, ())


class FakeMetricsSource:
    def __init__(self, observations_by_query: dict[str, tuple[MetricObservation, ...]]) -> None:
        self.observations_by_query = observations_by_query
        self.calls: list[str] = []

    def retrieve(self, query: MetricsQuery) -> tuple[MetricObservation, ...]:
        self.calls.append(query.query_id)
        return self.observations_by_query.get(query.query_id, ())


class DogfoodSnapshot(CreatorModel):
    profiles: tuple[PublicationProfile, ...]
    syntheses: tuple[ResearchSynthesis, ...]
    plan: DailyEditorialPlan
    briefs: tuple[DucktyperBrief, ...]
    artifacts: tuple[RenderedArtifact, ...]
    manifests: tuple[RenderManifest, ...]
    reviews: tuple[DeliveryReviewBundle, ...]
    operations: tuple[ProposedPublicationOperation, ...]
    assessments: tuple[DailyPerformanceAssessment, ...]
    evidence_calls: tuple[str, ...]
    metrics_calls: tuple[str, ...]


def publication_profiles() -> tuple[PublicationProfile, PublicationProfile]:
    profrod = PublicationProfile(
        profile_id="profile_profrod_ai",
        created_at=NOW,
        organization_id=ORGANIZATION_ID,
        publication_id="profrod.ai",
        display_name="Prof Rod",
        audience_definition="Savvy builders shipping practical AI systems",
        editorial_pillars=("agent engineering", "AI product craft", "builder leverage"),
        voice_rules=("First person", "Pragmatic", "Show the mechanism"),
        visual_style_ref="style_profrod_editorial@1",
        character_refs=("prof_rod", "ducktyper"),
        default_channels=("website", "linkedin", "youtube"),
        prohibited_topics=("celebrity gossip",),
        prohibited_claims=("guaranteed revenue",),
        cta_policy="Invite builders to test the technique in a bounded project.",
        approval_policy_ref="approval_profrod@1",
    )
    zeroemployee = PublicationProfile(
        profile_id="profile_zeroemployee_org",
        created_at=NOW,
        organization_id=ORGANIZATION_ID,
        publication_id="zeroemployee.org",
        display_name="Zero Employee",
        audience_definition="Organizations governing dependable digital labor",
        editorial_pillars=("governance", "authority boundaries", "operational evidence"),
        voice_rules=("Institutional", "Precise", "Separate fact from hypothesis"),
        visual_style_ref="style_zeroemployee_systems@1",
        character_refs=("zeo_operator",),
        default_channels=("website", "newsletter", "x"),
        prohibited_topics=("unbounded autonomy",),
        prohibited_claims=("humans are obsolete",),
        cta_policy="Invite operators to adopt one explicit control boundary.",
        approval_policy_ref="approval_zeroemployee@1",
    )
    return profrod, zeroemployee


def _evidence_item(
    *,
    publication_id: str,
    number: int,
    source_kind: str,
    connection_ref: str,
    title: str,
    claim: str,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"evidence_{publication_id}_{number}",
        created_at=NOW,
        organization_id=ORGANIZATION_ID,
        publication_id=publication_id,
        source_kind=source_kind,
        source_ref=f"source_{publication_id}_{number}",
        connection_ref=connection_ref,
        observed_at=NOW - timedelta(hours=number),
        author_or_origin=f"fixture-origin-{number}",
        title=title,
        excerpt_or_summary=claim,
        canonical_url=f"https://fixtures.invalid/{publication_id}/{number}",
        publication_scope=publication_id,
    )


def evidence_fixture() -> tuple[
    dict[str, tuple[EvidenceItem, ...]],
    dict[str, tuple[EvidenceQuery, ...]],
]:
    evidence_by_query: dict[str, tuple[EvidenceItem, ...]] = {}
    queries_by_publication: dict[str, tuple[EvidenceQuery, ...]] = {}
    topics = {
        "profrod.ai": (
            ("AI basics", "Basic AI explainers remain common."),
            ("Bounded agent retries", "Bounded retries reduce runaway automation risk."),
            ("Typed creator handoffs", "Typed briefs reduce renderer ambiguity."),
            ("Evidence-led demos", "Source-linked demos improve builder trust."),
        ),
        "zeroemployee.org": (
            ("AI basics", "Generic AI overviews remain common."),
            ("Exact effect authority", "Exact effect authorization narrows provider-write risk."),
            ("Digest-bound approvals", "Approval digests expose post-review mutation."),
            ("Reconciliation evidence", "Receipts support explicit reconciliation state."),
        ),
    }
    source_axes = (
        ("gmail", "connection_mail_fixture"),
        ("web_archive", "connection_archive_fixture"),
        ("social_analytics", "connection_social_fixture"),
        ("web_archive", "connection_archive_fixture"),
    )
    for publication_id, rows in topics.items():
        queries: list[EvidenceQuery] = []
        grouped: dict[tuple[str, str], list[EvidenceItem]] = {}
        for index, ((title, claim), (source_kind, connection_ref)) in enumerate(
            zip(rows, source_axes, strict=True), start=1
        ):
            item = _evidence_item(
                publication_id=publication_id,
                number=index,
                source_kind=source_kind,
                connection_ref=connection_ref,
                title=title,
                claim=claim,
            )
            grouped.setdefault((source_kind, connection_ref), []).append(item)
        for index, ((source_kind, connection_ref), items) in enumerate(sorted(grouped.items())):
            query = EvidenceQuery(
                query_id=f"query_{publication_id}_{index}",
                source_kind=source_kind,
                connection_ref=connection_ref,
                research_window=RESEARCH_WINDOW,
                terms=(publication_id,),
            )
            queries.append(query)
            evidence_by_query[query.query_id] = tuple(items)
        queries_by_publication[publication_id] = tuple(queries)
    return evidence_by_query, queries_by_publication


def recent_history() -> tuple[ContentHistoryEntry, ...]:
    return tuple(
        ContentHistoryEntry(
            history_id=f"history_{profile.publication_id}",
            created_at=NOW - timedelta(days=1),
            organization_id=ORGANIZATION_ID,
            publication_id=profile.publication_id,
            deliverable_kind=DeliverableKind.HUD,
            topic="AI basics",
            published_at=NOW - timedelta(days=1),
            artifact_ref=f"artifact_history_{profile.publication_id}",
        )
        for profile in publication_profiles()
    )


def objectives() -> tuple[PublicationObjective, ...]:
    return (
        PublicationObjective(
            publication_id="profrod.ai",
            objective="Help builders ship one reliable creator operation",
            desired_audience_action="Implement a typed handoff",
        ),
        PublicationObjective(
            publication_id="zeroemployee.org",
            objective="Teach organizations to govern provider effects",
            desired_audience_action="Adopt an explicit approval boundary",
        ),
    )


def _channel_plan(brief: DucktyperBrief) -> ChannelPlan:
    provider_by_channel = {
        "website": ProviderKind.WEBSITE,
        "linkedin": ProviderKind.LINKEDIN,
        "youtube": ProviderKind.YOUTUBE,
        "newsletter": ProviderKind.NEWSLETTER,
        "x": ProviderKind.X,
    }
    destinations = tuple(
        ChannelDestination(
            channel=channel,
            provider_kind=provider_by_channel[channel],
            connection_ref=f"connection_{brief.publication_id}_{channel}",
            destination_account_ref=f"destination_{brief.publication_id}_{channel}",
            scheduled_for=NOW + timedelta(days=1),
        )
        for channel in brief.target_channels[:2]
    )
    return ChannelPlan(
        channel_plan_id=stable_id("channels", brief.brief_id),
        created_at=NOW,
        organization_id=brief.organization_id,
        publication_id=brief.publication_id,
        input_refs=(brief.brief_id,),
        destinations=destinations,
    )


def _synthetic_render(brief: DucktyperBrief) -> tuple[RenderedArtifact, RenderManifest]:
    artifact_bytes = f"synthetic render for {brief.content_digest}".encode()
    artifact_digest = f"sha256:{hashlib.sha256(artifact_bytes).hexdigest()}"
    artifact = RenderedArtifact(
        artifact_ref=stable_id("artifact", brief.brief_id),
        artifact_digest=artifact_digest,
        brief_id=brief.brief_id,
        content_revision=brief.content_revision,
        brief_content_digest=brief.content_digest,
        created_at=NOW,
        organization_id=brief.organization_id,
        publication_id=brief.publication_id,
        input_refs=(brief.brief_id,),
        media_type="video/mp4"
        if brief.deliverable_kind != DeliverableKind.COMIC_SLIDES
        else "application/pdf",
        storage_ref=f"artifact://ducktyper/{brief.brief_id}",
        byte_length=len(artifact_bytes),
        extracted_text=f"{brief.hook} {brief.thesis} {brief.cta}",
    )
    channel_checks = (f"destination.{channel}.constraints" for channel in brief.target_channels[:2])
    format_checks = {
        DeliverableKind.ANIMATED_EPISODE: ("media.decode", "video.duration", "audio.track"),
        DeliverableKind.HUD: ("media.decode", "visual.dimensions", "motion.sequence"),
        DeliverableKind.COMIC_SLIDES: (
            "media.decode",
            "visual.dimensions",
            "comic.panel_count",
        ),
    }[brief.deliverable_kind]
    check_ids = (
        *(f"element.{element}" for element in required_render_elements(brief)),
        "content.extracted_text",
        *format_checks,
        *channel_checks,
    )
    manifest = RenderManifest(
        manifest_id=stable_id("manifest", brief.brief_id),
        created_at=NOW,
        organization_id=brief.organization_id,
        publication_id=brief.publication_id,
        input_refs=(brief.brief_id, artifact.artifact_ref),
        brief_id=brief.brief_id,
        content_revision=brief.content_revision,
        brief_content_digest=brief.content_digest,
        artifact_ref=artifact.artifact_ref,
        artifact_digest=artifact.artifact_digest,
        brand_profile_ref=brief.brand_profile_ref,
        artifact_digest_proof=ArtifactDigestProof(
            algorithm="sha256",
            digest=artifact.artifact_digest,
            byte_length=artifact.byte_length,
            storage_ref=artifact.storage_ref,
            retrieved_at=NOW,
            evidence_ref=f"retrieval://{artifact.artifact_ref}",
            tool_identity="ducktyper.synthetic-verifier",
            tool_version="1.0.0",
        ),
        rendered_claim_ids=tuple(claim.claim_id for claim in brief.evidence_claims),
        attestations=tuple(
            RenderAttestation(
                check_id=check_id,
                check_version="1.0.0",
                result=True,
                evidence_ref=f"attestation://{artifact.artifact_ref}/{check_id}",
                tool_identity="ducktyper.synthetic-verifier",
                observed_value="verified",
                expected_constraint="must pass",
            )
            for check_id in check_ids
        ),
    )
    return artifact, manifest


def _metric_fixture(
    operations: tuple[ProposedPublicationOperation, ...],
) -> tuple[dict[str, tuple[MetricObservation, ...]], dict[str, tuple[MetricsQuery, ...]]]:
    observations_by_query: dict[str, tuple[MetricObservation, ...]] = {}
    queries_by_publication: dict[str, tuple[MetricsQuery, ...]] = {}
    for profile in publication_profiles():
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
        observations_by_query[query.query_id] = tuple(
            MetricObservation(
                observation_id=f"observation_{profile.publication_id}_{metric}",
                created_at=NOW,
                organization_id=ORGANIZATION_ID,
                publication_id=profile.publication_id,
                input_refs=(operation.operation_id,),
                provider_kind=operation.provider_kind,
                connection_ref=operation.connection_ref,
                destination_account_ref=operation.destination_account_ref,
                observed_at=NOW,
                artifact_ref=operation.artifact_ref,
                publication_operation_ref=operation.operation_id,
                metric_name=metric,
                metric_value=value,
                unit="ratio",
                aggregation=MetricAggregation.RATE,
                denominator="impressions",
                attribution_window=PERFORMANCE_WINDOW,
                objective_mapping="audience_engagement",
                baseline=0.05,
                target=0.08,
                normalized_rate=0.12 if metric == "views" else 0.084,
                provider_definition=f"Provider-defined {metric}",
                provider_definition_version="2026-09-01",
            )
            for metric, value in (("views", 1200.0), ("engagements", 84.0))
        )
        queries_by_publication[profile.publication_id] = (query,)
    return observations_by_query, queries_by_publication


def build_dogfood_snapshot() -> DogfoodSnapshot:
    registry = capability_registry()
    profiles = publication_profiles()
    evidence_rows, queries_by_publication = evidence_fixture()
    evidence_source = FakeEvidenceSource(evidence_rows)

    syntheses: list[ResearchSynthesis] = []
    for profile in profiles:
        result = invoke_sync(
            registry.get("creator.research_synthesis@1.0.0"),
            ResearchSynthesisRequest(
                organization_id=ORGANIZATION_ID,
                publication=profile,
                research_window=RESEARCH_WINDOW,
                queries=queries_by_publication[profile.publication_id],
                content_history_refs=(f"history_{profile.publication_id}",),
                created_at=NOW,
            ),
            make_context(
                capability_name="research_synthesis",
                services={"creator.evidence_source": evidence_source},
            ),
        )
        assert isinstance(result.data, ResearchSynthesisResponse)
        syntheses.append(result.data.synthesis)

    plan_result = invoke_sync(
        registry.get("creator.plan_daily_portfolio@1.0.0"),
        PlanDailyPortfolioRequest(
            organization_id=ORGANIZATION_ID,
            profiles=profiles,
            syntheses=tuple(syntheses),
            content_history=recent_history(),
            objectives=objectives(),
            constraints=PortfolioConstraints(),
            plan_date="2026-09-05",
            due_at=DUE_AT,
            created_at=NOW,
        ),
        make_context(capability_name="plan_daily_portfolio"),
    )
    assert isinstance(plan_result.data, PlanDailyPortfolioResponse)
    plan = plan_result.data.plan

    profile_by_id = {item.publication_id: item for item in profiles}
    synthesis_by_id = {item.publication_id: item for item in syntheses}
    briefs: list[DucktyperBrief] = []
    artifacts: list[RenderedArtifact] = []
    manifests: list[RenderManifest] = []
    reviews: list[DeliveryReviewBundle] = []
    operations: list[ProposedPublicationOperation] = []
    for assignment in plan.assignments:
        profile = profile_by_id[assignment.publication_id]
        synthesis = synthesis_by_id[assignment.publication_id]
        brief_result = invoke_sync(
            registry.get("creator.create_ducktyper_brief@1.0.0"),
            CreateDucktyperBriefRequest(
                assignment=assignment,
                publication=profile,
                synthesis=synthesis,
                created_at=NOW,
            ),
            make_context(capability_name="create_ducktyper_brief"),
        )
        assert isinstance(brief_result.data, CreateDucktyperBriefResponse)
        brief = brief_result.data.brief
        artifact, manifest = _synthetic_render(brief)
        channel_plan = _channel_plan(brief)
        validation_result = invoke_sync(
            registry.get("creator.validate_delivery@1.0.0"),
            ValidateDeliveryRequest(
                brief=brief,
                artifact=artifact,
                manifest=manifest,
                publication=profile,
                synthesis=synthesis,
                channel_plan=channel_plan,
                created_at=NOW,
            ),
            make_context(capability_name="validate_delivery"),
        )
        assert isinstance(validation_result.data, ValidateDeliveryResponse)
        review = validation_result.data.review
        distribution_result = invoke_sync(
            registry.get("creator.prepare_distribution@1.0.0"),
            PrepareDistributionRequest(
                brief=brief,
                artifact=artifact,
                manifest=manifest,
                review=review,
                channel_plan=channel_plan,
                created_at=NOW,
            ),
            make_context(capability_name="prepare_distribution"),
        )
        assert isinstance(distribution_result.data, PrepareDistributionResponse)
        briefs.append(brief)
        artifacts.append(artifact)
        manifests.append(manifest)
        reviews.append(review)
        operations.extend(distribution_result.data.operations)

    metric_rows, metric_queries = _metric_fixture(tuple(operations))
    metrics_source = FakeMetricsSource(metric_rows)
    objective_by_id = {item.publication_id: item.objective for item in objectives()}
    assessments: list[DailyPerformanceAssessment] = []
    for profile in profiles:
        result = invoke_sync(
            registry.get("creator.assess_performance@1.0.0"),
            AssessPerformanceRequest(
                publication=profile,
                queries=metric_queries[profile.publication_id],
                objective=objective_by_id[profile.publication_id],
                created_at=NOW,
            ),
            make_context(
                capability_name="assess_performance",
                services={"creator.metrics_source": metrics_source},
            ),
        )
        assert isinstance(result.data, AssessPerformanceResponse)
        assessments.append(result.data.assessment)

    return DogfoodSnapshot(
        profiles=profiles,
        syntheses=tuple(syntheses),
        plan=plan,
        briefs=tuple(briefs),
        artifacts=tuple(artifacts),
        manifests=tuple(manifests),
        reviews=tuple(reviews),
        operations=tuple(operations),
        assessments=tuple(assessments),
        evidence_calls=tuple(evidence_source.calls),
        metrics_calls=tuple(metrics_source.calls),
    )
