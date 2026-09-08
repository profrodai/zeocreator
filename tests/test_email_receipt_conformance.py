"""The shared corpus must detect permissive, rejecting and incomplete implementations."""

import copy

import pytest

from zeo_creator.reference.email_receipt_conformance import (
    creator_validators,
    packaged_cases,
    verify_cases,
)


def test_creator_matches_portable_cases():
    corpus = packaged_cases()
    assert len(corpus["cases"]) == 36
    assert verify_cases(corpus, creator_validators()) == ()
    assert corpus["authentication_proven"] is False


def test_corpus_cannot_bless_accept_everything():
    validators = {name: lambda value: value for name in creator_validators()}
    failures = verify_cases(packaged_cases(), validators)
    assert "migration-cannot-return-source-object-as-target" in failures
    assert "activate_sequence_revision-from-paused" in failures


def test_corpus_cannot_bless_reject_everything():
    def reject(value):
        raise ValueError("rejected")

    validators = dict.fromkeys(creator_validators(), reject)
    assert "broadcast-correspondence" in verify_cases(packaged_cases(), validators)


def test_missing_validator_refuses_instead_of_skipping():
    validators = creator_validators()
    validators.pop("correspondence")
    with pytest.raises(ValueError, match="every declared validator"):
        verify_cases(packaged_cases(), validators)


@pytest.mark.parametrize("section", ["cases", "schemas"])
def test_modified_corpus_refuses(section):
    corpus = copy.deepcopy(packaged_cases())
    if section == "cases":
        corpus["cases"][0]["valid"] = not corpus["cases"][0]["valid"]
    else:
        corpus["schemas"]["result"]["description"] = "changed"
    with pytest.raises(ValueError, match="digest mismatch"):
        verify_cases(corpus, creator_validators())
