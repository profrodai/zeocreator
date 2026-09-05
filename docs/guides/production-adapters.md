# Integrate a production engine

ZEO Creator depends on public contracts, never on a particular producer. Your
adapter consumes a `ContentBrief` and returns an `ArtifactManifest`.

```mermaid
flowchart LR
    B[ContentBrief] --> A[Production adapter]
    A --> P[Private or public producer]
    P --> M[ArtifactManifest]
    M --> V[ZEO Creator validation]
```

## Consume creator intent

Treat these brief fields as the stable boundary:

- `content_kind` is an extensible qualified identifier;
- `source_content` is a standard media type plus content;
- evidence claims and source references preserve provenance;
- brand and style fields are references, not embedded systems;
- `delivery_requirements` declares checks the producer must attest; and
- `producer_extension` is opaque to ZEO Creator.

An extension includes a namespace, schema identifier, version, schema digest,
and JSON payload. Validate it inside the adapter. Do not require ZEO Creator to
import the private schema.

## Return a bundle

Use one `ArtifactDescriptor` per produced file. Supply its role, media type,
byte length, content digest, storage reference, and safe metadata. The manifest
must also include a corresponding `ArtifactDigestProof` based on retrieved bytes.

Each `ArtifactAttestation` identifies the check, check version, result, evidence
reference, tool identity, observed value, and expected constraint. ZEO Creator
requires every brief-declared required check to exist and pass. Producers may
add further private checks.

## Export machine-readable contracts

Pin a ZEO Creator version in producer CI, then export its schemas:

```console
zeo-creator contracts list --json
zeo-creator contracts export --output=./vendor/zeo-creator
zeo-creator contract-schema --name=content-brief --version=1
```

Use the exported schemas to validate adapter inputs and outputs in any language.
RFC 8785 golden vectors in `reference/digest-vectors.json` verify cross-language
digest compatibility.

## Adapter responsibilities

The adapter owns lowering, producer configuration, production execution, and
private quality checks. It must not place reusable credentials in briefs,
manifests, extensions, metadata, logs, or receipts.
