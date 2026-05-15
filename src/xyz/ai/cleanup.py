from __future__ import annotations

from typing import Any

import json
import logging
import re

from .client import GeminiClient
from .prompts import CLEANUP_PROMPT

logger = logging.getLogger(__name__)


async def smart_cleanup(
    client: GeminiClient,
    packages: list[dict[str, Any]],
    dupe_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Analyze installed packages and return cleanup recommendations.

    Each recommendation dict has keys: name, manager, verdict, reason.
    verdict is "remove" or "review".
    Returns [] when AI is unavailable or nothing actionable is found.
    """
    if not client.is_available:
        return []

    sample = packages[:300]
    pkg_list = "\n".join(
        f"- {p['name']} ({p['manager']} {p['version']})" for p in sample
    )

    dupes_section = ""
    if dupe_names:
        names = ", ".join(sorted(dupe_names))
        dupes_section = (
            f"\nThe app has already detected these cross-manager duplicates "
            f"(same package name, different managers): {names}\n"
            f"Flag ALL of these as at least 'review'.\n"
        )

    prompt = CLEANUP_PROMPT.format(package_list=pkg_list, dupes_section=dupes_section)
    response = await client.generate(prompt, temperature=0.2, max_tokens=4096)
    logger.debug("Cleanup raw response: %s", response[:500])

    try:
        # Greedy match: from first '[' to last ']'
        match = re.search(r"\[.*\]", response, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if isinstance(data, list):
                return [r for r in data if isinstance(r, dict) and "name" in r]
    except Exception as exc:
        logger.warning("Failed to parse cleanup response: %s", exc)

    return []
