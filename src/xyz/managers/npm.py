from __future__ import annotations

import json

from .base import BaseManager, Package
from ._subprocess import run_command


class NpmManager(BaseManager):
    @property
    def name(self) -> str:
        return "npm"

    async def list(self) -> list[Package]:
        stdout, _, returncode = await run_command(
            ["npm", "list", "-g", "--json", "--depth=0"]
        )
        # npm exits 1 on peer-dependency warnings — treat same as success
        if returncode not in (0, 1):
            return []
        try:
            raw = json.loads(stdout)
        except json.JSONDecodeError:
            return []
        return [
            Package(name=pkg_name, version=info.get("version", ""), manager=self.name)
            for pkg_name, info in raw.get("dependencies", {}).items()
        ]

    async def update(self, name: str) -> bool:
        _, _, code = await run_command(["npm", "update", "-g", name])
        return code == 0

    async def delete(self, name: str) -> bool:
        _, _, code = await run_command(["npm", "uninstall", "-g", name])
        return code == 0

    async def check_orphans(self) -> list[Package]:
        return []
