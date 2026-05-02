"""Orphan risk assessment — Gemini evaluates whether removing an orphan is safe.

Called automatically when the user selects a package that has been flagged
as an orphan (installed as a dependency but its parent was removed).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from xyz.ai.prompts import ORPHAN_RISK_PROMPT

if TYPE_CHECKING:
    from xyz.ai.client import GeminiClient

logger = logging.getLogger(__name__)

# Cache: (name, manager) -> risk assessment text
_cache: dict[tuple[str, str], str] = {}


async def assess_orphan_risk(
    client: "GeminiClient",
    name: str,
    manager: str,
) -> str:
    """Assess the risk of removing an orphaned package.

    Args:
        client: The shared GeminiClient instance.
        name: Package name.
        manager: Manager that owns the package.

    Returns:
        Risk assessment text with level (Low/Medium/High) and explanation.
    """
    cache_key = (name, manager)
    if cache_key in _cache:
        logger.debug("Orphan cache hit for %s/%s", manager, name)
        return _cache[cache_key]

    prompt = ORPHAN_RISK_PROMPT.format(name=name, manager=manager)
    result = await client.generate(prompt)

    # Only cache successful responses
    if not result.startswith(("\U0001f511", "\u26a0\ufe0f", "\u23f3")):
        _cache[cache_key] = result

    return result


def clear_cache() -> None:
    """Clear the orphan assessment cache."""
    _cache.clear()
