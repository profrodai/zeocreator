"""Optional provider-neutral artifact retrieval boundary."""

from typing import Protocol

from zeo_creator.contracts.delivery import RenderedArtifact, RenderManifest


class ArtifactStorePort(Protocol):
    def get_artifact(self, artifact_ref: str) -> RenderedArtifact | None: ...

    def get_render_manifest(self, manifest_ref: str) -> RenderManifest | None: ...
