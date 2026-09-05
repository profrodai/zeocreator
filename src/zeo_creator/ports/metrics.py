"""Provider-neutral performance read port supplied by a controlling runtime."""

from typing import Protocol

from zeo_creator.contracts.performance import MetricObservation, MetricsQuery


class MetricsSourcePort(Protocol):
    def retrieve(self, query: MetricsQuery) -> tuple[MetricObservation, ...]: ...
