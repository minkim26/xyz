"""Package explainer -- Gemini-powered plain-English package descriptions.

When a user selects a package in the TUI, this module asks Gemini to
explain what it does, why it's installed, and whether it's safe to remove.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncGenerator

from xyz.ai.prompts import EXPLAIN_PROMPT

if TYPE_CHECKING:
    from xyz.ai.client import GeminiClient

logger = logging.getLogger(__name__)

# Simple in-memory cache: (name, manager) -> explanation text
_cache: dict[tuple[str, str], str] = {}

# Error prefixes used by client.py -- don't cache these
_ERROR_PREFIXES = ("AI features", "Gemini returned", "Rate limit", "Invalid API", "AI request")


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
    if not result.startswith(_ERROR_PREFIXES):
        _cache[cache_key] = result

    return result


async def stream_explain_package(
    client: "GeminiClient",
    name: str,
    manager: str,
    version: str = "unknown",
) -> AsyncGenerator[str, None]:
    """Stream a plain-English explanation, yielding text chunks as they arrive.

    On a cache hit, yields the cached text as a single chunk so the caller
    doesn't need to distinguish the two cases.
    """
    cache_key = (name, manager)
    if cache_key in _cache:
        logger.debug("Cache hit for %s/%s", manager, name)
        yield _cache[cache_key]
        return

    prompt = EXPLAIN_PROMPT.format(name=name, manager=manager, version=version)
    accumulated = ""
    async for chunk in client.stream_generate(prompt):
        accumulated += chunk
        yield chunk

    if accumulated and not accumulated.startswith(_ERROR_PREFIXES):
        _cache[cache_key] = accumulated


def clear_cache() -> None:
    """Clear the explanation cache -- useful for testing."""
    _cache.clear()
