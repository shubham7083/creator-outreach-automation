from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeVar

from creator_outreach_automation.models.base import EntityModel

TEntity = TypeVar("TEntity", bound=EntityModel)


class Repository(ABC, Generic[TEntity]):
    @abstractmethod
    async def add(self, entity: TEntity) -> TEntity:
        ...

    @abstractmethod
    async def get(self, entity_id: str) -> TEntity | None:
        ...

    @abstractmethod
    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[TEntity]:
        ...

    @abstractmethod
    async def update(self, entity: TEntity) -> TEntity:
        ...

    @abstractmethod
    async def delete(self, entity_id: str) -> None:
        ...
