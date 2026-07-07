from __future__ import annotations

from typing import Protocol

from creator_outreach_automation.agents.base import Agent
from creator_outreach_automation.agents.models import (
    BrandDiscoveryAgentInput,
    BrandDiscoveryAgentOutput,
    ContactAgentInput,
    ContactAgentOutput,
    CRMAgentInput,
    CRMAgentOutput,
    CRMStatus,
    CreatorAgentInput,
    CreatorAgentOutput,
    EmailAgentInput,
    EmailAgentOutput,
    ScoringAgentInput,
    ScoringAgentOutput,
)
from creator_outreach_automation.agents.tools import AgentTool
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.contact import Contact
from creator_outreach_automation.services.brand_discovery import BrandDiscoveryEngine
from creator_outreach_automation.services.brand_scoring import BrandScoringEngine
from creator_outreach_automation.services.creator_analysis import CreatorAnalysisService
from creator_outreach_automation.services.outreach_engine import OutreachEngine


class ContactDiscoveryServiceProtocol(Protocol):
    async def discover(self, brand: Brand) -> list[Contact]:
        ...


class CreatorAgent(Agent[CreatorAgentInput, CreatorAgentOutput]):
    name = "creator"
    input_model = CreatorAgentInput
    output_model = CreatorAgentOutput

    def __init__(self, service: CreatorAnalysisService, **kwargs: object) -> None:
        super().__init__(
            tools=[AgentTool(name="creator_analysis", description="Analyze Instagram or YouTube creators")],
            **kwargs,
        )
        self._service = service

    async def execute(self, agent_input: CreatorAgentInput) -> CreatorAgentOutput:
        profile = await self._service.analyze(agent_input.analysis_input)
        return CreatorAgentOutput(creator_profile=profile)


class BrandDiscoveryAgent(Agent[BrandDiscoveryAgentInput, BrandDiscoveryAgentOutput]):
    name = "brand_discovery"
    input_model = BrandDiscoveryAgentInput
    output_model = BrandDiscoveryAgentOutput

    def __init__(self, engine: BrandDiscoveryEngine, **kwargs: object) -> None:
        super().__init__(
            tools=[AgentTool(name="brand_discovery", description="Discover brands by niche")],
            **kwargs,
        )
        self._engine = engine

    async def execute(self, agent_input: BrandDiscoveryAgentInput) -> BrandDiscoveryAgentOutput:
        brands = await self._engine.discover(agent_input.creator_profile)
        return BrandDiscoveryAgentOutput(brands=brands)


class ScoringAgent(Agent[ScoringAgentInput, ScoringAgentOutput]):
    name = "scoring"
    input_model = ScoringAgentInput
    output_model = ScoringAgentOutput

    def __init__(self, engine: BrandScoringEngine, **kwargs: object) -> None:
        super().__init__(
            tools=[AgentTool(name="brand_scoring", description="Score creator-brand fit")],
            **kwargs,
        )
        self._engine = engine

    async def execute(self, agent_input: ScoringAgentInput) -> ScoringAgentOutput:
        result = await self._engine.score_brands(
            creator_profile=agent_input.creator_profile,
            brand_summaries=[
                (summary.brand, summary.website_summary)
                for summary in agent_input.brand_summaries
            ],
        )
        return ScoringAgentOutput(scoring_result=result)


class ContactAgent(Agent[ContactAgentInput, ContactAgentOutput]):
    name = "contact"
    input_model = ContactAgentInput
    output_model = ContactAgentOutput

    def __init__(self, service: ContactDiscoveryServiceProtocol, **kwargs: object) -> None:
        super().__init__(
            tools=[AgentTool(name="contact_discovery", description="Find brand marketing contacts")],
            **kwargs,
        )
        self._service = service

    async def execute(self, agent_input: ContactAgentInput) -> ContactAgentOutput:
        contacts: list[Contact] = []
        for brand in agent_input.brands:
            contacts.extend(await self._service.discover(brand))
        return ContactAgentOutput(contacts=contacts)


class EmailAgent(Agent[EmailAgentInput, EmailAgentOutput]):
    name = "email"
    input_model = EmailAgentInput
    output_model = EmailAgentOutput

    def __init__(self, engine: OutreachEngine, **kwargs: object) -> None:
        super().__init__(
            tools=[AgentTool(name="gmail_drafts", description="Create Gmail drafts only")],
            **kwargs,
        )
        self._engine = engine

    async def execute(self, agent_input: EmailAgentInput) -> EmailAgentOutput:
        sequences = []
        for request in agent_input.outreach_requests:
            sequences.append(await self._engine.create_drafts(request))
        return EmailAgentOutput(sequences=sequences)


class CRMAgent(Agent[CRMAgentInput, CRMAgentOutput]):
    name = "crm"
    input_model = CRMAgentInput
    output_model = CRMAgentOutput

    def __init__(self, **kwargs: object) -> None:
        super().__init__(
            tools=[AgentTool(name="crm_status", description="Summarize campaign pipeline status")],
            **kwargs,
        )

    async def execute(self, agent_input: CRMAgentInput) -> CRMAgentOutput:
        approved = [item for item in agent_input.scored_brands if item.accepted]
        next_actions: list[str] = []
        if agent_input.creator_profile is None:
            next_actions.append("Analyze a creator profile")
        if not agent_input.brands:
            next_actions.append("Discover brands")
        if agent_input.brands and not agent_input.scored_brands:
            next_actions.append("Score brands")
        if approved and not agent_input.contacts:
            next_actions.append("Find decision-maker contacts")
        if agent_input.contacts and not agent_input.outreach_sequences:
            next_actions.append("Generate Gmail drafts")
        return CRMAgentOutput(
            status=CRMStatus(
                creator_handle=agent_input.creator_profile.handle if agent_input.creator_profile else None,
                brand_count=len(agent_input.brands),
                scored_count=len(agent_input.scored_brands),
                approved_count=len(approved),
                contact_count=len(agent_input.contacts),
                outreach_sequence_count=len(agent_input.outreach_sequences),
                next_actions=next_actions,
            )
        )
