"""XYZ AI layer -- Gemini-powered package intelligence.

This module exposes convenience functions that match the signatures the
TUI layer expects.  Internally each function delegates to the real
implementation in ``explainer``, ``orphan``, and ``search``, passing
the shared :class:`GeminiClient` singleton automatically.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

from xyz.ai.client import GeminiClient
from xyz.ai.cleanup import smart_cleanup as _cleanup
from xyz.ai.cve import check_package_cves as _check_cves
from xyz.ai.explainer import explain_package as _explain, stream_explain_package as _stream_explain
from xyz.ai.orphan import assess_orphan_risk as _assess, stream_assess_orphan_risk as _stream_assess
from xyz.ai.search import natural_language_search as _nl_search


# ── Public convenience wrappers (TUI-facing) ─────────────────────────────
# The TUI calls these WITHOUT a client argument; the singleton is injected
# automatically so Teammate 2's code doesn't need to change at all.


async def explain_package(name: str, manager: str, version: str) -> str:
    """Explain a package in plain English via Gemini.

    Returns a user-friendly string in all cases (never raises).
    """
    client = GeminiClient.get_instance()
    return await _explain(client, name, manager, version)


async def assess_orphan_risk(name: str, manager: str) -> str:
    """Assess the risk of removing an orphaned package.

    Returns a risk level and explanation (never raises).
    """
    client = GeminiClient.get_instance()
    return await _assess(client, name, manager)


async def natural_language_search(query: str, package_names: list[str]) -> list[str]:
    """Map a free-text query to matching installed package names.

    Returns a list of matching names, or ``[]`` on failure / offline.
    """
    client = GeminiClient.get_instance()
    return await _nl_search(client, query, package_names)


async def stream_explain_package(name: str, manager: str, version: str) -> AsyncGenerator[str, None]:
    """Stream a plain-English package explanation, yielding text chunks."""
    client = GeminiClient.get_instance()
    async for chunk in _stream_explain(client, name, manager, version):
        yield chunk


async def stream_assess_orphan_risk(name: str, manager: str) -> AsyncGenerator[str, None]:
    """Stream an orphan risk assessment, yielding text chunks."""
    client = GeminiClient.get_instance()
    async for chunk in _stream_assess(client, name, manager):
        yield chunk


async def smart_cleanup(packages: list[dict[str, Any]], dupe_names: set[str] | None = None) -> list[dict[str, Any]]:
    """Analyze all installed packages and return cleanup recommendations.

    Each dict has: name, manager, verdict ("remove"|"review"), reason.
    Returns [] when AI is unavailable or nothing actionable is found.
    """
    client = GeminiClient.get_instance()
    return await _cleanup(client, packages, dupe_names=dupe_names)


async def check_package_cves(name: str, manager: str, version: str) -> dict[str, Any]:
    """Check a package for known CVEs using Gemini with Google Search grounding.

    Returns a dict with keys:
        severity  -- "none" | "low" | "medium" | "high" | "critical" | "unknown"
        cve_ids   -- list of CVE ID strings (may be empty)
        summary   -- human-readable sentence about findings
    """
    client = GeminiClient.get_instance()
    return await _check_cves(client, name, manager, version)


__all__ = [
    "GeminiClient",
    "explain_package",
    "stream_explain_package",
    "assess_orphan_risk",
    "stream_assess_orphan_risk",
    "natural_language_search",
    "smart_cleanup",
    "check_package_cves",
]
