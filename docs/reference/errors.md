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
| `ZEO_CREATOR_STALE_DIGEST` | A delivery input was modified after binding | Re-render or rebuild the review chain |
| `ZEO_CREATOR_DUPLICATE_PUBLICATION` | Planner received a publication twice | Deduplicate scoped inputs |
| `ZEO_CREATOR_INSUFFICIENT_NOVEL_TOPICS` | Evidence cannot fill requested unique formats | Gather more evidence or change constraints |
| `ZEO_CREATOR_BRAND_MISMATCH` | Profile or render brand reference differs | Use the matching publication profile |
| `ZEO_CREATOR_UNSUPPORTED_CLAIM` | Assignment/render includes an unaccepted claim | Remove it or add accepted evidence |
| `ZEO_CREATOR_MISSING_CLAIM_TRACE` | Accepted claims are absent from the render manifest | Correct Ducktyper's manifest/render |
| `ZEO_CREATOR_RENDER_IDENTITY_MISMATCH` | Brief, manifest, and artifact identity differ | Use outputs from the accepted brief revision |
| `ZEO_CREATOR_MISSING_RENDER_ELEMENT` | Required format element is absent | Re-render with full coverage |
| `ZEO_CREATOR_PROHIBITED_CLAIM` | Render contains prohibited language | Revise and re-render |
| `ZEO_CREATOR_DESTINATION_MISMATCH` | Channel was not accepted by the brief | Correct the channel plan |
| `ZEO_CREATOR_TECHNICAL_CHECKS_MISSING` | Ducktyper supplied no technical checks | Require a complete render manifest |
| `ZEO_CREATOR_TECHNICAL_CHECK_FAILED` | A renderer check failed | Repair or re-render the artifact |
| `ZEO_CREATOR_DELIVERY_BLOCKED` | Distribution was attempted with blocking findings | Resolve findings and obtain a new review |
| `ZEO_CREATOR_APPROVAL_STALE` | Payload, destination, or schedule changed | Generate and approve a new digest |

The canonical list for each capability is present in its manifest. Use:

```console
zeo-creator capabilities --json
```
