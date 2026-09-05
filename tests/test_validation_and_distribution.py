"""Failure paths for producer-neutral delivery and distribution."""

from datetime import datetime, timedelta
from typing import cast

import pytest

from tests.fixtures.reference import NOW, build_reference_snapshot, publication_profiles
from zeo_creator.contracts.delivery import ArtifactManifest, DeliveryReviewBundle
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
        variants=review.proposed_variants,
    )


def _review_with_manifest(manifest: ArtifactManifest) -> DeliveryReviewBundle:
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
    assert all(item.destination.scheduled_for is not None for item in review.proposed_variants)
    variants = tuple(
        item.model_copy(
            update={
                "destination": item.destination.model_copy(
                    update={
                        "scheduled_for": cast(datetime, item.destination.scheduled_for)
                        + timedelta(hours=1)
                    }
                )
            }
        )
        for item in review.proposed_variants
    )
    changed_plan = _channel_plan(0).model_copy(update={"variants": variants})
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


def test_distribution_operations_preserve_destination_variants() -> None:
    snapshot = build_reference_snapshot()
    first_brief = snapshot.briefs[1]
    operations = tuple(
        item for item in snapshot.operations if first_brief.brief_id in item.input_refs
    )

    assert len(operations) == 2
    assert operations[0].channel == operations[0].destination.channel
    assert operations[1].channel == operations[1].destination.channel
    assert operations[0].selected_artifact_refs != operations[1].selected_artifact_refs
    assert operations[0].content.content != operations[1].content.content


def test_validation_blocks_unknown_variant_artifact() -> None:
    snapshot = build_reference_snapshot()
    plan = _channel_plan(0)
    variants = (
        plan.variants[0].model_copy(update={"selected_artifact_refs": ("missing",)}),
        *plan.variants[1:],
    )
    review = validate_delivery_bundle(
        brief=snapshot.briefs[0],
        manifest=snapshot.manifests[0],
        publication=publication_profiles()[0],
        synthesis=snapshot.syntheses[0],
        channel_plan=plan.model_copy(update={"variants": variants}),
        created_at=NOW,
        revision=1,
    )
    assert "ZEO_CREATOR_ARTIFACT_SELECTION_MISMATCH" in {
        finding.code for finding in review.blocking_findings
    }
