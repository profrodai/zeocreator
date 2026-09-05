"""Optional provider-neutral publication history boundary."""

from datetime import datetime
from typing import Protocol

from zeo_creator.contracts.editorial import ContentHistoryEntry


class ContentHistoryPort(Protocol):
    def recent(
        self,
        organization_id: str,
        publication_id: str,
        since: datetime,
    ) -> tuple[ContentHistoryEntry, ...]: ...
