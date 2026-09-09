# Supply source observations

Acquire source material before invoking canonical Creator transformations.
Runtime calls Zeocore/ZEOconnect, normalizes the result, and persists evidence and
retrieval receipts in Newsroom or another caller-owned store. Pass only scoped,
digest-bound observations into Creator.

## Canonical flow

1. Resolve connections and acquire evidence outside Creator.
2. Normalize source identity, origin, observation time, extraction provenance and
   completeness into `SourceObservation` or the required evidence contract.
3. Persist the acquisition receipt and evidence before planning or review.
4. Invoke the input-only editorial capability with the normalized artifacts.
5. Persist its result under the same organization and publication.

Provider SDKs, credentials, OAuth, contact records and unfiltered provider error
bodies stay outside Creator. An opaque connection reference is provenance, not
permission to resolve or use a credential.

For email performance, supply `EmailMetricObservation` to
`creator.assess_email_program@4.0.0`. See [performance](performance.md).

## Legacy evidence port

`creator.research_synthesis@1.0.0` retains its existing evidence-query schema and
`creator.evidence_source` requirement for compatibility. A runner can supply an
in-memory implementation of `EvidenceSourcePort.retrieve(query, publication)`
that returns previously acquired `EvidenceItem` values. This preserves older
applications without teaching Creator to acquire new source observations.

The existing `examples/research_connector.py` uses synthetic in-memory evidence
and is installed as `python -m zeo_creator.examples.research_connector`.
New canonical workflows acquire and persist observations
before Creator invocation; they do not inject a live connector into Creator's
`ToolContext`.

## Provenance obligations

The host authenticates source and receipt origin, binds organization/publication,
normalizes safe failure classifications, and enforces scope before returning
artifacts. Creator checks the supplied identity and digests; a digest alone does
not authenticate a source or establish factual truth.
