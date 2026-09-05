"""Acceptance coverage for the two-property daily creator portfolio."""

from collections import Counter

from tests.fixtures.dogfood import build_dogfood_snapshot
from zeo_creator.contracts.ducktyper import required_render_elements
from zeo_creator.contracts.editorial import DeliverableKind


def test_dogfood_snapshot_has_six_isolated_deliverables() -> None:
    snapshot = build_dogfood_snapshot()

    assert len(snapshot.syntheses) == 2
    assert len(snapshot.plan.assignments) == 6
    assert len(snapshot.briefs) == 6
    assert len(snapshot.artifacts) == 6
    assert len(snapshot.manifests) == 6
    assert len(snapshot.reviews) == 6
    assert len(snapshot.operations) == 12
    assert len(snapshot.assessments) == 2

    expected = {
        (publication_id, kind)
        for publication_id in ("profrod.ai", "zeroemployee.org")
        for kind in DeliverableKind
    }
    assert {
        (assignment.publication_id, assignment.deliverable_kind)
        for assignment in snapshot.plan.assignments
    } == expected
    assert Counter(item.publication_id for item in snapshot.briefs) == {
        "profrod.ai": 3,
        "zeroemployee.org": 3,
    }


def test_briefs_and_renders_are_evidence_and_digest_bound() -> None:
    snapshot = build_dogfood_snapshot()
    synthesis_by_publication = {item.publication_id: item for item in snapshot.syntheses}

    for brief, artifact, manifest, review in zip(
        snapshot.briefs,
        snapshot.artifacts,
        snapshot.manifests,
        snapshot.reviews,
        strict=True,
    ):
        synthesis = synthesis_by_publication[brief.publication_id]
        assert brief.source_refs
        assert set(brief.source_refs) <= set(synthesis.evidence_refs)
        assert all(claim.evidence_refs for claim in brief.evidence_claims)
        assert artifact.brief_id == brief.brief_id
        assert artifact.brief_content_digest == brief.content_digest
        assert manifest.brief_content_digest == brief.content_digest
        attested_elements = {
            item.check_id.removeprefix("element.")
            for item in manifest.attestations
            if item.check_id.startswith("element.") and item.result
        }
        assert set(required_render_elements(brief)) <= attested_elements
        assert review.ready_for_approval is True
        assert review.approval_digest


def test_publication_identity_never_crosses_the_daily_chain() -> None:
    snapshot = build_dogfood_snapshot()
    profiles = {item.publication_id: item for item in snapshot.profiles}

    for brief, review in zip(snapshot.briefs, snapshot.reviews, strict=True):
        profile = profiles[brief.publication_id]
        assert brief.brand_profile_ref == profile.reference
        assert review.publication_id == brief.publication_id
    for operation in snapshot.operations:
        assert operation.publication_id in operation.connection_ref
        assert operation.publication_id in operation.destination_account_ref
    assert {item.publication_id for item in snapshot.assessments} == {
        "profrod.ai",
        "zeroemployee.org",
    }


def test_dogfood_fixture_is_deterministic() -> None:
    assert build_dogfood_snapshot().model_dump(mode="json") == build_dogfood_snapshot().model_dump(
        mode="json"
    )
