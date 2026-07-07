from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import Field

from creator_outreach_automation.models.base import AppModel


ToolHandler = Callable[..., Awaitable[Any]]


class AgentTool(AppModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class AgentToolbox:
    def __init__(self, tools: list[AgentTool] | None = None) -> None:
        self._tools = {tool.name: tool for tool in tools or []}

    def add(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    def list(self) -> list[AgentTool]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return sorted(self._tools)
