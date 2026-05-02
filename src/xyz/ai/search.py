"""Natural language search -- Gemini maps free-text queries to package names.

Triggered when the user types a query with a ``?`` prefix in the TUI
search bar (e.g. ``?anything related to machine learning``).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from xyz.ai.prompts import NL_SEARCH_PROMPT

if TYPE_CHECKING:
    from xyz.ai.client import GeminiClient

logger = logging.getLogger(__name__)


async def natural_language_search(
    client: "GeminiClient",
    query: str,
    package_names: list[str],
) -> list[str]:
    """Use Gemini to find packages matching a natural language description.

    Args:
        client: The shared GeminiClient instance.
        query: Free-text search query (e.g. ``"machine learning"``).
        package_names: Full list of installed package names to search within.

    Returns:
        List of matching package name strings, or an empty list on failure.
    """
    if not package_names:
        return []

    if not client.is_available:
        logger.info("NL search unavailable -- no API key")
        return []

    # Format the package list as a compact comma-separated string
    names_str = ", ".join(package_names)
    prompt = NL_SEARCH_PROMPT.format(package_names=names_str, query=query)

    result = await client.generate(prompt, max_tokens=1024)

    # Parse the JSON array from the response
    return _parse_package_list(result, package_names)


def _parse_package_list(response: str, valid_names: list[str]) -> list[str]:
    """Extract a JSON array of package names from Gemini's response.

    Performs validation to ensure only names that actually exist in the
    installed package list are returned.
    """
    # Strip markdown code fences if Gemini wraps the response
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse NL search response as JSON: %s", text)
        return []

    if not isinstance(parsed, list):
        logger.warning("NL search response is not a list: %s", type(parsed))
        return []

    # Validate: only return names that are actually in the installed list
    valid_set = set(valid_names)
    matched = [name for name in parsed if isinstance(name, str) and name in valid_set]

    logger.info("NL search matched %d packages for query", len(matched))
    return matched
