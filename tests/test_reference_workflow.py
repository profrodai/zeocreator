"""Acceptance coverage for the neutral multi-publication creator workflow."""

from collections import Counter

from tests.fixtures.reference import CONTENT_KINDS, build_reference_snapshot


def test_reference_snapshot_has_extensible_content_and_artifact_bundles() -> None:
    snapshot = build_reference_snapshot()

    assert len(snapshot.syntheses) == 2
    assert len(snapshot.plan.assignments) == 8
    assert len(snapshot.briefs) == 8
    assert len(snapshot.manifests) == 8
    assert len(snapshot.reviews) == 8
    assert len(snapshot.operations) == 16
    assert len(snapshot.assessments) == 2
    assert {item.content_kind for item in snapshot.plan.assignments} == set(CONTENT_KINDS)
    assert Counter(item.publication_id for item in snapshot.briefs) == {
        "publication-a.example": 4,
        "publication-b.example": 4,
    }
    assert any(len(item.artifacts) > 1 for item in snapshot.manifests)


def test_briefs_and_artifacts_are_evidence_and_digest_bound() -> None:
    snapshot = build_reference_snapshot()
    synthesis_by_publication = {item.publication_id: item for item in snapshot.syntheses}

    for brief, manifest, review in zip(
        snapshot.briefs, snapshot.manifests, snapshot.reviews, strict=True
    ):
        synthesis = synthesis_by_publication[brief.publication_id]
        assert set(brief.source_refs) <= set(synthesis.evidence_refs)
        assert manifest.brief_content_digest == brief.content_digest
        assert {item.artifact_ref for item in manifest.artifacts} == {
            item.artifact_ref for item in manifest.digest_proofs
        }
        assert review.ready_for_approval is True
        assert review.artifact_integrity_pass is True


def test_publication_identity_never_crosses_the_chain() -> None:
    snapshot = build_reference_snapshot()
    profiles = {item.publication_id: item for item in snapshot.profiles}
    for brief, review in zip(snapshot.briefs, snapshot.reviews, strict=True):
        assert brief.brand_profile_ref == profiles[brief.publication_id].reference
        assert review.publication_id == brief.publication_id
    assert {item.publication_id for item in snapshot.assessments} == {
        "publication-a.example",
        "publication-b.example",
    }


def test_reference_fixture_is_deterministic() -> None:
    assert build_reference_snapshot().model_dump(
        mode="json"
    ) == build_reference_snapshot().model_dump(mode="json")
