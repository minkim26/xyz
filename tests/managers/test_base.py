from __future__ import annotations

import dataclasses

import pytest

from xyz.managers.base import Package


def test_package_defaults() -> None:
    pkg = Package(name="requests", version="2.31.0", manager="pip")
    assert pkg.size is None
    assert pkg.is_orphan is False


def test_package_value_equality() -> None:
    a = Package(name="requests", version="2.31.0", manager="pip")
    b = Package(name="requests", version="2.31.0", manager="pip")
    assert a == b


def test_package_inequality_on_different_fields() -> None:
    a = Package(name="requests", version="2.31.0", manager="pip")
    b = Package(name="requests", version="2.32.0", manager="pip")
    assert a != b


def test_package_is_frozen() -> None:
    pkg = Package(name="requests", version="2.31.0", manager="pip")
    with pytest.raises(dataclasses.FrozenInstanceError):
        pkg.version = "9.9.9"  # type: ignore[misc]


def test_package_with_all_fields() -> None:
    pkg = Package(name="lodash", version="4.17.21", manager="npm", size=1_400_000, is_orphan=True)
    assert pkg.size == 1_400_000
    assert pkg.is_orphan is True


def test_package_is_hashable() -> None:
    pkg = Package(name="requests", version="2.31.0", manager="pip")
    assert hash(pkg) is not None
    seen = {pkg}
    assert pkg in seen
