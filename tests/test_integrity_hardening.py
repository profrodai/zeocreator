"""Security-relevant lineage, timestamp, digest, and delivery invariants."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.fixtures.dogfood import (
    NOW,
    DogfoodSnapshot,
    build_dogfood_snapshot,
    publication_profiles,
)
from zeo_creator.contracts.common import CreatorModel, canonical_bytes, canonical_digest
from zeo_creator.contracts.distribution import ChannelPlan
from zeo_creator.contracts.evidence import EvidenceClaim, ResearchSynthesis
from zeo_creator.services.validation import validate_delivery_bundle


class TimestampProbe(CreatorModel):
    happened_at: datetime


def test_all_contract_models_reject_naive_datetimes_and_normalize_utc() -> None:
    with pytest.raises(ValidationError, match="timestamps must include a UTC offset"):
        TimestampProbe(happened_at=datetime(2026, 9, 5, 8))

    probe = TimestampProbe(happened_at=datetime(2026, 9, 5, 9, tzinfo=UTC) + timedelta(0))
    assert probe.happened_at.tzinfo is UTC


def test_equivalent_instants_have_the_same_digest() -> None:
    utc = {"at": datetime(2026, 9, 5, 8, tzinfo=UTC)}
    plus_one = {"at": datetime.fromisoformat("2026-09-05T09:00:00+01:00")}
    assert canonical_digest(utc) == canonical_digest(plus_one)


def test_python_matches_committed_cross_language_digest_vectors() -> None:
    vectors = json.loads(Path("reference/digest-vectors.json").read_text())
    for vector in vectors:
        payload = vector["canonical_json"].encode()
        assert f"sha256:{hashlib.sha256(payload).hexdigest()}" == vector["sha256"]
    timestamp = {"observed_at": datetime.fromisoformat("2026-09-05T09:00:00+01:00")}
    assert canonical_bytes(timestamp).decode() == vectors[-1]["canonical_json"]


def test_synthesis_rejects_claim_evidence_outside_its_evidence_set() -> None:
    synthesis = build_dogfood_snapshot().syntheses[0]
    data = synthesis.model_dump(mode="python", exclude={"content_digest"})
    data["candidate_claims"] = (
        EvidenceClaim(claim_id="claim_bad", text="Unsupported", evidence_refs=("missing",)),
    )
    with pytest.raises(ValidationError, match="absent from synthesis"):
        ResearchSynthesis.model_validate(data)


def test_untraceable_brief_is_always_blocking() -> None:
    snapshot = build_dogfood_snapshot()
    brief = snapshot.briefs[0].model_copy(update={"source_refs": ("missing",)})
    review = validate_delivery_bundle(
        brief=brief,
        artifact=snapshot.artifacts[0],
        manifest=snapshot.manifests[0],
        publication=publication_profiles()[0],
        synthesis=snapshot.syntheses[0],
        channel_plan=_channel_plan(snapshot, 0),
        created_at=NOW,
        revision=1,
    )
    assert review.source_claim_traceability is False
    assert review.ready_for_approval is False
    assert "ZEO_CREATOR_MISSING_CLAIM_TRACE" in {item.code for item in review.blocking_findings}


def test_empty_extracted_text_and_bad_artifact_proof_fail_closed() -> None:
    snapshot = build_dogfood_snapshot()
    artifact = snapshot.artifacts[0].model_copy(update={"extracted_text": ""})
    proof = snapshot.manifests[0].artifact_digest_proof.model_copy(update={"byte_length": 1})
    manifest = snapshot.manifests[0].model_copy(update={"artifact_digest_proof": proof})
    review = validate_delivery_bundle(
        brief=snapshot.briefs[0],
        artifact=artifact,
        manifest=manifest,
        publication=publication_profiles()[0],
        synthesis=snapshot.syntheses[0],
        channel_plan=_channel_plan(snapshot, 0),
        created_at=NOW,
        revision=1,
    )
    codes = {item.code for item in review.blocking_findings}
    assert {"ZEO_CREATOR_EXTRACTED_TEXT_MISSING", "ZEO_CREATOR_ARTIFACT_DIGEST_UNVERIFIED"} <= codes
    assert review.ready_for_approval is False


def _channel_plan(snapshot: DogfoodSnapshot, index: int) -> ChannelPlan:
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
