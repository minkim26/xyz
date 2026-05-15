from __future__ import annotations

import builtins
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    manager: str
    size: int | None = None  # bytes; None when the CLI does not provide it
    is_orphan: bool = False
    install_date: str | None = None
    source: str | None = None

    def formatted_size(self) -> str:
        if self.size is None:
            return "—"
        size = float(self.size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class BaseManager(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    def is_available(self) -> bool:
        return shutil.which(self.name) is not None

    @abstractmethod
    async def list(self) -> builtins.list[Package]: ...

    @abstractmethod
    async def update(self, name: str, dry_run: bool = False) -> tuple[bool, str]: ...

    @abstractmethod
    async def delete(self, name: str, dry_run: bool = False) -> tuple[bool, str]: ...

    @abstractmethod
    @abstractmethod
    async def check_orphans(self) -> builtins.list[Package]: ...

    async def get_deps(self, name: str) -> tuple[builtins.list[str], builtins.list[str]]:
        """Return (requires, required_by). Override in managers that support it."""
        return [], []
