from __future__ import annotations

import asyncio
from dataclasses import replace
import logging

from .base import BaseManager, Package
from .brew import BrewManager
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

    def get_manager(self, name: str) -> BaseManager | None:
        return next((m for m in self._managers if m.name == name), None)

    async def scan_all(self) -> list[Package]:
        tasks = [self._scan_manager(m) for m in self._managers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        packages: list[Package] = []
        for manager, result in zip(self._managers, results):
            if isinstance(result, tuple):
                listed, orphan_keys = result
                packages.extend([
                    replace(pkg, is_orphan=(pkg.name.lower(), pkg.manager) in orphan_keys)
                    for pkg in listed
                ])
                continue
            if isinstance(result, BaseException):
                if not isinstance(result, Exception):
                    raise result
                logger.warning("Manager %s scan failed: %s", manager.name, result)
        return packages

    async def _scan_manager(self, manager: BaseManager) -> tuple[list[Package], set[tuple[str, str]]]:
        listed = await asyncio.wait_for(manager.list(), timeout=self._timeout)

        orphan_keys: set[tuple[str, str]] = set()
        try:
            orphan_pkgs = await asyncio.wait_for(
                manager.check_orphans(), timeout=self._timeout
            )
            orphan_keys = {(p.name.lower(), p.manager) for p in orphan_pkgs}
        except BaseException as orphan_err:
            if not isinstance(orphan_err, Exception):
                raise orphan_err
            logger.warning("Manager %s orphan check failed: %s", manager.name, orphan_err)

        return listed, orphan_keys

    async def update(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        for manager in self._managers:
            if manager.name == pkg.manager:
                return await manager.update(pkg.name, dry_run=dry_run)
        return False, f"Manager {pkg.manager} not found."

    async def delete(self, pkg: Package, dry_run: bool = False) -> tuple[bool, str]:
        for manager in self._managers:
            if manager.name == pkg.manager:
                return await manager.delete(pkg.name, dry_run=dry_run)
        return False, f"Manager {pkg.manager} not found."


def _detect_managers() -> list[BaseManager]:
    detected: list[BaseManager] = []
    for manager in (PipManager(), NpmManager(), BrewManager()):
        if manager.is_available():
            detected.append(manager)
    return detected
