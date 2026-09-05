.PHONY: help setup sync test lint typecheck format check verify clean lock update \
	cli version doctor capabilities reference reference-check docs docs-serve examples

UV ?= uv
ZEO_CREATOR := $(UV) run zeo-creator
ARGS ?=

help:
	@echo "ZEO Creator — capability package diagnostics"
	@echo ""
	@echo "  make setup          Install the exact locked environment"
	@echo "  make verify         Lint, strict type-check, and test"
	@echo "  make doctor         Verify Python/Zeocore/manifests/projections"
	@echo "  make capabilities   List the six public capabilities"
	@echo "  make reference      Regenerate JSON schemas and dogfood samples"
	@echo "  make docs           Build the documentation site in strict mode"
	@echo "  make docs-serve     Serve docs locally with live reload"
	@echo "  make examples       Run every public example"
	@echo "  make version        Show the installed distribution version"
	@echo "  make cli ARGS='…'   Invoke diagnostics directly"

setup: sync

sync:
	$(UV) sync --frozen

lock:
	$(UV) lock

update:
	$(UV) lock --upgrade
	$(UV) sync

cli:
	$(ZEO_CREATOR) $(ARGS)

version:
	$(ZEO_CREATOR) --version

doctor:
	$(ZEO_CREATOR) doctor --json

capabilities:
	$(ZEO_CREATOR) capabilities

reference:
	$(UV) run python -m scripts.export_reference_artifacts

test:
	$(UV) run pytest -q

lint:
	$(UV) run ruff check src tests scripts examples

typecheck:
	$(UV) run mypy src/zeo_creator examples

format:
	$(UV) run ruff format src tests scripts examples

docs:
	$(UV) run mkdocs build --strict

docs-serve:
	$(UV) run mkdocs serve

examples:
	$(UV) run python examples/inspect_capabilities.py
	$(UV) run python examples/create_brief.py
	$(UV) run python examples/research_connector.py
	$(UV) run python examples/validate_and_prepare.py
	$(UV) run python examples/assess_performance.py
	$(UV) run python examples/complete_daily_portfolio.py

reference-check: reference
	git diff --exit-code -- reference

check: lint typecheck test reference-check docs

verify: check

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml htmlcov dist build site
