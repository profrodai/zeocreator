.PHONY: help setup sync test lint typecheck format check verify clean lock update \
	cli version doctor capabilities reference reference-check

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
	$(UV) run ruff check src tests scripts

typecheck:
	$(UV) run mypy src/zeo_creator

format:
	$(UV) run ruff format src tests scripts

reference-check: reference
	git diff --exit-code -- reference

check: lint typecheck test reference-check

verify: check

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage coverage.xml htmlcov dist build
