from __future__ import annotations

import builtins
import json
import os
import shutil
from datetime import datetime

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

    async def list(self) -> builtins.list[Package]:  # type: ignore[valid-type]
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
            install_date = source = None
            for base in _CELLAR_PATHS:
                path = os.path.join(base, name, version)
                if os.path.isdir(path):
                    try:
                        install_date = datetime.fromtimestamp(
                            os.path.getmtime(path)
                        ).strftime("%Y-%m-%d")
                    except OSError:
                        pass
                    source = "brew.sh"
                    break
            packages.append(Package(name=name, version=version, manager=self.name, size=None, install_date=install_date, source=source))
        return packages

    async def update(self, name: str, dry_run: bool = False) -> tuple[bool, str]:
        cmd = ["brew", "upgrade", name]
        if dry_run:
            cmd.append("--dry-run")
        stdout, stderr, code = await run_command(cmd)
        return code == 0, f"{stdout}\n{stderr}".strip()

    async def delete(self, name: str, dry_run: bool = False) -> tuple[bool, str]:
        if dry_run:
            return True, f"Would uninstall {name}."
        cmd = ["brew", "uninstall", name]
        stdout, stderr, code = await run_command(cmd)
        return code == 0, f"{stdout}\n{stderr}".strip()

    async def get_deps(self, name: str) -> tuple[list[str], list[str]]:
        import asyncio as _asyncio
        (deps_out, _, _), (uses_out, _, _) = await _asyncio.gather(
            run_command(["brew", "deps", name]),
            run_command(["brew", "uses", "--installed", name]),
        )
        requires = [x.strip() for x in deps_out.splitlines() if x.strip()]
        required_by = [x.strip() for x in uses_out.splitlines() if x.strip()]
        return requires, required_by

    async def check_orphans(self) -> builtins.list[Package]:
        """Return orphan formulae.

        For Homebrew, treat an orphan as a formula that is both:
        1) a leaf (no installed formula depends on it), and
        2) installed as a dependency (not explicitly requested by user).
        """
        leaves_out, _, leaves_rc = await run_command(["brew", "leaves"])
        if leaves_rc != 0:
            return []

        list_out, _, list_rc = await run_command(["brew", "list", "--versions", "--formula"])
        if list_rc != 0:
            return []

        versions: dict[str, str] = {}
        for line in list_out.strip().splitlines():
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            version = parts[-1] if len(parts) > 1 else ""
            versions[name] = version

        leaf_names = [x.strip() for x in leaves_out.splitlines() if x.strip()]
        if not leaf_names:
            return []

        installed_as_dependency: set[str] = set()
        info_out, _, info_rc = await run_command(["brew", "info", "--json=v2", *leaf_names])
        if info_rc == 0:
            try:
                info_data = json.loads(info_out)
                for formula in info_data.get("formulae", []):
                    if not isinstance(formula, dict):
                        continue
                    name = formula.get("name")
                    if not isinstance(name, str) or not name:
                        continue
                    installs = formula.get("installed")
                    if not isinstance(installs, list):
                        continue
                    if any(
                        bool(inst.get("installed_as_dependency", False))
                        for inst in installs
                        if isinstance(inst, dict)
                    ):
                        installed_as_dependency.add(name)
            except (json.JSONDecodeError, TypeError):
                installed_as_dependency = set()

        orphans: builtins.list[Package] = []
        for name in leaf_names:
            if not name:
                continue
            if installed_as_dependency and name not in installed_as_dependency:
                continue
            orphans.append(
                Package(
                    name=name,
                    version=versions.get(name, ""),
                    manager=self.name,
                    is_orphan=True,
                )
            )
        return orphans
