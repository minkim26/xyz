"""CVE vulnerability scanning -- Gemini + Google Search grounding.

Checks whether an installed package version has known CVEs by querying
Gemini with Google Search grounding, which pulls live data from NVD,
OSV, and GitHub Security Advisories.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from xyz.ai.prompts import CVE_PROMPT

if TYPE_CHECKING:
    from xyz.ai.client import GeminiClient

logger = logging.getLogger(__name__)

# Cache: (name, manager, version) -> result dict
_cache: dict[tuple[str, str, str], dict] = {}

_ERROR_PREFIXES = ("AI features", "Gemini returned", "Rate limit", "Invalid API", "AI request")

SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _parse_response(text: str) -> dict:
    """Extract structured CVE data from Gemini's response text."""
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            severity = data.get("severity", "unknown").lower()
            if severity not in SEVERITY_ORDER:
                severity = "unknown"
            return {
                "severity": severity,
                "cve_ids": [c for c in data.get("cve_ids", []) if isinstance(c, str)],
                "summary": data.get("summary", "").strip(),
            }
    except Exception:
        logger.debug("CVE JSON parse failed, returning raw text")

    # Fallback: couldn't parse JSON — surface the raw response
    return {"severity": "unknown", "cve_ids": [], "summary": text[:400]}


async def check_package_cves(
    client: "GeminiClient",
    name: str,
    manager: str,
    version: str,
) -> dict:
    """Check a package for known CVEs using Gemini with Google Search grounding.

    Returns a dict with keys:
        severity  -- "none" | "low" | "medium" | "high" | "critical" | "unknown"
        cve_ids   -- list of CVE ID strings (may be empty)
        summary   -- human-readable sentence about findings
    """
    cache_key = (name, manager, version)
    if cache_key in _cache:
        logger.debug("CVE cache hit for %s/%s %s", manager, name, version)
        return _cache[cache_key]

    prompt = CVE_PROMPT.format(name=name, manager=manager, version=version)
    response = await client.generate_with_search(prompt, temperature=0.1)

    if response.startswith(_ERROR_PREFIXES):
        return {"severity": "unknown", "cve_ids": [], "summary": response}

    result = _parse_response(response)
    _cache[cache_key] = result
    return result


def clear_cache() -> None:
    """Clear the CVE cache."""
    _cache.clear()
