from __future__ import annotations

import pytest

from xyz.managers.pip import PipManager
from xyz.managers.base import Package


@pytest.fixture
def manager():
    return PipManager()


async def test_list_parses_packages(manager, fake_subprocess):
    stdout = '[{"name":"requests","version":"2.31.0"},{"name":"setuptools","version":"68.0.0"}]'
    with fake_subprocess("xyz.managers.pip", stdout=stdout):
        packages = await manager.list()

    assert len(packages) == 2
    assert packages[0] == Package(name="requests", version="2.31.0", manager="pip")
    assert packages[1] == Package(name="setuptools", version="68.0.0", manager="pip")


async def test_list_returns_empty_on_nonzero_exit(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.pip", stdout="", returncode=1):
        packages = await manager.list()
    assert packages == []


async def test_list_empty_json_array(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.pip", stdout="[]"):
        packages = await manager.list()
    assert packages == []


async def test_list_package_has_correct_manager_field(manager, fake_subprocess):
    stdout = '[{"name":"pip","version":"23.0.1"}]'
    with fake_subprocess("xyz.managers.pip", stdout=stdout):
        packages = await manager.list()
    assert packages[0].manager == "pip"


async def test_list_package_size_is_none(manager, fake_subprocess):
    stdout = '[{"name":"pip","version":"23.0.1"}]'
    with fake_subprocess("xyz.managers.pip", stdout=stdout):
        packages = await manager.list()
    assert packages[0].size is None


async def test_update_returns_true_on_success(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.pip", returncode=0):
        result = await manager.update("requests")
    assert result == (True, "")


async def test_update_returns_false_on_failure(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.pip", returncode=1):
        result = await manager.update("requests")
    assert result == (False, "")


async def test_delete_returns_true_on_success(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.pip", returncode=0):
        result = await manager.delete("requests")
    assert result == (True, "")


async def test_delete_returns_false_on_failure(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.pip", returncode=1):
        result = await manager.delete("requests")
    assert result == (False, "")


async def test_update_propagates_output(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.pip", returncode=0, stdout="success output", stderr="some warning"):
        result = await manager.update("requests")
    assert result == (True, "success output\nsome warning")


async def test_delete_propagates_output(manager, fake_subprocess):
    with fake_subprocess("xyz.managers.pip", returncode=1, stdout="", stderr="error removing"):
        result = await manager.delete("requests")
    assert result == (False, "error removing")


async def test_check_orphans_stub_returns_empty(manager, fake_subprocess):
    leaves = '[{"name":"urllib3","version":"2.2.1"},{"name":"pip","version":"24.0"}]'
    inspect = '{"installed":[{"metadata":{"name":"urllib3"},"requested":false},{"metadata":{"name":"pip"},"requested":true}]}'
    with fake_subprocess("xyz.managers.pip") as mocked:
        mocked.side_effect = [
            (leaves, "", 0),
            (inspect, "", 0),
        ]
        result = await manager.check_orphans()

    assert result == [
        Package(name="urllib3", version="2.2.1", manager="pip", is_orphan=True)
    ]


def test_manager_name_is_pip(manager):
    assert manager.name == "pip"
