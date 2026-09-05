# Validate and prepare distribution

Delivery review answers one question: *is this exact artifact bundle, with these
exact destination variants, ready to ask a human to approve?*

## Validate the artifact bundle

Invoke `creator.validate_delivery@1.0.0` with the accepted brief, generic
artifact manifest, matching publication profile and synthesis, and proposed
channel plan.

The review separates blocking findings from advisory findings and reports five
top-level checks:

| Check | Protects against |
|---|---|
| Identity match | Wrong brief, revision, artifact, organization, or publication |
| Required-attestation coverage | Missing or failed checks declared by the brief |
| Source-claim traceability | Unsupported or omitted factual claims |
| Brand constraints | Wrong profile, prohibited claims, or unapproved channels |
| Artifact integrity | Missing or invalid byte-digest proof |

## Understand the approval digest

The digest includes:

```text
brief ID + brief digest + revision
artifact references + artifact digests
artifact manifest ID + manifest digest
channel-plan digest, including every destination variant
selected artifact references + content + accessibility text + extension + schedule
```

Change any one of these and the earlier approval no longer applies.

## Prepare proposals

Only a review with no blocking findings can enter
`creator.prepare_distribution@1.0.0`. Each `DistributionVariant` becomes one
`ProposedPublicationOperation` with:

- explicit channel and typed destination;
- only the artifact references selected for that destination;
- a destination-specific `ContentDocument`;
- optional accessibility text and opaque extension;
- schedule;
- exact required effects;
- approval digest; and
- deterministic idempotency key.

## Runnable example

```python
--8<-- "examples/validate_and_prepare.py"
```

```console
uv run python examples/validate_and_prepare.py
```

The example always reports `"executed_operations": 0`. Proposal construction has
no provider-write effect.

## Runtime handoff

After human approval, the controlling runtime must:

1. verify the proposal is still current;
2. resolve the referenced connection and destination;
3. check organizational policy;
4. mint exact, bounded write and external-communication authority;
5. execute through an authorized connector;
6. retain a secret-safe receipt; and
7. reconcile the provider outcome.

None of those responsibilities should be moved into ZEO Creator to simplify a
demo.
