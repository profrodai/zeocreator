"""Inject a provider-neutral evidence connector into research synthesis."""

import json
from datetime import UTC, datetime

from zeo_core.tools import invoke_sync

from zeo_creator.capabilities.research_synthesis import ResearchSynthesisResponse
from zeo_creator.contracts.evidence import EvidenceItem, EvidenceQuery
from zeo_creator.contracts.publications import PublicationProfile
from zeo_creator.registry import capability_registry
from zeo_creator.runtime import make_context


class InMemoryEvidenceSource:
    """A local adapter with the same shape as a runner-supplied connector proxy."""

    def retrieve(
        self,
        query: EvidenceQuery,
        publication: PublicationProfile,
    ) -> tuple[EvidenceItem, ...]:
        return (
            EvidenceItem(
                evidence_id="evidence_bounded_retries",
                created_at=datetime(2026, 9, 5, 8, tzinfo=UTC),
                organization_id=publication.organization_id,
                publication_id=publication.publication_id,
                source_kind=query.source_kind,
                source_ref="archive/article-42",
                connection_ref=query.connection_ref,
                observed_at=datetime(2026, 9, 5, 7, tzinfo=UTC),
                author_or_origin="Example engineering archive",
                title="Bounded retries make automation predictable",
                excerpt_or_summary="Retry limits reduce runaway automation risk.",
                canonical_url="https://example.com/bounded-retries",
                publication_scope=publication.publication_id,
            ),
        )


def main() -> None:
    capability = capability_registry().get("creator.research_synthesis@1.0.0")
    request = capability.request_model.model_validate(capability.definition.examples[0].request)
    result = invoke_sync(
        capability,
        request,
        make_context(
            capability_name="research_synthesis",
            services={"creator.evidence_source": InMemoryEvidenceSource()},
        ),
    )
    if not isinstance(result.data, ResearchSynthesisResponse):
        raise RuntimeError(result.human_message)

    synthesis = result.data.synthesis
    print(
        json.dumps(
            {
                "publication_id": synthesis.publication_id,
                "themes": synthesis.themes,
                "evidence_refs": synthesis.evidence_refs,
                "coverage_gaps": synthesis.coverage_gaps,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
