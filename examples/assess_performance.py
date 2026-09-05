"""Inject read-only metrics and produce a publication-scoped assessment."""

import json
from datetime import UTC, datetime

from zeo_core.tools import invoke_sync

from zeo_creator.capabilities.assess_performance import AssessPerformanceResponse
from zeo_creator.contracts.performance import MetricAggregation, MetricObservation, MetricsQuery
from zeo_creator.registry import capability_registry
from zeo_creator.runtime import make_context


class InMemoryMetricsSource:
    def retrieve(self, query: MetricsQuery) -> tuple[MetricObservation, ...]:
        return (
            MetricObservation(
                observation_id="observation_example_views",
                created_at=datetime(2026, 9, 5, 8, tzinfo=UTC),
                organization_id="org_example",
                publication_id=query.publication_id,
                provider_kind=query.provider_kind,
                connection_ref=query.connection_ref,
                destination_account_ref=query.destination_account_ref,
                observed_at=datetime(2026, 9, 5, 8, tzinfo=UTC),
                artifact_ref="artifact_example",
                publication_operation_ref="operation_example",
                metric_name="views",
                metric_value=1_200,
                unit="ratio",
                aggregation=MetricAggregation.RATE,
                denominator="impressions",
                attribution_window=query.observation_window,
                objective_mapping="audience_reach",
                baseline=0.08,
                target=0.12,
                normalized_rate=0.1,
                provider_definition="Provider-defined qualified views",
                provider_definition_version="2026-09-01",
            ),
        )


def main() -> None:
    capability = capability_registry().get("creator.assess_performance@1.0.0")
    request = capability.request_model.model_validate(capability.definition.examples[0].request)
    result = invoke_sync(
        capability,
        request,
        make_context(
            capability_name="assess_performance",
            services={"creator.metrics_source": InMemoryMetricsSource()},
        ),
    )
    if not isinstance(result.data, AssessPerformanceResponse):
        raise RuntimeError(result.human_message)

    assessment = result.data.assessment
    print(
        json.dumps(
            {
                "publication_id": assessment.publication_id,
                "relative_to_objective": assessment.performance_relative_to_objective,
                "confidence": assessment.confidence,
                "hypotheses": assessment.hypotheses,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
