from __future__ import annotations

import json
import shutil

from .base import BaseManager, Package
from ._subprocess import run_command


class PipManager(BaseManager):
    def __init__(self) -> None:
        self._cmd = "pip3" if shutil.which("pip3") else "pip"

    @property
    def name(self) -> str:
        return "pip"

    def is_available(self) -> bool:
        return shutil.which("pip3") is not None or shutil.which("pip") is not None

    async def list(self) -> list[Package]:
        stdout, _, returncode = await run_command([self._cmd, "list", "--format=json"])
        if returncode != 0:
            return []
        return [
            Package(name=p["name"], version=p["version"], manager=self.name)
            for p in json.loads(stdout)
        ]

    async def update(self, name: str) -> bool:
        _, _, code = await run_command([self._cmd, "install", "--upgrade", name])
        return code == 0

    async def delete(self, name: str) -> bool:
        _, _, code = await run_command([self._cmd, "uninstall", "-y", name])
        return code == 0

    async def check_orphans(self) -> list[Package]:
        return []  # Stretch: Hours 16-20
