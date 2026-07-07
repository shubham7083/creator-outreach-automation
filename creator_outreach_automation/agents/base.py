from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from creator_outreach_automation.agents.memory import AgentMemory
from creator_outreach_automation.agents.tools import AgentTool, AgentToolbox
from creator_outreach_automation.models.base import AppModel

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class AgentExecutionError(RuntimeError):
    """Raised when an agent cannot complete its assigned task."""


class AgentRunMetadata(AppModel):
    agent_name: str
    attempts: int = 1
    tool_names: list[str] = Field(default_factory=list)


class AgentRunResult(AppModel, Generic[TOutput]):
    output: TOutput
    metadata: AgentRunMetadata


class Agent(ABC, Generic[TInput, TOutput]):
    name: str
    input_model: type[TInput]
    output_model: type[TOutput]

    def __init__(
        self,
        *,
        memory: AgentMemory | None = None,
        tools: list[AgentTool] | None = None,
        max_retries: int = 3,
    ) -> None:
        self.memory = memory or AgentMemory()
        self.tools = AgentToolbox(tools)
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    async def run(self, raw_input: TInput | dict[str, object]) -> AgentRunResult[TOutput]:
        agent_input = self._coerce_input(raw_input)
        self.logger.info("Agent started")
        self.memory.add(agent_name=self.name, key="last_input", value=agent_input.model_dump(mode="json"))
        try:
            output = await self._run_with_retry(agent_input)
        except Exception as error:
            self.logger.exception("Agent failed")
            raise AgentExecutionError(f"{self.name} failed: {error}") from error
        self.memory.add(agent_name=self.name, key="last_output", value=output.model_dump(mode="json"))
        self.logger.info("Agent completed")
        return AgentRunResult(
            output=output,
            metadata=AgentRunMetadata(
                agent_name=self.name,
                attempts=self.max_retries,
                tool_names=self.tools.names(),
            ),
        )

    async def _run_with_retry(self, agent_input: TInput) -> TOutput:
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            reraise=True,
        )
        async def execute() -> TOutput:
            return await self.execute(agent_input)

        return await execute()

    def _coerce_input(self, raw_input: TInput | dict[str, object]) -> TInput:
        if isinstance(raw_input, self.input_model):
            return raw_input
        return self.input_model.model_validate(raw_input)

    @abstractmethod
    async def execute(self, agent_input: TInput) -> TOutput:
        ...
