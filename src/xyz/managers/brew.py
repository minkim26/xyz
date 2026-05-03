from __future__ import annotations

import os
import shutil

from .base import BaseManager, Package
from ._subprocess import run_command

_CELLAR_PATHS = (
    "/opt/homebrew/Cellar",
    "/usr/local/Cellar",
    "/home/linuxbrew/.linuxbrew/Cellar",
)


def _cellar_size(name: str, version: str) -> int | None:
    for base in _CELLAR_PATHS:
        path = os.path.join(base, name, version)
        if not os.path.isdir(path):
            continue
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for fname in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, fname))
                except OSError:
                    pass
        return total or None
    return None


class BrewManager(BaseManager):
    @property
    def name(self) -> str:
        return "brew"

    def is_available(self) -> bool:
        return shutil.which("brew") is not None

    async def list(self) -> list[Package]:
        stdout, _, returncode = await run_command(
            ["brew", "list", "--versions", "--formula"]
        )
        if returncode != 0:
            return []
        packages = []
        for line in stdout.strip().splitlines():
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            version = parts[-1] if len(parts) > 1 else ""
            packages.append(Package(name=name, version=version, manager=self.name, size=None))
        return packages

    async def update(self, name: str) -> bool:
        _, _, code = await run_command(["brew", "upgrade", name])
        return code == 0

    async def delete(self, name: str) -> bool:
        _, _, code = await run_command(["brew", "uninstall", name])
        return code == 0

    async def check_orphans(self) -> list[Package]:
        return []
