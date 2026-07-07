from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from creator_outreach_automation.agents.base import Agent, AgentRunResult
from creator_outreach_automation.models.base import AppModel

logger = logging.getLogger(__name__)


class WorkflowState(AppModel):
    values: dict[str, Any] = Field(default_factory=dict)

    def get_required(self, key: str) -> Any:
        if key not in self.values:
            raise KeyError(f"Workflow state is missing required key: {key}")
        return self.values[key]

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value


class WorkflowStep(AppModel):
    agent_name: str
    input_key: str | None = None
    output_key: str


class WorkflowDefinition(AppModel):
    name: str
    steps: list[WorkflowStep] = Field(default_factory=list)


StepInputBuilder = Callable[[WorkflowState, WorkflowStep], BaseModel | dict[str, object]]


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, Agent[Any, Any]] = {}

    def register(self, agent: Agent[Any, Any]) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent[Any, Any]:
        try:
            return self._agents[name]
        except KeyError as error:
            raise KeyError(f"Agent is not registered: {name}") from error

    def names(self) -> list[str]:
        return sorted(self._agents)


class WorkflowManager:
    def __init__(
        self,
        *,
        registry: AgentRegistry,
        input_builders: dict[str, StepInputBuilder] | None = None,
    ) -> None:
        self._registry = registry
        self._input_builders = input_builders or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def register_input_builder(self, agent_name: str, builder: StepInputBuilder) -> None:
        self._input_builders[agent_name] = builder

    async def run(
        self,
        definition: WorkflowDefinition,
        *,
        initial_state: WorkflowState | None = None,
    ) -> WorkflowState:
        state = initial_state or WorkflowState()
        self.logger.info("Workflow started name=%s steps=%s", definition.name, len(definition.steps))
        for step in definition.steps:
            agent = self._registry.get(step.agent_name)
            agent_input = self._build_input(state, step, agent)
            result: AgentRunResult[Any] = await agent.run(agent_input)
            state.set(step.output_key, result.output)
            self.logger.info(
                "Workflow step completed workflow=%s agent=%s output_key=%s",
                definition.name,
                step.agent_name,
                step.output_key,
            )
        self.logger.info("Workflow completed name=%s", definition.name)
        return state

    def _build_input(
        self,
        state: WorkflowState,
        step: WorkflowStep,
        agent: Agent[Any, Any],
    ) -> BaseModel | dict[str, object]:
        builder = self._input_builders.get(step.agent_name)
        if builder:
            return builder(state, step)
        if step.input_key is None:
            raise ValueError(f"Workflow step {step.agent_name} needs input_key or input builder.")
        raw_value = state.get_required(step.input_key)
        if isinstance(raw_value, agent.input_model):
            return raw_value
        if isinstance(raw_value, dict):
            return raw_value
        raise TypeError(
            f"Workflow state key {step.input_key} cannot be used as input for {step.agent_name}."
        )


def default_workflow_definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="creator_outreach_pipeline",
        steps=[
            WorkflowStep(agent_name="creator", input_key="creator_input", output_key="creator_output"),
            WorkflowStep(agent_name="brand_discovery", output_key="brand_discovery_output"),
            WorkflowStep(agent_name="scoring", output_key="scoring_output"),
            WorkflowStep(agent_name="contact", output_key="contact_output"),
            WorkflowStep(agent_name="email", output_key="email_output"),
            WorkflowStep(agent_name="crm", output_key="crm_output"),
        ],
    )
