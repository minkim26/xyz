from __future__ import annotations

import asyncio
import shutil

from .base import BaseManager, Package
from .npm import NpmManager
from .pip import PipManager

_DEFAULT_TIMEOUT = 10.0


class ManagerRegistry:
    def __init__(
        self,
        managers: list[BaseManager] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._managers = managers if managers is not None else _detect_managers()
        self._timeout = timeout

    async def scan_all(self) -> list[Package]:
        tasks = [
            asyncio.wait_for(m.list(), timeout=self._timeout)
            for m in self._managers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        packages: list[Package] = []
        for result in results:
            if isinstance(result, list):
                packages.extend(result)
            # TimeoutError, subprocess errors, etc. are swallowed per-manager
        return packages


def _detect_managers() -> list[BaseManager]:
    detected: list[BaseManager] = []
    for manager in (PipManager(), NpmManager()):
        if manager.is_available():
            detected.append(manager)
    return detected
