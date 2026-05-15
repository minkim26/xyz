from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock


from xyz.managers.base import BaseManager, Package
from xyz.managers.registry import ManagerRegistry


def _mock_manager(packages: list[Package] | Exception) -> BaseManager:
    m = MagicMock(spec=BaseManager)
    if isinstance(packages, Exception):
        m.list = AsyncMock(side_effect=packages)
    else:
        m.list = AsyncMock(return_value=packages)
    m.check_orphans = AsyncMock(return_value=[])
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


async def test_registry_marks_orphan_packages_from_manager_signal():
    pip_pkg = Package(name="urllib3", version="2.2.1", manager="pip")
    npm_pkg = Package(name="eslint", version="8.57.0", manager="npm")

    pip_manager = _mock_manager([pip_pkg])
    pip_manager.name = "pip"
    pip_manager.check_orphans = AsyncMock(
        return_value=[Package(name="urllib3", version="2.2.1", manager="pip", is_orphan=True)]
    )

    npm_manager = _mock_manager([npm_pkg])
    npm_manager.name = "npm"
    npm_manager.check_orphans = AsyncMock(return_value=[])

    registry = ManagerRegistry(managers=[pip_manager, npm_manager])
    packages = await registry.scan_all()
    by_key = {(p.manager, p.name): p for p in packages}

    assert by_key[("pip", "urllib3")].is_orphan is True
    assert by_key[("npm", "eslint")].is_orphan is False


async def test_registry_keeps_list_when_orphan_check_times_out():
    pkg = Package(name="colima", version="0.7.4", manager="brew")

    async def fast_list() -> list[Package]:
        return [pkg]

    async def slow_orphans() -> list[Package]:
        await asyncio.sleep(100)
        return []

    manager = MagicMock(spec=BaseManager)
    manager.name = "brew"
    manager.list = fast_list
    manager.check_orphans = slow_orphans

    registry = ManagerRegistry(managers=[manager], timeout=0.01)
    packages = await registry.scan_all()

    assert packages == [pkg]
