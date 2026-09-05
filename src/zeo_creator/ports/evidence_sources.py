"""Provider-neutral evidence read port supplied by a controlling runtime."""

from typing import Protocol

from zeo_creator.contracts.evidence import EvidenceItem, EvidenceQuery
from zeo_creator.contracts.publications import PublicationProfile


class EvidenceSourcePort(Protocol):
    def retrieve(
        self,
        query: EvidenceQuery,
        publication: PublicationProfile,
    ) -> tuple[EvidenceItem, ...]: ...
