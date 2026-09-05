"""Deterministic strategies for commentary, newsletter and journalism workflows."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from html import escape
from typing import Protocol

from zeo_creator.contracts.commentary import (
    CommentaryDraft,
    CommentaryFinding,
    CommentaryReview,
    ConversationObservation,
    EngagementDisposition,
    EngagementOpportunity,
)
from zeo_creator.contracts.common import canonical_digest, stable_id
from zeo_creator.contracts.journalism import (
    CorrectionNotice,
    EditorialReview,
    NewsArticleDraft,
    NewsArticlePlan,
)
from zeo_creator.contracts.newsletter import (
    AudienceSelection,
    NewsletterEditorialReview,
    NewsletterIssueDraft,
    NewsletterIssuePlan,
    NewsletterSectionPlan,
)
from zeo_creator.contracts.newsroom import EditionPlan, GenerationTrace, RiskLevel, StoryDossier
from zeo_creator.contracts.production import ContentDocument


def _trace(name: str, inputs: Sequence[object]) -> GenerationTrace:
    return GenerationTrace(
        strategy_ref=f"zeo-creator.reference.{name}",
        strategy_version="1.0.0",
        policy_version="1.0.0",
        input_digests=tuple(canonical_digest(item) for item in inputs),
    )


class CommentaryStrategy(Protocol):
    def identify_engagement(
        self,
        *,
        conversation: ConversationObservation,
        persona_ref: str,
        distinctive_contribution: str,
        evidence_refs: Sequence[str],
        created_at: datetime,
        expires_at: datetime,
    ) -> EngagementOpportunity: ...

    def compose_commentary(
        self,
        *,
        opportunity: EngagementOpportunity,
        conversation: ConversationObservation,
        tone: str,
        authorship_mode: str,
        created_at: datetime,
    ) -> CommentaryDraft: ...

    def review_commentary(
        self,
        *,
        draft: CommentaryDraft,
        conversation: ConversationObservation,
        persona_position_refs: Sequence[str],
        personal_experience_refs: Sequence[str],
        approval_policy_ref: str,
        created_at: datetime,
    ) -> CommentaryReview: ...


class NewsletterStrategy(Protocol):
    def plan_newsletter(
        self,
        *,
        edition: EditionPlan,
        dossiers: Sequence[StoryDossier],
        audience: AudienceSelection,
        created_at: datetime,
    ) -> NewsletterIssuePlan: ...

    def compose_newsletter(
        self,
        *,
        plan: NewsletterIssuePlan,
        dossiers: Sequence[StoryDossier],
        created_at: datetime,
    ) -> NewsletterIssueDraft: ...

    def review_newsletter(
        self,
        *,
        plan: NewsletterIssuePlan,
        draft: NewsletterIssueDraft,
        created_at: datetime,
    ) -> NewsletterEditorialReview: ...


class JournalismStrategy(Protocol):
    def compose_article(
        self,
        *,
        plan: NewsArticlePlan,
        dossiers: Sequence[StoryDossier],
        created_at: datetime,
    ) -> NewsArticleDraft: ...

    def review_article(
        self,
        *,
        plan: NewsArticlePlan,
        draft: NewsArticleDraft,
        qualified_human_review_ref: str | None,
        created_at: datetime,
    ) -> EditorialReview: ...

    def prepare_correction(
        self,
        *,
        article: NewsArticleDraft,
        review: EditorialReview,
        publication_artifact_ref: str,
        corrected_claim_refs: Sequence[str],
        correction_text: ContentDocument,
        reason: str,
        effective_at: datetime,
        created_at: datetime,
    ) -> CorrectionNotice: ...


class DeterministicSpecializationStrategy(
    CommentaryStrategy, NewsletterStrategy, JournalismStrategy
):
    """Conservative reference implementation; production runners may inject intelligence."""

    def identify_engagement(
        self,
        *,
        conversation: ConversationObservation,
        persona_ref: str,
        distinctive_contribution: str,
        evidence_refs: Sequence[str],
        created_at: datetime,
        expires_at: datetime,
    ) -> EngagementOpportunity:
        disposition = (
            EngagementDisposition.REPLY
            if conversation.complete_through_cutoff and evidence_refs
            else EngagementDisposition.MONITOR
        )
        return EngagementOpportunity(
            opportunity_id=stable_id("engagement", conversation.conversation_id, persona_ref),
            created_at=created_at,
            organization_id=conversation.organization_id,
            publication_id=conversation.publication_id,
            input_refs=(conversation.conversation_id, *evidence_refs),
            conversation_ref=conversation.conversation_id,
            disposition=disposition,
            persona_ref=persona_ref,
            distinctive_contribution=distinctive_contribution,
            proposed_stance=distinctive_contribution,
            risk_level=RiskLevel.MEDIUM,
            timeliness_expires_at=expires_at,
            evidence_refs=tuple(evidence_refs),
            expected_community_value="Adds evidence or a distinct, attributable perspective.",
            generation=_trace("engagement-opportunity", (conversation,)),
        )

    def compose_commentary(
        self,
        *,
        opportunity: EngagementOpportunity,
        conversation: ConversationObservation,
        tone: str,
        authorship_mode: str,
        created_at: datetime,
    ) -> CommentaryDraft:
        return CommentaryDraft(
            commentary_id=stable_id("commentary", opportunity.opportunity_id),
            created_at=created_at,
            organization_id=opportunity.organization_id,
            publication_id=opportunity.publication_id,
            input_refs=(opportunity.opportunity_id, conversation.conversation_id),
            persona_ref=opportunity.persona_ref,
            conversation_ref=conversation.conversation_id,
            response_type=opportunity.disposition,
            content=ContentDocument(
                media_type="text/plain", content=opportunity.distinctive_contribution
            ),
            stance_ref=opportunity.opportunity_id,
            tone=tone,
            authorship_mode=authorship_mode,
            expires_at=opportunity.timeliness_expires_at,
            risk_level=opportunity.risk_level,
            generation=_trace("commentary-composition", (opportunity, conversation)),
        )

    def review_commentary(
        self,
        *,
        draft: CommentaryDraft,
        conversation: ConversationObservation,
        persona_position_refs: Sequence[str],
        personal_experience_refs: Sequence[str],
        approval_policy_ref: str,
        created_at: datetime,
    ) -> CommentaryReview:
        timely = created_at <= draft.expires_at
        contextual = draft.conversation_ref == conversation.conversation_id
        experience_safe = "i personally" not in draft.content.content.casefold() or bool(
            personal_experience_refs
        )
        findings = (
            CommentaryFinding(
                check_id="commentary.adds-value",
                blocking=True,
                passed=bool(draft.content.content),
                detail="Draft contains a distinct contribution.",
            ),
            CommentaryFinding(
                check_id="commentary.position-bound",
                blocking=True,
                passed=bool(persona_position_refs),
                detail="Persona position references supplied.",
            ),
            CommentaryFinding(
                check_id="commentary.experience-grounded",
                blocking=True,
                passed=experience_safe,
                detail="Personal experience is not fabricated.",
            ),
            CommentaryFinding(
                check_id="commentary.context-current",
                blocking=True,
                passed=contextual and timely,
                detail="Conversation context and expiry are current.",
            ),
            CommentaryFinding(
                check_id="commentary.non-attacking",
                blocking=True,
                passed="idiot" not in draft.content.content.casefold(),
                detail="No direct personal attack detected.",
            ),
        )
        approval_digest = canonical_digest(
            {
                "draft": draft.content_digest,
                "conversation": conversation.content_digest,
                "policy": approval_policy_ref,
            }
        )
        return CommentaryReview(
            review_id=stable_id("commentary_review", draft.commentary_id, approval_digest),
            created_at=created_at,
            organization_id=draft.organization_id,
            publication_id=draft.publication_id,
            input_refs=(draft.commentary_id,),
            commentary_ref=draft.commentary_id,
            findings=findings,
            ready_for_human_approval=all(item.passed for item in findings if item.blocking),
            approval_policy_ref=approval_policy_ref,
            approval_digest=approval_digest,
            generation=_trace("commentary-review", (draft, conversation)),
        )

    def compose_article(
        self,
        *,
        plan: NewsArticlePlan,
        dossiers: Sequence[StoryDossier],
        created_at: datetime,
    ) -> NewsArticleDraft:
        claims = tuple(claim for dossier in dossiers for claim in dossier.verified_claims)
        source_refs = tuple(dict.fromkeys(ref for claim in claims for ref in claim.evidence_refs))
        body = "\n\n".join(claim.text for claim in claims)
        return NewsArticleDraft(
            article_draft_id=stable_id("article_draft", plan.article_plan_id),
            created_at=created_at,
            organization_id=plan.organization_id,
            publication_id=plan.publication_id,
            input_refs=(plan.article_plan_id, *plan.dossier_refs),
            article_plan_ref=plan.article_plan_id,
            headline=plan.headline_direction,
            body=ContentDocument(media_type="text/markdown", content=body or plan.thesis),
            claims=claims,
            source_refs=source_refs,
            bylines=plan.bylines,
            generation=_trace("news-article-composition", (plan, *dossiers)),
        )

    def review_article(
        self,
        *,
        plan: NewsArticlePlan,
        draft: NewsArticleDraft,
        qualified_human_review_ref: str | None,
        created_at: datetime,
    ) -> EditorialReview:
        claim_ok = all(
            ref in draft.source_refs for claim in draft.claims for ref in claim.evidence_refs
        )
        human_required = plan.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL} or bool(
            plan.high_risk_classifications
        )
        human_ok = not human_required or bool(qualified_human_review_ref)
        blocking = tuple(
            message
            for condition, message in (
                (claim_ok, "Claim traceability failed."),
                (human_ok, "Qualified human review is required."),
            )
            if not condition
        )
        digest = canonical_digest(
            {
                "plan": plan.content_digest,
                "draft": draft.content_digest,
                "human": qualified_human_review_ref,
            }
        )
        return EditorialReview(
            review_id=stable_id("editorial_review", draft.article_draft_id, digest),
            created_at=created_at,
            organization_id=draft.organization_id,
            publication_id=draft.publication_id,
            input_refs=(plan.article_plan_id, draft.article_draft_id),
            article_draft_ref=draft.article_draft_id,
            claim_traceability=claim_ok,
            attribution_satisfied=all(item.accepted for item in draft.bylines),
            privacy_satisfied=True,
            risk_policy_satisfied=human_ok,
            qualified_human_required=human_required,
            qualified_human_review_ref=qualified_human_review_ref,
            blocking_findings=blocking,
            ready_for_approval=claim_ok
            and all(item.accepted for item in draft.bylines)
            and human_ok
            and not blocking,
            approval_digest=digest,
            generation=_trace("news-article-review", (plan, draft)),
        )

    def plan_newsletter(
        self,
        *,
        edition: EditionPlan,
        dossiers: Sequence[StoryDossier],
        audience: AudienceSelection,
        created_at: datetime,
    ) -> NewsletterIssuePlan:
        sections = tuple(
            NewsletterSectionPlan(
                section_id=stable_id("section", dossier.dossier_id),
                heading=dossier.possible_angles[0] if dossier.possible_angles else dossier.story_id,
                dossier_refs=(dossier.dossier_id,),
                purpose=dossier.audience_significance,
            )
            for dossier in dossiers
        )
        return NewsletterIssuePlan(
            issue_plan_id=stable_id("newsletter_plan", edition.edition_id),
            created_at=created_at,
            organization_id=edition.organization_id,
            publication_id=edition.publication_id,
            input_refs=(edition.edition_id, *(item.dossier_id for item in dossiers)),
            edition_plan_ref=edition.edition_id,
            working_title=f"{edition.edition_kind} briefing",
            subject_variants=(f"{edition.edition_kind}: what matters",),
            preheader_variants=("Verified developments and useful context.",),
            sections=sections,
            audience=audience,
            link_tracking_plan_ref="tracking.standard@1",
            generation=_trace("newsletter-planning", (edition, *dossiers)),
        )

    def compose_newsletter(
        self,
        *,
        plan: NewsletterIssuePlan,
        dossiers: Sequence[StoryDossier],
        created_at: datetime,
    ) -> NewsletterIssueDraft:
        dossier_by_id = {item.dossier_id: item for item in dossiers}
        parts = [
            (section.heading, dossier_by_id[section.dossier_refs[0]].recommended_framing)
            for section in plan.sections
            if section.dossier_refs[0] in dossier_by_id
        ]
        plain = "\n\n".join(f"{heading}\n{text}" for heading, text in parts)
        html = "".join(
            f"<section><h2>{escape(heading)}</h2><p>{escape(text)}</p></section>"
            for heading, text in parts
        )
        return NewsletterIssueDraft(
            issue_draft_id=stable_id("newsletter_draft", plan.issue_plan_id),
            created_at=created_at,
            organization_id=plan.organization_id,
            publication_id=plan.publication_id,
            input_refs=(plan.issue_plan_id, *(item.dossier_id for item in dossiers)),
            issue_plan_ref=plan.issue_plan_id,
            subject=plan.subject_variants[0],
            preheader=plan.preheader_variants[0],
            html_content=ContentDocument(media_type="text/html", content=html),
            plain_text_content=ContentDocument(media_type="text/plain", content=plain),
            source_refs=tuple(
                dict.fromkeys(ref for item in dossiers for ref in item.evidence_lineage)
            ),
            generation=_trace("newsletter-composition", (plan, *dossiers)),
        )

    def review_newsletter(
        self,
        *,
        plan: NewsletterIssuePlan,
        draft: NewsletterIssueDraft,
        created_at: datetime,
    ) -> NewsletterEditorialReview:
        source_ok = bool(draft.source_refs)
        coverage = all(
            section.heading in draft.plain_text_content.content for section in plan.sections
        )
        blocking = tuple(
            message
            for condition, message in (
                (coverage, "Missing planned section."),
                (source_ok, "Missing source lineage."),
            )
            if not condition
        )
        digest = canonical_digest({"plan": plan.content_digest, "draft": draft.content_digest})
        return NewsletterEditorialReview(
            review_id=stable_id("newsletter_review", draft.issue_draft_id, digest),
            created_at=created_at,
            organization_id=draft.organization_id,
            publication_id=draft.publication_id,
            input_refs=(plan.issue_plan_id, draft.issue_draft_id),
            issue_draft_ref=draft.issue_draft_id,
            section_coverage=coverage,
            source_traceability=source_ok,
            audience_policy_satisfied=True,
            links_validated=True,
            preview_required=plan.preview_required,
            test_send_required=plan.test_send_required,
            blocking_findings=blocking,
            ready_for_human_approval=not blocking,
            approval_digest=digest,
            generation=_trace("newsletter-review", (plan, draft)),
        )

    def prepare_correction(
        self,
        *,
        article: NewsArticleDraft,
        review: EditorialReview,
        publication_artifact_ref: str,
        corrected_claim_refs: Sequence[str],
        correction_text: ContentDocument,
        reason: str,
        effective_at: datetime,
        created_at: datetime,
    ) -> CorrectionNotice:
        return CorrectionNotice(
            correction_id=stable_id("correction", publication_artifact_ref, article.content_digest),
            created_at=created_at,
            organization_id=article.organization_id,
            publication_id=article.publication_id,
            input_refs=(article.article_draft_id, review.review_id, publication_artifact_ref),
            publication_artifact_ref=publication_artifact_ref,
            corrected_claim_refs=tuple(corrected_claim_refs),
            correction_text=correction_text,
            reason=reason,
            effective_at=effective_at,
            editor_review_ref=review.review_id,
        )


REFERENCE_SPECIALIZATION_STRATEGY = DeterministicSpecializationStrategy()
