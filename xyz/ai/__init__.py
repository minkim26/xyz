"""XYZ AI layer — Gemini-powered package intelligence."""

from xyz.ai.client import GeminiClient
from xyz.ai.explainer import explain_package
from xyz.ai.orphan import assess_orphan_risk
from xyz.ai.search import natural_language_search

__all__ = [
    "GeminiClient",
    "explain_package",
    "assess_orphan_risk",
    "natural_language_search",
]
