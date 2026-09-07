# Assess performance

Canonical email assessment is input-only. Runtime retrieves aggregate provider
metrics through Zeocore/ZEOconnect, Newsroom persists normalized observations and
retrieval receipts, and Creator receives those artifacts in
`creator.assess_email_program@1.0.0`.

## Supply observations

Use `AssessEmailProgramRequest` with the exact `EmailCampaignPlan`, a tuple of
`EmailMetricObservation`, the observation window, expected metric names and an
explicit timestamp. No connector service is required or consulted. The
[installed reference workflow](email-marketing.md#offline-proof) demonstrates the
complete acquisition-boundary simulation and capability invocation.

Each observation carries organization/publication, campaign revision, operation
binding, retrieval-receipt reference and digest, provider definition/version,
aggregate segment, window, completeness, coverage and attribution assumptions.
It contains no subscriber identities or provider response body.

Supported names cover attempted, accepted, delivered, deferred, bounced,
complained, unsubscribed, opened, unique link clicks, CTA conversions, sequence
enrolments, step completion/exit, campaign conversion and attributed revenue.
Open observations require reliability notes. Revenue requires an attribution
policy. Rates require a nonzero denominator and an exact numerator/value relation.

## Interpret conservatively

Partial observations remain partial. Missing expected metrics become data gaps.
An empty input produces an unknown, limited-confidence assessment. Provider
acceptance is not delivery, an open is not reliable evidence of attention, and
correlation does not establish campaign lift.

Creator records hypotheses for future review. It does not select a winner, alter
a live campaign, enlarge an audience, schedule work or activate a sequence.
Assess each publication and campaign revision separately.

## Legacy v1 compatibility

`creator.assess_performance@1.0.0`, `MetricsQuery`, `MetricObservation` and
`PerformanceAssessment` retain their original schemas and behavior. That legacy
capability uses `creator.metrics_source`; existing applications may supply an
in-memory view of previously collected observations. It is not the canonical
email-marketing path. Do not pass a live connector or ZEOconnect proxy into the
new email capabilities.

The old credential-free example remains available as
`uv run python examples/assess_performance.py`. New email integrations should run
`uv run python examples/email_marketing.py` and use the input-only request above.
