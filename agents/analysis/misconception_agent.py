from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def aggregate_misconceptions(subject: str, module_code: str) -> list[dict[str, Any]]:
    """Aggregate misconceptions from all examiner reports for a subject/module."""
    raise NotImplementedError


def generate_corrective_intervention(misconception_id: int) -> str:
    """Generate a corrective intervention for a misconception."""
    raise NotImplementedError


def get_active_misconceptions(
    subject: str | None = None,
    module_code: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return active misconceptions, optionally filtered by subject/module."""
    raise NotImplementedError
