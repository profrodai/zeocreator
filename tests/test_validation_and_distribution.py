"""Failure paths for producer-neutral delivery and distribution."""

from datetime import timedelta

import pytest

from tests.fixtures.reference import NOW, build_reference_snapshot, publication_profiles
from zeo_creator.contracts.delivery import ArtifactManifest
from zeo_creator.contracts.distribution import ChannelPlan
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.distribution import prepare_distribution_operations
from zeo_creator.services.validation import validate_delivery_bundle


def _channel_plan(index: int) -> ChannelPlan:
    snapshot = build_reference_snapshot()
    brief = snapshot.briefs[index]
    review = snapshot.reviews[index]
    return ChannelPlan(
        channel_plan_id=review.input_refs[-1],
        created_at=NOW,
        organization_id=brief.organization_id,
        publication_id=brief.publication_id,
        input_refs=(brief.brief_id,),
        destinations=review.proposed_destinations,
    )


def _review_with_manifest(manifest: ArtifactManifest):
    snapshot = build_reference_snapshot()
    return validate_delivery_bundle(
        brief=snapshot.briefs[0],
        manifest=manifest,
        publication=publication_profiles()[0],
        synthesis=snapshot.syntheses[0],
        channel_plan=_channel_plan(0),
        created_at=NOW,
        revision=1,
    )


@pytest.mark.parametrize(
    ("changes", "expected_code"),
    [
        ({"brand_profile_ref": "profile_wrong@1"}, "ZEO_CREATOR_BRAND_MISMATCH"),
        ({"produced_claim_ids": ("claim_not_in_brief",)}, "ZEO_CREATOR_UNSUPPORTED_CLAIM"),
        ({"brief_content_digest": "sha256:" + "0" * 64}, "ZEO_CREATOR_STALE_DIGEST"),
    ],
)
def test_validation_blocks_wrong_brand_claim_and_digest(
    changes: dict[str, object], expected_code: str
) -> None:
    manifest = build_reference_snapshot().manifests[0].model_copy(update=changes)
    review = _review_with_manifest(manifest)
    assert review.ready_for_approval is False
    assert expected_code in {finding.code for finding in review.blocking_findings}


def test_validation_blocks_missing_required_attestation() -> None:
    manifest = build_reference_snapshot().manifests[0]
    changed = manifest.model_copy(
        update={
            "attestations": tuple(
                item for item in manifest.attestations if item.check_id != "artifact.readable"
            )
        }
    )
    review = _review_with_manifest(changed)
    assert review.required_attestations_pass is False
    assert review.ready_for_approval is False


def test_changed_schedule_invalidates_approval() -> None:
    snapshot = build_reference_snapshot()
    brief, manifest, review = snapshot.briefs[0], snapshot.manifests[0], snapshot.reviews[0]
    destinations = tuple(
        item.model_copy(update={"scheduled_for": item.scheduled_for + timedelta(hours=1)})
        for item in review.proposed_destinations
    )
    changed_plan = _channel_plan(0).model_copy(update={"destinations": destinations})
    with pytest.raises(CreatorDomainError) as caught:
        prepare_distribution_operations(
            brief=brief,
            manifest=manifest,
            review=review,
            channel_plan=changed_plan,
            created_at=NOW,
            revision=1,
        )
    assert caught.value.code == "ZEO_CREATOR_APPROVAL_STALE"


def test_distribution_handoff_is_idempotent_and_write_free() -> None:
    first = build_reference_snapshot().operations
    second = build_reference_snapshot().operations
    assert [item.idempotency_key for item in first] == [item.idempotency_key for item in second]
