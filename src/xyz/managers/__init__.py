"""
Stub implementation — replace with real parsers when Teammate 1 integrates.
The Package dataclass and ManagerRegistry interface are the contract the TUI
and AI layers depend on; the internals here are fake until then.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class Package:
    name: str
    version: str
    manager: str
    size: str = "—"
    is_orphan: bool = False


class ManagerRegistry:
    """Returns fake packages until Teammate 1 wires up real subprocess parsers."""

    _FAKE: list[Package] = [
        Package("requests",    "2.31.0",  "pip",  "120 KB"),
        Package("textual",     "8.2.5",   "pip",  "2.1 MB"),
        Package("numpy",       "1.24.3",  "pip",  "15 MB"),
        Package("rich",        "15.0.0",  "pip",  "890 KB"),
        Package("pydantic",    "2.13.3",  "pip",  "1.2 MB"),
        Package("react",       "18.2.0",  "npm",  "4.5 MB"),
        Package("lodash",      "4.17.21", "npm",  "1.4 MB", is_orphan=True),
        Package("typescript",  "5.1.6",   "npm",  "55 MB"),
        Package("webpack",     "5.88.0",  "npm",  "28 MB",  is_orphan=True),
        Package("wget",        "1.21.4",  "brew", "3.2 MB"),
        Package("git",         "2.41.0",  "brew", "42 MB"),
        Package("ripgrep",     "13.0.0",  "brew", "5.6 MB", is_orphan=True),
        Package("node",        "20.5.0",  "brew", "60 MB"),
        Package("vim",         "9.0.0",   "brew", "8.1 MB"),
    ]

    async def scan_all(self) -> list[Package]:
        await asyncio.sleep(0.4)
        return list(self._FAKE)

    async def update(self, pkg: Package) -> None:
        await asyncio.sleep(1.2)

    async def delete(self, pkg: Package) -> None:
        await asyncio.sleep(0.8)

    async def upgrade_all(self) -> None:
        await asyncio.sleep(2.0)
