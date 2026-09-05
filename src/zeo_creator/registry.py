"""Explicit capability discovery catalog for any controlling runner."""

from zeo_core.adapters.llm_tools import OpenAIFunctionTool, project_openai_tool
from zeo_core.contracts import CapabilityManifest
from zeo_core.tools import BoundCapability, CapabilityRegistry, bound_capability_of

from zeo_creator.capabilities import (
    assess_performance,
    create_ducktyper_brief,
    plan_daily_portfolio,
    prepare_distribution,
    research_synthesis,
    validate_delivery,
)

CAPABILITIES: tuple[BoundCapability, ...] = tuple(
    bound_capability_of(item)
    for item in (
        research_synthesis,
        plan_daily_portfolio,
        create_ducktyper_brief,
        validate_delivery,
        prepare_distribution,
        assess_performance,
    )
)


def capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    for item in CAPABILITIES:
        registry.register(item)
    return registry


def capability_manifests() -> tuple[CapabilityManifest, ...]:
    return tuple(capability_registry().manifests())


def openai_tool_projections() -> tuple[OpenAIFunctionTool, ...]:
    projections: list[OpenAIFunctionTool] = []
    for manifest in capability_manifests():
        result = project_openai_tool(manifest)
        if not result.ok or result.tool is None:
            detail = result.incompatibility or "unknown incompatibility"
            raise ValueError(f"Cannot project {manifest.id.canonical()}: {detail}")
        projections.append(result.tool)
    return tuple(projections)


__all__ = [
    "CAPABILITIES",
    "capability_manifests",
    "capability_registry",
    "openai_tool_projections",
]
