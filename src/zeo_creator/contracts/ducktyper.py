"""Typed external boundary consumed by the Ducktyper renderer."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from zeo_creator.contracts.common import CreatorModel, DurableArtifact
from zeo_creator.contracts.editorial import DeliverableKind
from zeo_creator.contracts.evidence import EvidenceClaim


class AnimatedEpisodePayload(CreatorModel):
    kind: Literal[DeliverableKind.ANIMATED_EPISODE] = DeliverableKind.ANIMATED_EPISODE
    script: str = Field(min_length=1)
    scene_beats: tuple[str, ...] = Field(min_length=1)
    dialogue: tuple[str, ...] = Field(min_length=1)
    voice_over: tuple[str, ...] = Field(min_length=1)
    on_screen_text: tuple[str, ...] = Field(min_length=1)
    character_actions: tuple[str, ...] = Field(min_length=1)
    setting: str = Field(min_length=1)
    duration_seconds: int = Field(gt=0)
    audio_direction: str = Field(min_length=1)
    ending: str = Field(min_length=1)


class HudPayload(CreatorModel):
    kind: Literal[DeliverableKind.HUD] = DeliverableKind.HUD
    information_hierarchy: tuple[str, ...] = Field(min_length=1)
    metrics: tuple[str, ...] = Field(min_length=1)
    labels: tuple[str, ...] = Field(min_length=1)
    motion_sequence: tuple[str, ...] = Field(min_length=1)
    visual_metaphor: str = Field(min_length=1)
    screen_regions: tuple[str, ...] = Field(min_length=1)
    narration: tuple[str, ...] = Field(min_length=1)
    highlight_events: tuple[str, ...] = Field(min_length=1)


class ComicSlidesPayload(CreatorModel):
    kind: Literal[DeliverableKind.COMIC_SLIDES] = DeliverableKind.COMIC_SLIDES
    panel_count: int = Field(ge=2)
    panel_beats: tuple[str, ...] = Field(min_length=2)
    dialogue_captions: tuple[str, ...] = Field(min_length=1)
    poses: tuple[str, ...] = Field(min_length=1)
    continuity_requirements: tuple[str, ...] = Field(min_length=1)
    slide_headlines: tuple[str, ...] = Field(min_length=1)
    final_cta: str = Field(min_length=1)

    @model_validator(mode="after")
    def panels_match(self) -> ComicSlidesPayload:
        if len(self.panel_beats) != self.panel_count:
            raise ValueError("panel_count must match panel_beats")
        return self


FormatPayload = Annotated[
    AnimatedEpisodePayload | HudPayload | ComicSlidesPayload,
    Field(discriminator="kind"),
]


class DucktyperBrief(DurableArtifact):
    brief_id: str = Field(min_length=1)
    assignment_id: str = Field(min_length=1)
    deliverable_kind: DeliverableKind
    objective: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    desired_audience_action: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    thesis: str = Field(min_length=1)
    hook: str = Field(min_length=1)
    evidence_claims: tuple[EvidenceClaim, ...] = Field(min_length=1)
    source_refs: tuple[str, ...] = Field(min_length=1)
    brand_profile_ref: str = Field(min_length=1)
    character_refs: tuple[str, ...] = ()
    visual_style_ref: str = Field(min_length=1)
    cta: str = Field(min_length=1)
    prohibited_claims: tuple[str, ...] = ()
    target_channels: tuple[str, ...] = Field(min_length=1)
    content_revision: int = Field(default=1, ge=1)
    format_payload: FormatPayload

    @model_validator(mode="after")
    def payload_matches_deliverable(self) -> DucktyperBrief:
        if self.format_payload.kind != self.deliverable_kind:
            raise ValueError("format payload kind must match deliverable_kind")
        return self


def required_render_elements(brief: DucktyperBrief) -> tuple[str, ...]:
    """Return stable validation keys required from Ducktyper's manifest."""
    if isinstance(brief.format_payload, AnimatedEpisodePayload):
        return (
            "script",
            "scene_beats",
            "dialogue",
            "voice_over",
            "on_screen_text",
            "character_actions",
            "setting",
            "audio_direction",
            "ending",
        )
    if isinstance(brief.format_payload, HudPayload):
        return (
            "information_hierarchy",
            "metrics",
            "labels",
            "motion_sequence",
            "visual_metaphor",
            "screen_regions",
            "narration",
            "highlight_events",
        )
    return (
        "panel_beats",
        "dialogue_captions",
        "poses",
        "continuity_requirements",
        "slide_headlines",
        "final_cta",
    )
