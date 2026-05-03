from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def fake_subprocess():
    """
    Returns a context-manager factory that patches run_command for a given module.

    Usage::

        def test_something(fake_subprocess):
            with fake_subprocess("xyz.managers.pip", stdout='[{"name":"pip","version":"23"}]'):
                result = await manager.list()
    """

    @contextmanager
    def _make(
        module: str,
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
    ) -> Generator[AsyncMock, None, None]:
        mock = AsyncMock(return_value=(stdout, stderr, returncode))
        with patch(f"{module}.run_command", new=mock) as patched:
            yield patched

    return _make
