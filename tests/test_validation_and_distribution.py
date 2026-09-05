"""Failure-path coverage for delivery approval and publication proposals."""

from datetime import timedelta

import pytest

from tests.fixtures.dogfood import NOW, build_dogfood_snapshot, publication_profiles
from zeo_creator.contracts.delivery import RenderManifest
from zeo_creator.contracts.distribution import ChannelPlan
from zeo_creator.errors import CreatorDomainError
from zeo_creator.services.distribution import prepare_distribution_operations
from zeo_creator.services.validation import validate_delivery_bundle


def _review_with_manifest(manifest: RenderManifest):
    snapshot = build_dogfood_snapshot()
    brief = snapshot.briefs[0]
    artifact = snapshot.artifacts[0]
    original_review = snapshot.reviews[0]
    channel_plan = ChannelPlan(
        channel_plan_id=original_review.input_refs[-1],
        created_at=NOW,
        organization_id=brief.organization_id,
        publication_id=brief.publication_id,
        input_refs=(brief.brief_id,),
        destinations=original_review.proposed_destinations,
    )
    return validate_delivery_bundle(
        brief=brief,
        artifact=artifact,
        manifest=manifest,
        publication=publication_profiles()[0],
        synthesis=snapshot.syntheses[0],
        channel_plan=channel_plan,
        created_at=NOW,
        revision=1,
    )


@pytest.mark.parametrize(
    ("changes", "expected_code"),
    [
        ({"brand_profile_ref": "profile_wrong@1"}, "ZEO_CREATOR_BRAND_MISMATCH"),
        ({"rendered_claim_ids": ("claim_not_in_brief",)}, "ZEO_CREATOR_UNSUPPORTED_CLAIM"),
        ({"brief_content_digest": "sha256:" + "0" * 64}, "ZEO_CREATOR_STALE_DIGEST"),
    ],
)
def test_validation_blocks_wrong_brand_claim_digest_and_elements(
    changes: dict[str, object], expected_code: str
) -> None:
    manifest = build_dogfood_snapshot().manifests[0].model_copy(update=changes)
    review = _review_with_manifest(manifest)

    assert review.ready_for_approval is False
    assert expected_code in {finding.code for finding in review.blocking_findings}


def test_validation_blocks_missing_render_element_attestation() -> None:
    manifest = build_dogfood_snapshot().manifests[0]
    changed = manifest.model_copy(
        update={
            "attestations": tuple(
                item for item in manifest.attestations if item.check_id != "element.script"
            )
        }
    )
    review = _review_with_manifest(changed)

    assert review.ready_for_approval is False
    assert "ZEO_CREATOR_MISSING_RENDER_ELEMENT" in {
        finding.code for finding in review.blocking_findings
    }


def test_changed_schedule_invalidates_approval() -> None:
    snapshot = build_dogfood_snapshot()
    brief, artifact, manifest, review = (
        snapshot.briefs[0],
        snapshot.artifacts[0],
        snapshot.manifests[0],
        snapshot.reviews[0],
    )
    changed_destinations = tuple(
        destination.model_copy(
            update={"scheduled_for": destination.scheduled_for + timedelta(hours=1)}
        )
        for destination in review.proposed_destinations
    )
    changed_plan = ChannelPlan(
        channel_plan_id=review.input_refs[-1],
        created_at=NOW,
        organization_id=brief.organization_id,
        publication_id=brief.publication_id,
        input_refs=(brief.brief_id,),
        destinations=changed_destinations,
    )

    with pytest.raises(CreatorDomainError) as caught:
        prepare_distribution_operations(
            brief=brief,
            artifact=artifact,
            manifest=manifest,
            review=review,
            channel_plan=changed_plan,
            created_at=NOW,
            revision=1,
        )
    assert caught.value.code == "ZEO_CREATOR_APPROVAL_STALE"


def test_distribution_handoff_is_idempotent_and_write_free() -> None:
    first = build_dogfood_snapshot().operations
    second = build_dogfood_snapshot().operations

    assert [item.idempotency_key for item in first] == [item.idempotency_key for item in second]
    assert [item.operation_id for item in first] == [item.operation_id for item in second]
