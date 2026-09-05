# Assess performance

Performance assessment is a read-only, publication-scoped capability. It turns
authorized metric observations into learnings and hypotheses without creating
future commitments.

## Implement the metrics port

```python
from zeo_creator.contracts.performance import MetricObservation, MetricsQuery


class MyMetricsSource:
    def retrieve(self, query: MetricsQuery) -> tuple[MetricObservation, ...]:
        rows = analytics_connector.read_metrics(
            connection_ref=query.connection_ref,
            destination_account_ref=query.destination_account_ref,
            starts_at=query.observation_window.starts_at,
            ends_at=query.observation_window.ends_at,
            operation_refs=query.operation_refs,
        )
        return tuple(to_metric_observation(row, query) for row in rows)
```

Inject it as `creator.metrics_source` in the invocation context.

## Runnable example

```python
--8<-- "examples/assess_performance.py"
```

```console
uv run python examples/assess_performance.py
```

## Interpret the output

A `DailyPerformanceAssessment` contains:

- metric observations and their observation window;
- provider, connection, and destination provenance;
- artifact and publication-operation references;
- performance relative to the stated objective;
- confidence and data gaps;
- reusable learnings;
- explicitly labeled hypotheses; and
- proposed follow-up work for a runtime or human to consider.

Run one assessment per publication. A blended cross-brand report destroys the
scope needed to interpret results safely.

!!! note "Assessment is not scheduling"

    Proposed follow-up work is output data. The capability does not create a
    future commitment, schedule a job, or alter the next editorial plan.
