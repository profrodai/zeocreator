"""Historical exporter source must not relabel a current corpus under an old filename."""

import importlib

import pytest


@pytest.mark.parametrize("version", [6, 7])
def test_unversioned_legacy_exporters_refuse_before_writing_corpus(monkeypatch, version):
    exporter = importlib.import_module(f"scripts.export_reference_artifacts_v{version}")
    writes = []
    monkeypatch.setattr(exporter, "previous_export", lambda: None)
    monkeypatch.setattr(exporter, "write", lambda path, value: writes.append((path.name, value)))
    with pytest.raises(ValueError, match="Unversioned receipt export is retired"):
        exporter.main()
    assert not any("email-receipt-conformance" in name for name, _ in writes)


@pytest.mark.parametrize("version", [1, 3])
def test_only_current_corpus_can_be_rebuilt(monkeypatch, version):
    from zeo_creator.reference import email_receipt_conformance as corpus

    def unexpected_generation(*args):
        pytest.fail("unsupported version reached reference generation")

    monkeypatch.setattr(corpus, "run_program", unexpected_generation)
    with pytest.raises(ValueError, match="Only corpus v2 can be rebuilt"):
        corpus.build_cases(version=version)
