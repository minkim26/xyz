from __future__ import annotations

import asyncio
import builtins
import glob
import json
import os
import shutil
from datetime import datetime

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

    async def list(self) -> builtins.list[Package]:
        (list_out, _, rc), (show_out, _, _) = await asyncio.gather(
            run_command([self._cmd, "list", "--format=json"]),
            run_command([self._cmd, "show", "pip"]),
        )
        if rc != 0:
            return []
        try:
            data = json.loads(list_out)
        except (json.JSONDecodeError, TypeError):
            return []

        site_dirs = []
        for line in show_out.splitlines():
            if line.startswith("Location:"):
                site_dirs = [line.split(":", 1)[1].strip()]
                break

        packages = []
        for p in data:
            name, version = p["name"], p["version"]
            install_date = source = None
            for sp in site_dirs:
                matches = glob.glob(os.path.join(sp, f"{name}-{version}.dist-info"))
                if not matches:
                    matches = glob.glob(os.path.join(sp, f"{name.replace('-', '_')}-{version}.dist-info"))
                if matches:
                    try:
                        install_date = datetime.fromtimestamp(
                            os.path.getmtime(matches[0])
                        ).strftime("%Y-%m-%d")
                    except OSError:
                        pass
                    source = "pypi.org"
                    break
            packages.append(Package(name=name, version=version, manager=self.name, install_date=install_date, source=source))
        return packages

    async def update(self, name: str, dry_run: bool = False) -> tuple[bool, str]:
        import sys
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", name]
        if dry_run:
            cmd.insert(4, "--dry-run")
        stdout, stderr, code = await run_command(cmd)
        return code == 0, f"{stdout}\n{stderr}".strip()

    async def delete(self, name: str, dry_run: bool = False) -> tuple[bool, str]:
        if dry_run:
            return True, f"Would uninstall {name} and its unneeded dependencies."
        stdout, stderr, code = await run_command([self._cmd, "uninstall", "-y", name])
        return code == 0, f"{stdout}\n{stderr}".strip()

    async def get_deps(self, name: str) -> tuple[list[str], list[str]]:
        stdout, _, rc = await run_command([self._cmd, "show", name])
        if rc != 0:
            return [], []
        requires: list[str] = []
        required_by: list[str] = []
        for line in stdout.splitlines():
            if line.startswith("Requires:"):
                val = line.split(":", 1)[1].strip()
                requires = [x.strip() for x in val.split(",") if x.strip()]
            elif line.startswith("Required-by:"):
                val = line.split(":", 1)[1].strip()
                required_by = [x.strip() for x in val.split(",") if x.strip()]
        return requires, required_by

    async def check_orphans(self) -> builtins.list[Package]:
        return []  # Stretch: Hours 16-20
