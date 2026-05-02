"""XYZ AI layer -- Gemini-powered package intelligence.

This module exposes convenience functions that match the signatures the
TUI layer expects.  Internally each function delegates to the real
implementation in ``explainer``, ``orphan``, and ``search``, passing
the shared :class:`GeminiClient` singleton automatically.
"""

from __future__ import annotations

from xyz.ai.client import GeminiClient
from xyz.ai.explainer import explain_package as _explain
from xyz.ai.orphan import assess_orphan_risk as _assess
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


__all__ = [
    "GeminiClient",
    "explain_package",
    "assess_orphan_risk",
    "natural_language_search",
]
