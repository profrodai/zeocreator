# Capability catalog

All capability IDs are stable at `1.0.0`. Each manifest includes JSON request
and response schemas, effects, requirements, examples, projections, and typed
error codes.

| Capability | Input focus | Output | Effect |
|---|---|---|---|
| `creator.research_synthesis@1.0.0` | Publication, research window, evidence queries | `ResearchSynthesis` | Read |
| `creator.extract_editorial_signals@1.0.0` | Normalized source observations | Editorial signals | None |
| `creator.update_story_revisions@1.0.0` | Signals and prior immutable revisions | Story revisions | None |
| `creator.build_story_dossier@1.0.0` | One story revision and prior coverage | `StoryDossier` | None |
| `creator.plan_editorial_agenda@1.0.0` | Dossiers, desk, coverage window, slots | `EditorialAgenda` | None |
| `creator.plan_edition@1.0.0` | Agenda, publication window, update policy | `EditionPlan` | None |
| `creator.plan_content_portfolio@1.0.0` | Syntheses, objectives, history, requirements, planning window | `ContentPortfolioPlan` | None |
| `creator.create_content_brief@1.0.0` | Assignment, synthesis, profile, creative direction | `ContentBrief` | None |
| `creator.identify_engagement_opportunities@1.0.0` | Conversation, persona, evidence, expiry | `EngagementOpportunity` | None |
| `creator.compose_commentary@1.0.0` | Opportunity and conversation | `CommentaryDraft` | None |
| `creator.review_commentary@1.0.0` | Draft, context, position and experience refs | `CommentaryReview` | None |
| `creator.plan_newsletter_issue@1.0.0` | Edition, dossiers, audience policy refs | `NewsletterIssuePlan` | None |
| `creator.compose_newsletter_issue@1.0.0` | Accepted issue plan and dossiers | HTML/plain-text draft | None |
| `creator.review_newsletter_issue@1.0.0` | Plan and draft | `NewsletterEditorialReview` | None |
| `creator.compose_news_article@1.0.0` | Article plan and frozen dossiers | `NewsArticleDraft` | None |
| `creator.review_news_article@1.0.0` | Plan, draft and qualified-human review ref | `EditorialReview` | None |
| `creator.prepare_correction@1.0.0` | Reviewed article and corrected claims | `CorrectionNotice` | None |
| `creator.validate_delivery@1.0.0` | Brief, artifact manifest, profile, synthesis, channel plan | `DeliveryReviewBundle` | None |
| `creator.prepare_distribution@1.0.0` | Accepted review and exact channel plan | Publication proposals | None |
| `creator.assess_performance@1.0.0` | Profile, metric queries, objective | Performance assessment | Read |

| `creator.plan_email_campaign@1.0.0` | Supplied email artifacts | EmailCampaignPlan | Input-only read |
| `creator.plan_email_sequence@1.0.0` | Supplied email artifacts | EmailSequencePlan | Input-only read |
| `creator.plan_email_message@1.0.0` | Supplied email artifacts | EmailMessagePlan | Input-only read |
| `creator.compose_email_message@1.0.0` | Supplied email artifacts | EmailMessageDraft | Input-only read |
| `creator.review_email_message@1.0.0` | Supplied email artifacts | EmailEditorialReview | Input-only read |
| `creator.prepare_email_delivery@1.0.0` | Supplied email artifacts | EmailDeliveryPackage | Input-only read |
| `creator.assess_email_program@1.0.0` | Supplied email artifacts | EmailProgramAssessment | Input-only read |

Use `zeo-creator capabilities --json` for canonical manifests or
`zeo-creator capabilities --projection openai` for function-tool projections.

Zeocore 0.9 requires every manifest to carry at least one effect kind. Pure
transformations therefore conservatively declare `read`; the email family also
carries the `pure` tag and has no required acquisition services or network access. This
compatibility boundary can be removed if Zeocore gains an explicit pure effect.

Composition, scheduling, retries, approval waits, and effect authorization are
runtime concerns; the package deliberately exposes no monolithic workflow.

The query-based research and performance v1 capabilities are retained for legacy
compatibility. Canonical email assessment uses already-collected observations in
`assess_email_program`; never inject a live connector into that capability.
