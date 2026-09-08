# Email marketing

<!-- Reviewed 2026-09-07. Email v3 closes the sequence lifecycle and observation population; v1/v2 preparation APIs are retired; original schemas remain archived. -->

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
the broader journey containing entry/exit/conversion/suppression policies; v3 can
represent it through one linear sequence. HubSpot Sales Sequences are outside
this model; the integration target is HubSpot Marketing.

## Invoke the nine capabilities

Use the standard capability registry and typed requests from
`zeo_creator.capabilities.email_marketing`. All nine capabilities declare only
Zeocore's conservative `read` effect, carry a `pure` tag, and have no required
acquisition services or network access:

```text
creator.plan_email_campaign@3.0.0
creator.finalize_email_campaign@3.0.0
creator.propose_email_operation@3.0.0
creator.plan_email_sequence@3.0.0
creator.plan_email_message@3.0.0
creator.compose_email_message@3.0.0
creator.review_email_message@3.0.0
creator.prepare_email_delivery@3.0.0
creator.assess_email_program@3.0.0
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
footer/unsubscribe, consent/suppression and claims. Preview and test evidence belong exclusively to delivery preparation. An editorial review can be ready before either external check exists; it does not claim they passed. Optional preview/test requirements do not block editorial review.

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
immediate broadcast, provision a sequence revision, activate, enrol, pause, cancel, retire and migrate-existing-enrollees. Activation does
not enrol anyone; test success does not approve production; later or larger
audiences require new proposals. Remote update/cancel/pause/retire intents require
an opaque target, observed remote revision digest and normalized `EmailRemoteReceipt` binding issuer, operation, release and exact execution context. Activation also requires the exact provisioned sequence receipt. Cancellation accepts only a scheduling receipt; update accepts only a draft receipt. Both bind `originating_operation` and `target_delivery`, and proposal preparation receives the complete originating proposal. The receipt operation and originating proposal must match exactly. Cancellation cannot name another delivery; draft updates may supply new content only for the same logical message as the target. Cancellation does not require an expired audience or old preview proof to become fresh again.

`creator.propose_email_operation@3.0.0` and `services.email_marketing.propose_operation` inspect the actual release, package and sequence. New content effects re-run delivery preparation; cancellation validates its historical target without reauthorizing a send. They enforce exact package/audience/context bindings and schedule semantics, and check enrolment policy and both proposal/resolution times against the enrolment window. The capability does not
certify support, inspect a provider account, validate a human authorization or
execute anything. At the handoff the host must resolve every digest-bound artifact,
check stored revision uniqueness and the receipt-to-provider-object mapping, authenticate evidence issuers and contract digests, recheck audience authorization/freshness/drift at dispatch, resolve the public operation
contract, refuse unsupported semantics, and obtain fresh effect authority.

A sequence revision has unique stable step IDs and contiguous ordinals. Editing
through `plan_email_sequence` requires the previous revision and increments it.
A separate `provision_sequence_revision` operation binds the exact revision and returns the normalized receipt required for activation. Provisioning cannot activate or enrol anyone. The fake lifecycle produces that receipt through an approved simulated operation; it is no longer supplied out of thin air. Existing enrollees retain their original revision by default. Migration requires
a separate `migrate_existing_enrollees` effect containing source and target sequence revisions, an exact enrollee snapshot, an explicit policy, and a retain/skip/restart disposition for every source step. The source receipt, provisioned target receipt, and target previous-revision binding must agree. Source kind/sequence and target kind/sequence/context/outcome are checked by direct contract construction as well as the service. Activation and enrolment reject migration material. Runtime determines current remote state and grants separate authority.
Conditional graphs, CRM mutations, lead scoring and arbitrary workflows are
outside the linear v3 model.

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
The effect-family harness exercises all twelve distinct intents through thirteen operations per program: it provisions both source and target sequence revisions and consumes the returned receipts during activation and migration. There are 104 approved simulated operations across eight programs.
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

Each assessment persists its expected metric set, exact observation window and an
`EmailMeasurementPopulation` containing the exact release and expected confirmed operation
receipts supplied by Runtime/Newsroom. Normalized receipts identify their delivery/message
or sequence. Completeness requires every released message to be represented and every
expected operation × metric cell to have qualified observations. Omitting an operation
for a second released message cannot make the release complete. Observations outside the
declared receipt population are rejected. Multiple operations for one message each need
coverage. The explicit aggregation policy is `per_operation_no_pooling`: values remain
per operation, without silently summing overlapping recipients or incompatible metrics.

Every observation must bind a confirmed normalized operation receipt, provider/connection
and campaign release. An assessment accepts a single aggregate cohort and does not pool
providers or connections. Units are `count`, `rate`, or `currency`; rates must equal their
explicit numerator/denominator. Missing population cells, conflicting values, incomplete
coverage or unreliable observations prevent qualified completeness. Qualitative stopping
conditions remain `human_needed`; Creator does not execute a runtime stop.

## Personalized test and production ordering

A personalized message requires audience-specific external evidence twice:

1. Resolve tokens against the test snapshot outside Creator and supply qualified lowering evidence.
2. Review using that test coverage, prepare the test package with its preview, and authorize a separate test operation.
3. Resolve and render against the production snapshot outside Creator using the same execution context and template mapping.
4. Produce a second editorial review using production coverage, then prepare production with its preview plus the prior test-send evidence.

Reusing the test review for production fails because its snapshot coverage differs.
The regression walkthrough supplies digest-bound external evidence without subscriber
values; it tests consumption of that evidence, not the truth of a provider rendering.
The fake renderer still refuses personalized drafts. Runtime must authenticate issuers
and verify the real mapping/render/snapshot coverage before authorizing effects.

## Email contract migration and release policy

The package is `0.4.0.dev0`; its nine email capabilities and durable email artifacts use
major version 3. Published email v1 and v2 schemas remain byte-for-byte available for
audit. Their preparation APIs are retired from discovery; the twenty original non-email
capabilities remain unchanged. This explicitly affirms the earlier email v1 retirement:
these email families existed only as unreleased development commits, and unsafe approvals
cannot carry forward. This is not a PyPI release or a claim of stable API compatibility.

Rebuild current campaign/message/sequence artifacts, finalize a release with a fully
coordinated CTA set, obtain current audience-specific proof evidence, provision sequence
revisions explicitly, and prepare new effect approvals. Mutations now require the originating
proposal and exact target delivery; assessments require a declared operation population.
The new required provenance fields and changed review semantics receive a new major version
rather than silently changing schemas already on main.

## Verification cost

`current()` validates each root graph once through Pydantic, including nested digests,
scopes and type constraints. It rejects silent normalization/repair and unsafe copies;
it does not recursively JSON-roundtrip every descendant again. There is no process-global
trust cache. The full eight-program example remains in `make verify`, executed in process
without a hardware-dependent per-example deadline. CI retains a fifteen-minute overall
job bound. Regression tests prove both the single-root validation path and rejection of
nested corruption with a recomputed ancestor digest.

## Newsletter compatibility

Existing `AudienceSelection`, `NewsletterIssuePlan`, newsletter draft/review and
generic publication/performance v1 schemas remain byte-for-byte unchanged.
`PlanEmailMessageRequest.newsletter` provides an explicit specialization bridge:
select an existing subject and preheader variant, retain the issue's audience and
consent/suppression references, and supply the new message directions, compliance
and scoped evidence. The resulting plan binds the original newsletter revision.
No old schema is silently reinterpreted.

HubSpot provider implementation PR 53 is now merged in Zeocore at
`8019154c3e3d911a1736df077fa98d3022f7840d`. It adds provider capabilities but
contains no package release, completed Creator/Sovereign Agent receipt wiring,
or Kit parity. The released dependency remains Zeocore 0.9.0; this source merge
does not establish the shared neutral email contract or live interoperability.
