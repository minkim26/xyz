from __future__ import annotations

import builtins
import json
import os
from datetime import datetime
from urllib.parse import urlparse

from .base import BaseManager, Package
from ._subprocess import run_command


class NpmManager(BaseManager):
    @property
    def name(self) -> str:
        return "npm"

    async def list(self) -> builtins.list[Package]:
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
        deps = raw.get("dependencies") or {}
        packages = []
        for pkg_name, info in deps.items():
            version = info.get("version", "") if isinstance(info, dict) else ""
            pkg_path = info.get("path", "") if isinstance(info, dict) else ""
            resolved = info.get("resolved", "") if isinstance(info, dict) else ""
            install_date = source = None
            if pkg_path and os.path.isdir(pkg_path):
                try:
                    install_date = datetime.fromtimestamp(
                        os.path.getmtime(pkg_path)
                    ).strftime("%Y-%m-%d")
                except OSError:
                    pass
            try:
                source = urlparse(resolved).netloc or "npmjs.com"
            except Exception:
                source = "npmjs.com"
            packages.append(Package(name=pkg_name, version=version, manager=self.name, install_date=install_date, source=source))
        return packages

    async def update(self, name: str, dry_run: bool = False) -> tuple[bool, str]:
        cmd = ["npm", "update", "-g", name]
        if dry_run:
            cmd.append("--dry-run")
        stdout, stderr, code = await run_command(cmd)
        return code == 0, f"{stdout}\n{stderr}".strip()

    async def delete(self, name: str, dry_run: bool = False) -> tuple[bool, str]:
        cmd = ["npm", "uninstall", "-g", name]
        if dry_run:
            cmd.append("--dry-run")
        stdout, stderr, code = await run_command(cmd)
        return code == 0, f"{stdout}\n{stderr}".strip()

    async def check_orphans(self) -> builtins.list[Package]:
        return []
