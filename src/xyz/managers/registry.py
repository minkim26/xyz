from __future__ import annotations

import asyncio
import logging

from .base import BaseManager, Package
from .npm import NpmManager
from .pip import PipManager

_DEFAULT_TIMEOUT = 3.0

logger = logging.getLogger(__name__)


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
        for manager, result in zip(self._managers, results):
            if isinstance(result, list):
                packages.extend(result)
                continue
            if isinstance(result, BaseException):
                if not isinstance(result, Exception):
                    raise result
                logger.warning("Manager %s scan failed: %s", manager.name, result)
        return packages


def _detect_managers() -> list[BaseManager]:
    detected: list[BaseManager] = []
    for manager in (PipManager(), NpmManager()):
        if manager.is_available():
            detected.append(manager)
    return detected
