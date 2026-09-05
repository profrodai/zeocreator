# Error codes

Capability failures use stable enumerated codes. Treat them as programmatic
outcomes; use the human message for operators, not branching logic.

| Code | Meaning | Typical action |
|---|---|---|
| `ZEO_CAP_UNAVAILABLE` | A required context service is missing | Supply the declared service; do not fall back to ambient credentials |
| `ZEO_CREATOR_SCOPE_MISMATCH` | Organization or publication scope differs | Correct the input chain |
| `ZEO_CREATOR_PUBLICATION_LEAKAGE` | Evidence or artifacts cross publications | Rebuild with publication-scoped inputs |
| `ZEO_CREATOR_PROVENANCE_MISMATCH` | Observation provenance differs from its query | Correct the adapter or query |
| `ZEO_CREATOR_WINDOW_MISMATCH` | Query and synthesis windows differ | Align the research window |
| `ZEO_CREATOR_NO_EVIDENCE` | No permitted observations were returned | Expand authorized reads or record the coverage gap |
| `ZEO_CREATOR_NO_USABLE_EVIDENCE` | Policy excluded every observation | Escalate editorially; do not bypass policy |
| `ZEO_CREATOR_STALE_INPUT` | A canonical digest no longer matches | Revalidate and create a new revision |
| `ZEO_CREATOR_STALE_DIGEST` | A delivery input was modified after binding | Reproduce or rebuild the review chain |
| `ZEO_CREATOR_DUPLICATE_PUBLICATION` | Planner received a publication twice | Deduplicate scoped inputs |
| `ZEO_CREATOR_INSUFFICIENT_NOVEL_TOPICS` | Evidence cannot fill requested unique formats | Gather more evidence or change constraints |
| `ZEO_CREATOR_BRAND_MISMATCH` | Profile or artifact brand reference differs | Use the matching publication profile |
| `ZEO_CREATOR_UNSUPPORTED_CLAIM` | Assignment/artifact includes an unaccepted claim | Remove it or add accepted evidence |
| `ZEO_CREATOR_MISSING_CLAIM_TRACE` | Accepted claims are absent from the artifact manifest | Correct the producer manifest |
| `ZEO_CREATOR_ARTIFACT_IDENTITY_MISMATCH` | Brief, manifest, and artifact identity differ | Use outputs from the accepted brief revision |
| `ZEO_CREATOR_EXTRACTED_TEXT_MISSING` | Claim-sensitive artifact lacks verified extracted text | Extract and attest artifact text before review |
| `ZEO_CREATOR_ARTIFACT_DIGEST_UNVERIFIED` | Retrieved artifact-byte proof does not match the artifact | Retrieve the artifact again and recompute SHA-256 |
| `ZEO_CREATOR_PROHIBITED_CLAIM` | Artifact contains prohibited language | Revise and reproduce |
| `ZEO_CREATOR_DESTINATION_MISMATCH` | Channel was not accepted by the brief | Correct the channel plan |
| `ZEO_CREATOR_REQUIRED_ATTESTATION_FAILED` | A required attestation is absent or failed | Require a complete artifact manifest |
| `ZEO_CREATOR_DELIVERY_BLOCKED` | Distribution was attempted with blocking findings | Resolve findings and obtain a new review |
| `ZEO_CREATOR_APPROVAL_STALE` | Payload, destination, or schedule changed | Generate and approve a new digest |

The canonical list for each capability is present in its manifest. Use:

```console
zeo-creator capabilities --json
```
