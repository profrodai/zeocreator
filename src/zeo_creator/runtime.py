"""Small context constructor for examples and tests; production runners own this."""

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from zeo_core.tools import ToolContext


def make_context(
    *,
    capability_name: str,
    services: Mapping[str, Any] | None = None,
    work_dir: Path | str = ".",
) -> ToolContext:
    """Construct a bounded local context without credentials or workflow state."""
    root = Path(work_dir).resolve()
    return ToolContext(
        run_id=f"example-{capability_name}",
        tool_name=capability_name,
        tool_version="1.0.0",
        logger=logging.getLogger(f"zeo_creator.{capability_name}"),
        fs=None,
        work_dir=str(root),
        output_dir=str(root),
        services=services or {},
    )
