from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    manager: str
    size: Optional[int] = None  # bytes; None when the CLI does not provide it
    is_orphan: bool = False


class BaseManager(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    def is_available(self) -> bool:
        return shutil.which(self.name) is not None

    @abstractmethod
    async def list(self) -> list[Package]: ...

    @abstractmethod
    async def update(self, name: str) -> bool: ...

    @abstractmethod
    async def delete(self, name: str) -> bool: ...

    @abstractmethod
    async def check_orphans(self) -> list[Package]: ...
