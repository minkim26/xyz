from __future__ import annotations

import pytest

from xyz.managers.base import Package
from xyz.managers.brew import BrewManager


@pytest.fixture
def manager():
    return BrewManager()


async def test_check_orphans_from_leaves_and_versions(manager, fake_subprocess):
    info_json = """{
      \"formulae\": [
        {\"name\": \"colima\", \"installed\": [{\"installed_as_dependency\": false, \"installed_on_request\": true}]},
        {\"name\": \"readline\", \"installed\": [{\"installed_as_dependency\": true, \"installed_on_request\": false}]}
      ]
    }"""
    with fake_subprocess("xyz.managers.brew") as mocked:
        mocked.side_effect = [
            ("colima\nreadline\n", "", 0),
            ("colima 0.7.4\nreadline 8.2.10\n", "", 0),
            (info_json, "", 0),
        ]
        result = await manager.check_orphans()

    assert result == [
        Package(name="readline", version="8.2.10", manager="brew", is_orphan=True),
    ]
