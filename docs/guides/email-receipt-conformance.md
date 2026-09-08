# Shared email receipt conformance

Creator consumes normalized evidence through
`zeo_creator.services.email_receipts.validate_operation_receipt`. Pass the exact
`ProposedEmailOperation`, `EmailRemoteReceipt`, and (for a content effect) its
`EmailDeliveryPackage`. Cancellation can consume its historical target without
requiring a fresh package. Sequence effects do not take a delivery package.

For **proposal preparation**, the package argument follows `material.delivery`.
The reference cancellation material has only `target_delivery`, so omit `package`
when calling `propose_operation` or `creator.propose_email_operation` for it:

```python
from zeo_creator.services.email_marketing import propose_operation

cancel = propose_operation(
    cancel_material, created_at, idempotency_key,
    release=release, originating_operation=scheduling_proposal,
)
```

Supplying a package when `material.delivery` is absent refuses with
`unexpected_effect_delivery`. A cancellation material that explicitly includes a
`delivery` requires its matching package. This proposal rule is distinct from
receipt consumption below, which may validate a supplied historical target package.

```python
from zeo_creator.services.email_receipts import validate_operation_receipt

# Supplied by the integrating application after issuer/contract authentication.
receipt = validate_operation_receipt(proposal, normalized_receipt, package=package)
```

The consumer checks organization/publication, immutable proposal identity,
campaign release, execution account/context, effect intent, receipt chronology,
creative package, message, exact audience and sequence. A mutation must return its
approved remote target. Migration must return the *target* sequence object, while
its source remains provenance in the migration plan. A fresh digest does not make
an unrelated receipt correspond to the approved proposal.

During update/cancellation proposal preparation, Creator also checks that the
prior receipt's normalized intent equals its originating proposal's exact intent.
A matching operation reference alone is insufficient: a create-draft origin with
an update-draft result (or the reverse) refuses with
`originating_operation_effect_mismatch`, preserved through the public capability.

This function consumes evidence; it does not authenticate an issuer, prove an
external effect, authorize a retry, or freshen an expired approval. The integrating
host must validate the trusted issuer and receipt-contract digest, authenticate
account ownership, and retain remote observations. `ambiguous` and `needs_review`
remain unchanged. Consuming a historical receipt does not reauthorize a send.

## One result definition

`EmailRemoteResult` remains the exact six-way discriminated union introduced in
email v4. The separately addressable `email-remote-result.v4.schema.json` exports
that same type, including all definitions. It is available through the contract
catalog and wheel resources; no new competing receipt vocabulary is introduced.
The original v1/v2/v3/v4 schema files remain unchanged.

Zeocore owns the eventual public execution contract. It must adopt this reviewed
shape, either by extracting a shared public dependency without a dependency cycle,
or by vendoring the exported schema at a pinned commit and digest. Zeocore must
not import Creator while Creator depends on Zeocore. Private hosts may import the
Creator types and correspondence function directly. Any future shared extraction
must retain these wire bytes or use an explicit contract migration.

## Portable behavioral evidence

The current wheel corpus is `reference_artifacts/email-receipt-conformance-v2.json`:
135 sanitized cases with explicitly authored verdicts and RFC 8785 digests. Its
five complete schemas cover result, receipt, intent, proposal and package.
Every one of the twelve effects has positive result, receipt and correspondence
cases, including both draft effects and all six result discriminators. Negatives
cover incompatible effect/kind, contradictory lifecycle state, missing sequence
audience, account, connector revision, chronology, message, audience, delivery,
operation, release, remote target and package substitutions. Correspondence
substitutions carry valid fresh receipt digests, so accidental integrity failure
cannot stand in for the binding checks. Historical and uncertain evidence has
positive cases too. The original 16 lifecycle transition cases remain included.
The source artifact is `reference/email-receipt-conformance-v2.json`.

Corpus v1 remains byte-identical for historical reproduction and is superseded
for current conformance. The reviewers demonstrated that a validator checking only
operation, release and migration source, or one omitting four result kinds, could
pass v1. Both counterfeits fail v2 in regression tests. `packaged_cases()` and the
module command use v2; `packaged_cases(1)` is for reproducing the historical gap.
Require the pinned v2 artifact when reporting current conformance. The corpus
version changes independently of the unchanged email v4 wire contracts.

Regenerate current resources with `make reference`, which uses the v8 exporter
and `build_cases(version=2)`. Unversioned builder calls now refuse with a retirement
explanation, preventing preserved v6/v7 scripts from writing current data under a
historical corpus filename. Those legacy scripts may regenerate their earlier
schema/example outputs before reaching that refusal, but cannot write either
corpus. Their source stays unchanged for the historical record. Rebuilding v1 is
unsupported; read the frozen v1 resource for historical reproduction.

Run the installed Creator implementation without a checkout or credentials:

```shell
python -m zeo_creator.reference.email_receipt_conformance
```

A consuming implementation supplies four validation callbacks:

```python
from zeo_creator.reference.email_receipt_conformance import packaged_cases, verify_cases

failures = verify_cases(packaged_cases(), {
    "result": host_validate_result,
    "receipt": host_validate_receipt,
    "intent": host_validate_intent,
    "correspondence": host_validate_correspondence,
})
assert not failures
```

Each callback receives a JSON object, returns normally for acceptance, and raises
`ValueError` or `TypeError` for rejection. A correspondence input contains
`proposal`, `receipt`, and nullable `package`. Unexpected exceptions propagate;
they must not be counted as correct domain rejection. Missing validators fail the
run. Cases include both positive and negative expectations, so accepting or
rejecting every input fails. JSON Schema alone cannot enforce all semantic and
canonical digest invariants; use the behavioral cases too.

The corpus digests detect accidental changes, not authenticity. Pin the reviewed
commit and artifact SHA-256 outside the supplied document. A document carrying its
own replacement digest is not a trusted signature. Passing these cases establishes
only this stated offline conformance surface; it does not qualify every possible
input, provider semantics, authentication, durable idempotency, or live delivery.

## Integration work still owned by the execution layers

Current HubSpot and Kit adapters expose provider operations and raw result records.
Production integration still needs an authenticated host to resolve opaque sender,
template and audience references, bind observed payloads and revisions, normalize
provider outcomes to this shared contract, and persist reconciliation state.
Unsupported semantics must refuse. Subscriber data and raw provider errors stay
outside Creator. The reference host demonstrates this boundary with synthetic
data; it is not a production connector or durable execution store.
