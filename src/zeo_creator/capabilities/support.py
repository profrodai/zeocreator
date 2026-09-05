"""Shared Zeocore declarations for creator capabilities."""

from zeo_core.contracts import CapabilityRequirements, NetworkRequirement

EVIDENCE_READ_REQUIREMENTS = CapabilityRequirements(
    services=frozenset({"creator.evidence_source"}),
    network=NetworkRequirement(required=True),
)

METRICS_READ_REQUIREMENTS = CapabilityRequirements(
    services=frozenset({"creator.metrics_source"}),
    network=NetworkRequirement(required=True),
)
