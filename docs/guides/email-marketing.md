# Email marketing

<!-- Reviewed 2026-09-07. Email v2 replaces the v1 preparation API; original schemas remain archived. -->

Creator designs and evaluates email programs. Zeocore owns the public provider
contracts and lowering; ZEOconnect executes provider effects; Runtime owns
approvals, audience authorization, schedules and retries; Newsroom owns durable
publication history and observations. Any third-party host can implement these
responsibilities without importing private ZEO packages.

## Concepts and contracts

| Concept | Public artifact | Meaning |
|---|---|---|
| Campaign | `EmailCampaignPlan` | Bounded objective, audience, CTAs, attribution and stopping conditions |
| Campaign release | `EmailCampaignRelease` | Exact campaign, message and sequence membership, CTAs and measurement plan without cyclic digests |
| Sequence | `EmailSequencePlan` | Ordered immutable revision with explicit policy references and delays |
| Step | `EmailSequenceStepPlan` | Stable identity/ordinal, exact message-plan digest, admitted-event delay and freshness |
| Message | `EmailMessagePlan`, `EmailMessageDraft` | Editorial intent and exact subject, preheader, HTML, plain text and manifests |
| Audience intent | `AudienceIntent` | Segments, inclusions/exclusions, consent, suppression, geography, frequency and cross-publication policy |
| Audience snapshot | `AudienceSnapshotSummary` | Opaque runtime-supplied selection with digest, counts, provider/connection, expiry and drift state |
| Review | `EmailEditorialReview` | Structural checks plus supplied evidence, ready only for human approval |
| Delivery | `EmailDeliveryPackage` | Exact creative material and approval target digest |
| Effect intent | `ProposedEmailOperation` | Separate proposal referring to a public Zeocore `CapabilityId` and contract digest |
| Learning | `EmailMetricObservation`, `EmailProgramAssessment` | Receipt-linked aggregate input and qualified conclusions |

A newsletter is a periodic editorial issue sent as a one-off broadcast. A campaign
need not correspond to a provider-side campaign object. A lifecycle program is
the broader journey containing entry/exit/conversion/suppression policies; v2 can
represent it through one linear sequence. HubSpot Sales Sequences are outside
this model; the integration target is HubSpot Marketing.

## Invoke the nine capabilities

Use the standard capability registry and typed requests from
`zeo_creator.capabilities.email_marketing`. All nine capabilities declare only
Zeocore's conservative `read` effect, carry a `pure` tag, and have no required
acquisition services or network access:

```text
creator.plan_email_campaign@2.0.0
creator.finalize_email_campaign@2.0.0
creator.propose_email_operation@2.0.0
creator.plan_email_sequence@2.0.0
creator.plan_email_message@2.0.0
creator.compose_email_message@2.0.0
creator.review_email_message@2.0.0
creator.prepare_email_delivery@2.0.0
creator.assess_email_program@2.0.0
```

Composition accepts an optional `creator.email_strategy` implementing
`EmailCreativeStrategy.compose(plan, sections, created_at)`. The strategy receives
only supplied editorial inputs; it is not passed `ToolContext`, credentials or a
connector. Its returned scope, input digests and artifact integrity are checked.
The deterministic strategy copies curated source sections into matching HTML and
plain text and adds the declared CTAs and compliance footer.

## Review and readiness

Review covers source lineage, voice, audience policy, subject/body consistency,
HTML/plain-text consistency, links, CTAs, personalization, accessibility,
footer/unsubscribe, consent/suppression, claims, preview and test requirements.

The deterministic reviewer compares visible HTML text with plain text and rejects
unlisted markup/attributes. This intentionally conservative subset supports text
and descriptive links; richer email templates need explicit future contract work
and qualified render validation. Syntactically valid links do not prove remote
availability. Voice, subject/body consistency, accessibility, link validation and claim review
require supplied `EmailReviewEvidence` bound to the exact draft and an expiry.
The parser checks anchor labels against their declared CTA targets and the unsubscribe target. Exactly one CTA must be primary; sequence intent selects that CTA regardless of position. Missing evidence produces `human_needed`; it cannot be upgraded by a boolean
readiness claim. Delivery preparation repeats the checks at preparation time.

Tokens remain symbolic declarations with missing-value behavior `refuse`.
Undeclared or malformed placeholders always block readiness. Declared placeholders
require externally supplied, exact-draft `personalization` review evidence proving
resolution, followed by successful preview/test receipts with structured `EmailLoweringEvidence`. Each binds an issuer, receipt reference/digest, contract identity/digest, provider/connection/account, connector revision, lowering profile, sender, draft, template mapping, submitted/observed/rendered digests, token coverage, missing-value behavior and covered snapshot. A boolean alone is insufficient. Without that evidence they remain unresolved and
blocked. Values never enter Creator: the host resolves them outside this package
and refuses missing required values. Evidence authenticity and complete snapshot
coverage authenticity must be verified by the runtime under the public lowering contract. Creator checks the supplied coverage and context equalities. The fake renderer refuses all personalization tokens; it never claims copied placeholders are resolved.

Production preparation requires a current nonempty, unchanged audience snapshot,
matching consent/suppression digests, ready review, successful preview and a test
receipt for a separate test audience. A preview may bind the exact production snapshot; only a test-send audience must differ. Test preparation uses a test-only snapshot
and does not require a previous test-send receipt. Schedule intent must be in the
future and within snapshot validity. Runtime must recheck freshness and drift at
dispatch; Creator never evaluates a trigger or schedules work.

## Exact approval and separate effects

`EmailDeliveryPackage.material` includes the full draft and its binding, subject,
preheader, HTML/plain-text and manifest digests, sender/reply-to references,
compliance, audience summary, tracking, schedule intent, campaign/sequence revision,
review and preview/test evidence, campaign release, execution context and template mapping digest. `approval_digest` is the RFC 8785 digest of that
material. It is an approval target, not an approval receipt.

An operation proposal separately binds editorial effect intent, public Zeocore
operation identity/version/schema digest, delivery reference and approval digest,
sequence revision, exact audience, remote target/revision and migration policy
where applicable. Its own approval digest is RFC 8785 over `{material, idempotency_key}`. The execution context inside material namespaces the logical operation. Changing a retry key requires new approval and creates a different receipt identity.
Use separate identities and approvals for create/update draft, test send, schedule,
immediate broadcast, activate, enrol, pause, cancel, retire and migrate-existing-enrollees. Activation does
not enrol anyone; test success does not approve production; later or larger
audiences require new proposals. Remote update/cancel/pause/retire intents require
an opaque target, observed remote revision digest and normalized `EmailRemoteReceipt` binding issuer, operation, release and exact execution context. Activation also requires the exact provisioned sequence receipt. Cancellation accepts only a scheduling receipt; update accepts only a draft receipt.

`creator.propose_email_operation@2.0.0` and `services.email_marketing.propose_operation` inspect the actual release, package and sequence. They re-run delivery preparation, enforce exact package/audience/context bindings and schedule semantics, and check enrolment policy and both proposal/resolution times against the enrolment window. The capability does not
certify support, inspect a provider account, validate a human authorization or
execute anything. At the handoff the host must resolve every digest-bound artifact,
check stored revision uniqueness and the receipt-to-provider-object mapping, authenticate evidence issuers and contract digests, recheck audience authorization/freshness/drift at dispatch, resolve the public operation
contract, refuse unsupported semantics, and obtain fresh effect authority.

A sequence revision has unique stable step IDs and contiguous ordinals. Editing
through `plan_email_sequence` requires the previous revision and increments it.
Existing enrollees retain their original revision by default. Migration requires
a separate `migrate_existing_enrollees` effect containing source and target sequence revisions, an exact enrollee snapshot, an explicit policy, and a retain/skip/restart disposition for every source step. The source receipt and target previous-revision binding must agree. Activation and enrolment reject migration material. Runtime determines current remote state and grants separate authority.
Conditional graphs, CRM mutations, lead scoring and arbitrary workflows are
outside the linear v2 model.

## Publication isolation and data handling

All new references include organization, publication, revision and digest. Mixing
publications in a request, nested reference, review, snapshot or assessment is
rejected. Shared provider accounts and source material confer no audience-sharing
permission. Cross-promotion requires an explicit publication-scoped policy and a
separately resolved snapshot. Caller-supplied profiles hold Rasa, Prof Rod and
Zero Employee strategy outside the package.

Contracts have no subscriber email/name/contact-ID/property fields, reject extra
fields, and reject email-address-shaped prose. This is a structural guard, not a
universal PII detector: hosts must prevent subscriber records, private identities,
tracking values and provider response bodies from entering editorial text or
opaque references. Links use HTTPS without userinfo. Ordinary query parameters and fragments (including video IDs) are allowed; known tracking/subscriber parameter families are refused. This denylist is not a universal detector of encoded private data. Tracking remains a policy reference applied outside Creator.

Capability failures return a fixed safe code and an allowlisted refusal reason for known domain errors. Unknown validation and injected exception bodies remain opaque.
Pydantic's raw `ValidationError.errors()` can contain original input; never persist
it. Validate before durable logging and retain only safe error classifications.
Digest equality proves integrity, not consent, evidence authenticity, publication
ownership or human approval; those attestations are host responsibilities.

## Offline proof

```console
uv run python examples/email_marketing.py
# After installing the wheel, outside the source checkout:
python -m zeo_creator.reference.email_workflow
```

The compact `email_workflow` runs all nine capabilities for three isolated publications,
with four messages and one three-step sequence each. `examples/email_marketing.py`
and installed `python -m zeo_creator.reference.email_program_suite` widen this to eight
separate bounded programs: Rasa weekly newsletter and learning nurture; Prof Rod weekly
newsletter, lead-magnet welcome and membership; Zero Employee weekly newsletter,
orientation and product interest. The caller supplies sanitized identities and objectives;
these examples contain no private brand strategy. Every program includes matching
HTML/plain text, a campaign release, test and production preparation, and a partial assessment.
The effect-family harness exercises all eleven separate effect intents for each program,
including a supplied fake provisioning receipt and an explicit revision migration.
These are orchestration proofs, not editorial or provider acceptance verdicts.

`SimulatedEmailHost` demonstrates logical idempotency, conflicting reuse refusal
and ambiguous-outcome reconciliation without resubmission. It is a process-local
conformance harness, not a production journal. Provider transformations produce
`needs_review`. No account, credential, recipient identity, network or live effect
is involved, and the example's simulated approvals are not human approvals.

Schemas are available through `zeo-creator contracts export`. Wheel resources under
`zeo_creator/reference_artifacts` include examples, request/response schemas,
canonical digest vectors and documentation. JavaScript independently verifies the
Python-generated canonical vector bytes and SHA-256 values.

## Public Zeocore integration dependency

The pinned public Zeocore 0.9.0 supplies `CapabilityId` and capability manifests,
but not the commissioned neutral email effect vocabulary, lowering contracts and
receipt family. Creator therefore references caller-selected public operation
identities; it does not define executable provider operations or copy HubSpot/Kit
request bodies. The example uses clearly marked `example.email` identities.

Live interoperability is unverified until the public Zeocore contract is available
and conformance is run against it. A production host must not treat the fake shapes
or example operation IDs as a connector protocol. Lowering must record Creator
artifact/revision/digest, connector revision, submitted and observed payload
digests, transformations/refusals, remote references, idempotency and safe ambiguity.
Unsupported sequence semantics require refusal. Ambiguous results require
reconciliation before any retry.

## Assessment boundaries

Each assessment persists its expected metric set and exact observation window. Every
observation must bind a confirmed normalized operation receipt, provider/connection and
campaign release. An assessment accepts a single aggregate cohort and does not pool
providers or connections. Units are `count`, `rate`, or `currency`; rates must equal their
explicit numerator/denominator. Missing metrics, conflicting values, incomplete coverage
or unreliable observations prevent qualified completeness. Conclusions report supplied
values and qualifications without claiming causal lift. Qualitative campaign stopping
conditions are surfaced as `human_needed`; Creator neither evaluates runtime consent
state nor executes a stop.

## Email v1 migration

This package is `0.3.0.dev0`. The seven email `@1.0.0` capabilities are retired from the
registry because their input shapes cannot enforce the corrected bindings. The current
nine capabilities use `@2.0.0` and distinct projection names. Email artifact schemas use
`2.0.0`; every published email v1 schema remains available unchanged for audit/import.
Rebuild campaign intent, message and sequence plans under v2, finalize a release, acquire
fresh bound lowering/review evidence, prepare delivery with explicit execution context,
and obtain new effect approval. No v1 approval is carried forward. The twenty original
non-email capabilities retain their IDs and schemas.

## Newsletter compatibility

Existing `AudienceSelection`, `NewsletterIssuePlan`, newsletter draft/review and
generic publication/performance v1 schemas remain byte-for-byte unchanged.
`PlanEmailMessageRequest.newsletter` provides an explicit specialization bridge:
select an existing subject and preheader variant, retain the issue's audience and
consent/suppression references, and supply the new message directions, compliance
and scoped evidence. The resulting plan binds the original newsletter revision.
No old schema is silently reinterpreted.
