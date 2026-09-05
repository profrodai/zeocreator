# Contracts, identity, and digests

Every durable artifact is designed to survive process boundaries, retries, human
review, and later reconciliation.

## Common durable fields

`DurableArtifact` supplies:

| Field | Purpose |
|---|---|
| `schema_version` | Identifies the serialized contract version |
| `created_at` | Records artifact creation time |
| `organization_id` | Prevents organization-scope ambiguity |
| `publication_id` | Keeps publication identity explicit |
| `input_refs` | Points to the artifacts or observations used |
| `revision` | Distinguishes deliberate updates |
| `content_digest` | Binds the canonical JSON-safe content |

Models are strict, immutable, and reject unknown fields.

## Canonical digests

ZEO Creator serializes JSON-safe content with sorted keys and compact separators,
then prefixes its SHA-256 digest with `sha256:`.

```python
from zeo_creator.contracts.common import canonical_digest

digest = canonical_digest({"publication_id": "profrod.ai", "revision": 2})
```

The digest does not replace a signature or runtime authorization. It supplies a
stable content identity that an approval system can authorize exactly.

## Stable identifiers

`stable_id(prefix, *parts)` derives a readable deterministic identifier from
immutable identity material. Retrying the same proposal preserves its operation
ID and idempotency key; changing its destination, schedule, artifact, or approval
changes them.

## Revision discipline

Use a new revision whenever durable content changes. Never mutate an artifact
under an existing revision. ZEO Creator checks that each supplied digest still
matches the model content, including unsafe copies constructed outside normal
validation.

## Publication isolation

Publication identity flows through:

```text
PublicationProfile
  → EvidenceItem / ResearchSynthesis
  → EditorialAssignment / DailyEditorialPlan
  → DucktyperBrief
  → RenderedArtifact / RenderManifest
  → DeliveryReviewBundle
  → ProposedPublicationOperation
  → DailyPerformanceAssessment
```

A mismatch at any transition is a typed failure. Cross-property reuse must be
explicitly represented and attributable; it cannot occur by accidental object
mixing.

## Secret safety

Public models use explicit fields and `extra="forbid"`. Distribution payloads,
proposals, and receipts additionally reject credential-shaped keys recursively.

Safe references such as `connection_ref` and `destination_account_ref` identify
runner-owned records. They are not places to serialize provider credentials.
