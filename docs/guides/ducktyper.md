# Hand off to Ducktyper

ZEO Creator and Ducktyper meet at a typed external boundary. Neither package
imports the other's internal implementation.

## The brief envelope

Every `DucktyperBrief` carries:

- organization, publication, assignment, and brand identity;
- objective, audience, desired action, thesis, and hook;
- evidence claims and source references;
- character and visual-style references;
- CTA policy, prohibited claims, and target channels;
- content revision and canonical digest; and
- one discriminated format payload.

## Format payloads

=== "Animated episode"

    `AnimatedEpisodePayload` requires a script, scene beats, dialogue,
    voice-over, on-screen text, character actions, setting, duration, audio
    direction, and ending.

=== "HUD"

    `HudPayload` requires information hierarchy, metrics, labels, motion
    sequence, visual metaphor, screen regions, narration, and highlight events.

=== "Comic slides"

    `ComicSlidesPayload` requires panel count and beats, dialogue/captions,
    poses, continuity requirements, slide headlines, and final CTA. Panel count
    must match the number of panel beats.

Pydantic rejects an invalid format combination before renderer invocation.

## Serialize the accepted brief

```python
brief_json = brief.model_dump_json(indent=2)
```

Send this JSON across your chosen transport. The transport and artifact store are
runner concerns; the schema is the integration contract.

The canonical JSON Schema is committed as
[`DucktyperBrief.schema.json`](https://github.com/profrodai/zeocreator/blob/main/reference/schemas/DucktyperBrief.schema.json).

## Require bound render outputs

Ducktyper returns both:

```python
RenderedArtifact(
    brief_id=brief.brief_id,
    content_revision=brief.content_revision,
    brief_content_digest=brief.content_digest,
    artifact_digest="sha256:…",
    # ...
)
```

and:

```python
RenderManifest(
    brief_id=brief.brief_id,
    content_revision=brief.content_revision,
    brief_content_digest=brief.content_digest,
    artifact_ref=artifact.artifact_ref,
    artifact_digest=artifact.artifact_digest,
    # ...
)
```

The manifest also declares included format elements, rendered claim IDs, brand
profile reference, and technical checks. Validation fails when any binding is
missing, stale, or inconsistent.

## Revision rule

Treat an accepted brief as immutable. To change it:

1. create a new content revision;
2. compute its new canonical digest;
3. render against that revision;
4. validate the new render; and
5. obtain a new approval digest.

Never silently replace content under an existing brief revision.
