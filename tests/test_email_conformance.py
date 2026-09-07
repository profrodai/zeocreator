"""Installed public surfaces, non-circular digest checks and input-only invocation."""

import hashlib
import json
import socket
from importlib.resources import files
from pathlib import Path

import pytest
from zeo_core.contracts import CapabilityStatus, EffectKind
from zeo_core.tools import invoke_sync

from scripts.export_reference_artifacts_v2 import MODELS
from tests.test_email_marketing import reviewed, revised
from zeo_creator.contract_schemas import read_contract_schema
from zeo_creator.contracts.common import canonical_digest
from zeo_creator.contracts.email_marketing import (
    EmailReviewEvidence,
    PersonalizationDeclaration,
)
from zeo_creator.errors import CreatorDomainError
from zeo_creator.reference import email_inputs as x
from zeo_creator.reference.email_workflow import EmailReferenceRun, three_publications
from zeo_creator.registry import CAPABILITIES
from zeo_creator.runtime import make_context
from zeo_creator.services import email_marketing as s


def test_all_email_capabilities_invoke_without_network_or_acquisition(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("canonical email capability attempted network acquisition")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
    capabilities = [bound for bound in CAPABILITIES if "email" in bound.definition.tags]
    assert len(capabilities) == 7
    for bound in capabilities:
        assert bound.definition.effects.kinds == frozenset({EffectKind.READ})
        assert not bound.definition.requirements.services
        for example in bound.definition.examples:
            request = bound.request_model.model_validate(example.request)
            result = invoke_sync(
                bound, request, make_context(capability_name=bound.definition.canonical_id())
            )
            assert result.status == CapabilityStatus.success
            assert result.data is not None


def test_three_publication_reference_records_the_complete_data_flow():
    runs = three_publications()
    assert len({run.publication.publication_id for run in runs}) == 3
    for run in runs:
        assert len(run.drafts) == 4 and len(run.sequence.steps) == 3
        assert len(run.packages) == len(run.proposals) == len(run.receipts) == 8
        assert run.sequence.steps[0].message_plan == run.plans[1].binding()
        assert run.observations[0].operation == run.proposals[1].binding()
        assert run.observations[0].retrieval_receipt.digest == canonical_digest(run.receipts)
        assert run.assessment.observations == run.observations
        for package, proposal, receipt in zip(
            run.packages, run.proposals, run.receipts, strict=True
        ):
            assert proposal.material.delivery == package.binding()
            assert receipt.creator_artifact == package.binding()
            assert receipt.simulation is True
        production = run.packages[1]
        test_proof = next(row for row in production.material.proofs if row.kind == "test_send")
        assert test_proof.receipt_ref == run.receipts[0].receipt_id
        assert run.assessment.completeness == "partial"


def test_packaged_email_schemas_match_python_and_include_every_new_contract():
    for name, model in MODELS:
        assert read_contract_schema(name, "1") == model.model_json_schema()
    root = files("zeo_creator").joinpath("reference_artifacts")
    examples = json.loads(root.joinpath("email-marketing.json").read_text())
    runs = [EmailReferenceRun.model_validate(row) for row in examples]
    assert len({run.publication.publication_id for run in runs}) == 3
    assert (
        "Public Zeocore integration dependency"
        in root.joinpath("docs/guides/email-marketing.md").read_text()
    )


def test_committed_email_vectors_verify_independently_of_creator_digest():
    values = json.loads(Path("reference/email-digest-vectors.json").read_text())
    assert len(values) == 18
    for vector in values:
        assert (
            "sha256:" + hashlib.sha256(vector["canonical_json"].encode()).hexdigest()
            == vector["sha256"]
        )
    assert any("package" in vector["name"] for vector in values)


def test_preparation_rejects_forged_ready_review_and_expired_review_evidence():
    plan, draft, review = reviewed()
    no_evidence = revised(review, evidence=())
    with pytest.raises(CreatorDomainError, match="review_not_ready"):
        s.prepare_delivery(plan, draft, no_evidence, x.snapshot(), x.proofs(draft), x.NOW)
    expiring = tuple(revised(row, valid_until=x.NOW.replace(hour=13)) for row in review.evidence)
    review = revised(review, evidence=expiring)
    with pytest.raises(CreatorDomainError, match="review_evidence_stale"):
        s.prepare_delivery(
            plan, draft, review, x.snapshot(), x.proofs(draft), x.NOW.replace(hour=14)
        )


def test_personalization_needs_bound_resolution_evidence_without_receiving_values():
    token = PersonalizationDeclaration(name="greeting", source_policy="symbolic/greeting")
    plan = revised(
        x.plan(), personalization=(token,), subject_direction="{{greeting}} A practical capability"
    )
    draft = s.compose_message(plan, x.sections(), x.NOW)
    assert draft.subject.startswith("{{greeting}}")
    evidence = x.evidence(draft)
    unresolved = s.review_message(x.profile(), plan, draft, evidence, x.NOW)
    assert not unresolved.ready_for_human_approval
    resolution = EmailReviewEvidence(
        artifact_id="publication-a/resolution-proof",
        created_at=x.NOW,
        organization_id="example-org",
        publication_id="publication-a",
        draft=draft.binding(),
        check="personalization",
        passed=True,
        policy=x.ref("symbolic-policy"),
        receipt_ref="publication-a/simulated-preview-resolution",
        valid_until=x.LATER,
    )
    resolved = s.review_message(x.profile(), plan, draft, (*evidence, resolution), x.NOW)
    assert resolved.ready_for_human_approval
    item = s.prepare_delivery(plan, draft, resolved, x.snapshot(), x.proofs(draft), x.NOW)
    assert item.material.draft.personalization == (token,)
    assert "{{greeting}}" in item.material.draft.subject
    wrong = revised(resolution, draft=x.draft().binding())
    with pytest.raises(CreatorDomainError):
        s.review_message(x.profile(), plan, draft, (*evidence, wrong), x.NOW)


def test_exact_body_whitespace_is_not_silently_stripped():
    original = x.draft()
    draft = revised(
        original, html="\n" + original.html + "\n", plain_text="\n" + original.plain_text + "\n"
    )
    assert draft.html.startswith("\n") and draft.plain_text.endswith("\n")
    assert draft.content_digest != original.content_digest


@pytest.mark.parametrize("kind", ["preview", "test_send"])
def test_missing_production_proofs_fail(kind):
    plan, draft, review = reviewed()
    with pytest.raises(CreatorDomainError, match="requires_preview_and_test"):
        s.prepare_delivery(
            plan,
            draft,
            review,
            x.snapshot(),
            tuple(row for row in x.proofs(draft) if row.kind != kind),
            x.NOW,
        )


def test_all_original_v1_schemas_are_preserved():
    baseline = json.loads(Path("reference/email-compatibility-baseline-v1.json").read_text())
    assert baseline["source_commit"] == "4d807f68c330a075e27c7b4714ca0ebf2e88f948"
    for name, digest in baseline["sha256_by_path"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
