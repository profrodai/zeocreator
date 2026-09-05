"""Optional provider-neutral artifact retrieval boundary."""

from typing import Protocol

from zeo_creator.contracts.delivery import ArtifactManifest


class ArtifactStorePort(Protocol):
    def get_artifact_bytes(self, artifact_ref: str) -> bytes | None: ...

    def get_manifest(self, manifest_ref: str) -> ArtifactManifest | None: ...
