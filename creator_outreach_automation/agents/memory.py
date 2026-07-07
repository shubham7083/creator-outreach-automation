from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import Field

from creator_outreach_automation.models.base import AppModel


class AgentMemoryEntry(AppModel):
    agent_name: str
    key: str
    value: Any
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentMemory:
    def __init__(self) -> None:
        self._entries: list[AgentMemoryEntry] = []

    def add(self, *, agent_name: str, key: str, value: Any) -> None:
        self._entries.append(AgentMemoryEntry(agent_name=agent_name, key=key, value=value))

    def latest(self, *, agent_name: str, key: str) -> Any | None:
        for entry in reversed(self._entries):
            if entry.agent_name == agent_name and entry.key == key:
                return entry.value
        return None

    def all(self, *, agent_name: str | None = None) -> list[AgentMemoryEntry]:
        if agent_name is None:
            return list(self._entries)
        return [entry for entry in self._entries if entry.agent_name == agent_name]
