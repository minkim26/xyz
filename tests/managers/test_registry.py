from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from xyz.managers.base import BaseManager, Package
from xyz.managers.registry import ManagerRegistry


def _mock_manager(packages: list[Package] | Exception) -> BaseManager:
    m = MagicMock(spec=BaseManager)
    if isinstance(packages, Exception):
        m.list = AsyncMock(side_effect=packages)
    else:
        m.list = AsyncMock(return_value=packages)
    return m


_PKG_A = Package(name="requests", version="2.31.0", manager="pip")
_PKG_B = Package(name="typescript", version="5.4.5", manager="npm")


async def test_registry_gathers_all_managers():
    registry = ManagerRegistry(managers=[
        _mock_manager([_PKG_A]),
        _mock_manager([_PKG_B]),
    ])
    packages = await registry.scan_all()
    assert len(packages) == 2
    assert _PKG_A in packages
    assert _PKG_B in packages


async def test_registry_swallows_failed_manager():
    registry = ManagerRegistry(managers=[
        _mock_manager(RuntimeError("pip not found")),
        _mock_manager([_PKG_B]),
    ])
    packages = await registry.scan_all()
    assert packages == [_PKG_B]


async def test_registry_swallows_timeout():
    async def slow_list() -> list[Package]:
        await asyncio.sleep(100)
        return []

    slow = MagicMock(spec=BaseManager)
    slow.list = slow_list

    registry = ManagerRegistry(managers=[slow], timeout=0.01)
    packages = await registry.scan_all()
    assert packages == []


async def test_registry_empty_managers():
    registry = ManagerRegistry(managers=[])
    packages = await registry.scan_all()
    assert packages == []


async def test_registry_combines_packages_from_multiple_managers():
    pkg_c = Package(name="pip", version="23.0.1", manager="pip")
    registry = ManagerRegistry(managers=[
        _mock_manager([_PKG_A, pkg_c]),
        _mock_manager([_PKG_B]),
    ])
    packages = await registry.scan_all()
    assert len(packages) == 3


async def test_registry_one_manager_fails_others_succeed():
    registry = ManagerRegistry(managers=[
        _mock_manager(TimeoutError()),
        _mock_manager([_PKG_A]),
        _mock_manager(OSError("command not found")),
        _mock_manager([_PKG_B]),
    ])
    packages = await registry.scan_all()
    assert sorted(p.name for p in packages) == ["requests", "typescript"]
