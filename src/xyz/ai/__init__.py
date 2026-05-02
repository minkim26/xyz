"""
Stub implementation — replace with real Gemini calls when Teammate 3 integrates.
"""

from __future__ import annotations

import asyncio
import os


async def explain_package(name: str, manager: str, version: str) -> str:
    if not os.getenv("GEMINI_API_KEY"):
        return "Set GEMINI_API_KEY to enable AI explanations."
    await asyncio.sleep(0.3)
    return f"[Gemini explanation for {name} ({manager} {version}) goes here.]"


async def assess_orphan_risk(name: str, manager: str) -> str:
    if not os.getenv("GEMINI_API_KEY"):
        return "Set GEMINI_API_KEY to enable orphan risk assessment."
    await asyncio.sleep(0.3)
    return f"[Orphan risk assessment for {name} goes here.]"
