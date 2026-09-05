"""Neutral examples for editorial-kernel capability manifests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.evidence import ResearchWindow
from zeo_creator.contracts.newsroom import (
    EditorialAgenda,
    EditorialSignal,
    ObservationCompleteness,
    PublicationSlot,
    SlotUrgency,
    SourceObservation,
    StoryDossier,
    StoryRevision,
)
from zeo_creator.services.editorial_kernel import DeterministicEditorialStrategy

NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)
WINDOW = ResearchWindow(starts_at=NOW - timedelta(days=1), ends_at=NOW)


def observation() -> SourceObservation:
    raw = {"title": "A verified public update", "body": "The service published an update."}
    return SourceObservation(
        observation_id="observation_example",
        created_at=NOW,
        organization_id="org_example",
        publication_id="publication-a.example",
        source_identity="source_example",
        source_kind="official.notice",
        source_published_at=NOW - timedelta(hours=1),
        retrieved_at=NOW,
        canonical_url="https://example.invalid/update",
        author_or_origin="Example Service",
        publication_scope="publication-a.example",
        raw_artifact_ref="artifact://raw/example",
        raw_artifact_digest=canonical_digest(raw),
        extracted_content_ref="artifact://extracted/example",
        extracted_content_digest=canonical_digest(raw["body"]),
        extracted_text=raw["body"],
        completeness=ObservationCompleteness.COMPLETE,
        availability="available",
        language="en",
        geography=("example-region",),
        extraction_method="example.text",
        extraction_version="1.0.0",
        access_policy_ref="access.public@1",
        retention_policy_ref="retention.example@1",
    )


def slot() -> PublicationSlot:
    return PublicationSlot(
        slot_id="slot_example",
        publication_id="publication-a.example",
        desk_id="desk_general",
        content_kind="news.article",
        purpose="Explain the verified update",
        due_at=NOW + timedelta(hours=2),
        urgency=SlotUrgency.DAILY,
        target_channels=("website",),
        desired_audience_action="Understand what changed",
        risk_policy_ref="risk.general@1",
        approval_policy_ref="approval.editor@1",
    )


def extract_request() -> dict[str, object]:
    item = observation()
    return {
        "organization_id": item.organization_id,
        "publication_id": item.publication_id,
        "observations": [item.model_dump(mode="json")],
        "created_at": NOW.isoformat(),
        "revision": 1,
    }


def signal() -> EditorialSignal:
    return DeterministicEditorialStrategy().extract_signals(
        observations=(observation(),), created_at=NOW, revision=1
    )[0]


def story() -> StoryRevision:
    return DeterministicEditorialStrategy().update_revisions(
        signals=(signal(),), previous_revisions=(), created_at=NOW
    )[0]


def dossier() -> StoryDossier:
    return DeterministicEditorialStrategy().build_dossier(
        story=story(),
        audience_significance="Readers need a verified explanation.",
        prior_coverage_refs=(),
        created_at=NOW,
        revision=1,
    )


def agenda() -> EditorialAgenda:
    return DeterministicEditorialStrategy().plan_agenda(
        organization_id="org_example",
        publication_id="publication-a.example",
        desk_id="desk_general",
        coverage_window=WINDOW,
        dossiers=(dossier(),),
        slots=(slot().model_copy(update={"story_dossier_refs": (dossier().dossier_id,)}),),
        created_at=NOW,
        revision=1,
    )


def update_request() -> dict[str, object]:
    item = signal()
    return {
        "organization_id": item.organization_id,
        "publication_id": item.publication_id,
        "signals": [item.model_dump(mode="json")],
        "previous_revisions": [],
        "created_at": NOW.isoformat(),
    }


def dossier_request() -> dict[str, object]:
    item = story()
    return {
        "story": item.model_dump(mode="json"),
        "audience_significance": "Readers need a verified explanation.",
        "prior_coverage_refs": [],
        "created_at": NOW.isoformat(),
        "revision": 1,
    }


def agenda_request() -> dict[str, object]:
    item = dossier()
    demand = slot().model_copy(update={"story_dossier_refs": (item.dossier_id,)})
    return {
        "organization_id": item.organization_id,
        "publication_id": item.publication_id,
        "desk_id": demand.desk_id,
        "coverage_window": WINDOW.model_dump(mode="json"),
        "dossiers": [item.model_dump(mode="json")],
        "slots": [demand.model_dump(mode="json")],
        "created_at": NOW.isoformat(),
        "revision": 1,
    }


def edition_request() -> dict[str, object]:
    item = agenda()
    return {
        "agenda": item.model_dump(mode="json"),
        "edition_kind": "website.daily",
        "publication_window": WINDOW.model_dump(mode="json"),
        "update_policy_ref": "updates.living-edition@1",
        "human_editor_requirements": ["desk-editor"],
        "created_at": NOW.isoformat(),
        "revision": 1,
    }
