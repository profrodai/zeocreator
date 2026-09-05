"""Neutral examples for commentary, newsletter and journalism capabilities."""

from __future__ import annotations

from datetime import timedelta

from zeo_creator.capabilities._newsroom_examples import NOW, agenda, dossier
from zeo_creator.contracts.commentary import (
    CommentaryDraft,
    ConversationObservation,
    EngagementOpportunity,
)
from zeo_creator.contracts.journalism import BylineAssignment, NewsArticleDraft, NewsArticlePlan
from zeo_creator.contracts.newsletter import (
    AudienceSelection,
    NewsletterIssueDraft,
    NewsletterIssuePlan,
)
from zeo_creator.contracts.newsroom import EditionPlan, RiskLevel
from zeo_creator.contracts.production import ContentDocument
from zeo_creator.services.editorial_kernel import DeterministicEditorialStrategy
from zeo_creator.services.specializations import REFERENCE_SPECIALIZATION_STRATEGY


def conversation() -> ConversationObservation:
    return ConversationObservation(
        conversation_id="conversation_example",
        created_at=NOW,
        organization_id="org_example",
        publication_id="publication-a.example",
        provider_kind="community.example",
        original_post_ref="post_example",
        author_ref="author_example",
        author_context="A practitioner asking about evidence quality.",
        community_context="A technical creator community.",
        content=ContentDocument(
            media_type="text/plain", content="How should evidence be preserved?"
        ),
        engagement_snapshot={"replies": 3},
        related_story_refs=(dossier().story_id,),
        retrieved_at=NOW,
        retrieval_cutoff=NOW,
        complete_through_cutoff=True,
    )


def opportunity() -> EngagementOpportunity:
    return REFERENCE_SPECIALIZATION_STRATEGY.identify_engagement(
        conversation=conversation(),
        persona_ref="persona_example",
        distinctive_contribution="Preserve immutable source references before synthesis.",
        evidence_refs=dossier().evidence_lineage,
        created_at=NOW,
        expires_at=NOW + timedelta(hours=4),
    )


def commentary_draft() -> CommentaryDraft:
    return REFERENCE_SPECIALIZATION_STRATEGY.compose_commentary(
        opportunity=opportunity(),
        conversation=conversation(),
        tone="constructive",
        authorship_mode="human-reviewed",
        created_at=NOW,
    )


def edition() -> EditionPlan:
    return DeterministicEditorialStrategy().plan_edition(
        agenda=agenda(),
        edition_kind="newsletter.issue",
        publication_window=agenda().coverage_window,
        update_policy_ref="updates.immutable-issue@1",
        human_editor_requirements=("newsletter-editor",),
        created_at=NOW,
        revision=1,
    )


def audience() -> AudienceSelection:
    return AudienceSelection(
        segment_refs=("audience.example",),
        selection_policy_ref="audience.selection@1",
        suppression_policy_ref="audience.suppression@1",
        consent_policy_ref="audience.consent@1",
    )


def newsletter_plan() -> NewsletterIssuePlan:
    return REFERENCE_SPECIALIZATION_STRATEGY.plan_newsletter(
        edition=edition(), dossiers=(dossier(),), audience=audience(), created_at=NOW
    )


def newsletter_draft() -> NewsletterIssueDraft:
    return REFERENCE_SPECIALIZATION_STRATEGY.compose_newsletter(
        plan=newsletter_plan(), dossiers=(dossier(),), created_at=NOW
    )


def article_plan() -> NewsArticlePlan:
    item = dossier()
    return NewsArticlePlan(
        article_plan_id="article_plan_example",
        created_at=NOW,
        organization_id=item.organization_id,
        publication_id=item.publication_id,
        input_refs=(item.dossier_id,),
        dossier_refs=(item.dossier_id,),
        headline_direction="A verified public update",
        thesis="The update changes how operators preserve evidence.",
        required_claim_refs=tuple(claim.claim_id for claim in item.verified_claims),
        bylines=(
            BylineAssignment(contributor_ref="reporter_example", role="reporter", accepted=True),
        ),
        risk_level=RiskLevel.MEDIUM,
        human_editor_policy_ref="editorial.general@1",
        generation=item.generation,
    )


def article_draft() -> NewsArticleDraft:
    return REFERENCE_SPECIALIZATION_STRATEGY.compose_article(
        plan=article_plan(), dossiers=(dossier(),), created_at=NOW
    )
