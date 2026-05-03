from __future__ import annotations

import json

import pytest

from xyz.managers.npm import NpmManager
from xyz.managers.base import Package


@pytest.fixture
def manager():
    return NpmManager()


_TWO_PACKAGES = json.dumps({
    "dependencies": {
        "typescript": {"version": "5.4.5"},
        "eslint": {"version": "8.57.0"},
    }
})


async def test_list_parses_global_packages(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.npm", stdout=_TWO_PACKAGES):
        packages = await manager.list()

    assert len(packages) == 2
    names = {p.name for p in packages}
    assert names == {"typescript", "eslint"}
    for pkg in packages:
        assert pkg.manager == "npm"


async def test_list_package_has_correct_version(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.npm", stdout=_TWO_PACKAGES):
        packages = await manager.list()
    by_name = {p.name: p for p in packages}
    assert by_name["typescript"].version == "5.4.5"
    assert by_name["eslint"].version == "8.57.0"


async def test_list_accepts_exit_code_1(manager, fake_subprocess):
    # npm exits 1 on peer-dep warnings — should still parse
    with fake_subprocess("xyz.managers.npm", stdout=_TWO_PACKAGES, returncode=1):
        packages = await manager.list()
    assert len(packages) == 2


async def test_list_rejects_exit_code_2(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.npm", stdout=_TWO_PACKAGES, returncode=2):
        packages = await manager.list()
    assert packages == []


async def test_list_invalid_json(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.npm", stdout="not json at all"):
        packages = await manager.list()
    assert packages == []


async def test_list_empty_dependencies(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.npm", stdout='{"dependencies":{}}'):
        packages = await manager.list()
    assert packages == []


async def test_list_no_dependencies_key(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.npm", stdout='{"version":"10.0.0"}'):
        packages = await manager.list()
    assert packages == []


async def test_list_package_size_is_none(manager, fake_subprocess):
    single = json.dumps({"dependencies": {"lodash": {"version": "4.17.21"}}})
    with fake_subprocess("xyz.managers.npm", stdout=single):
        packages = await manager.list()
    assert packages[0].size is None


async def test_update_returns_true_on_success(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.npm", returncode=0):
        result = await manager.update("typescript")
    assert result == (True, "")


async def test_update_returns_false_on_failure(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.npm", returncode=1):
        result = await manager.update("typescript")
    assert result == (False, "")


async def test_delete_returns_true_on_success(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.npm", returncode=0):
        result = await manager.delete("typescript")
    assert result == (True, "")


async def test_delete_returns_false_on_failure(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.npm", returncode=1):
        result = await manager.delete("typescript")
    assert result == (False, "")


async def test_check_orphans_stub_returns_empty(manager):
    result = await manager.check_orphans()
    assert result == []


def test_manager_name_is_npm(manager):
    assert manager.name == "npm"
