"""Package explainer — Gemini-powered plain-English package descriptions.

When a user selects a package in the TUI, this module asks Gemini to
explain what it does, why it's installed, and whether it's safe to remove.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from xyz.ai.prompts import EXPLAIN_PROMPT

if TYPE_CHECKING:
    from xyz.ai.client import GeminiClient

logger = logging.getLogger(__name__)

# Simple in-memory cache: (name, manager) -> explanation text
_cache: dict[tuple[str, str], str] = {}


async def explain_package(
    client: "GeminiClient",
    name: str,
    manager: str,
    version: str = "unknown",
) -> str:
    """Return a plain-English explanation of a package.

    Results are cached so re-selecting a package doesn't burn another
    API call.

    Args:
        client: The shared GeminiClient instance.
        name: Package name (e.g. ``"numpy"``).
        manager: Manager that owns the package (e.g. ``"pip"``).
        version: Installed version string.

    Returns:
        Formatted explanation text ready for the detail pane.
    """
    cache_key = (name, manager)
    if cache_key in _cache:
        logger.debug("Cache hit for %s/%s", manager, name)
        return _cache[cache_key]

    prompt = EXPLAIN_PROMPT.format(name=name, manager=manager, version=version)
    result = await client.generate(prompt)

    # Only cache successful responses (not error messages)
    if not result.startswith(("\ud83d\udd11", "\u26a0\ufe0f", "\u23f3")):
        _cache[cache_key] = result

    return result


def clear_cache() -> None:
    """Clear the explanation cache — useful for testing."""
    _cache.clear()
