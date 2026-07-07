from __future__ import annotations

import pytest

from creator_outreach_automation.agents.builders import default_input_builders
from creator_outreach_automation.agents.concrete import (
    BrandDiscoveryAgent,
    ContactAgent,
    CRMAgent,
    CreatorAgent,
    EmailAgent,
    ScoringAgent,
)
from creator_outreach_automation.agents.models import CreatorAgentInput
from creator_outreach_automation.agents.workflow import (
    AgentRegistry,
    WorkflowManager,
    WorkflowState,
    default_workflow_definition,
)
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.brand_scoring import BrandScore, BrandScoringResult, ScoredBrand
from creator_outreach_automation.models.contact import Contact, ContactRole, ContactSource
from creator_outreach_automation.models.creator_analysis import (
    CreatorAnalysisInput,
    CreatorPlatform,
    CreatorProfile,
)
from creator_outreach_automation.models.outreach import (
    GmailDraftRecord,
    OutreachDraftKind,
    OutreachSequenceResult,
)


class FakeCreatorService:
    async def analyze(self, analysis_input: CreatorAnalysisInput) -> CreatorProfile:
        return _creator_profile()


class FakeBrandEngine:
    async def discover(self, creator_profile: CreatorProfile) -> list[Brand]:
        return [_brand()]


class FakeScoringEngine:
    async def score_brands(self, *, creator_profile: CreatorProfile, brand_summaries):
        brand = brand_summaries[0][0]
        score = BrandScore(
            score=8,
            reason="Strong fit.",
            campaign_idea="Creator workflow walkthrough.",
            estimated_pricing="$1,000",
            email_hook="Useful hook.",
        )
        return BrandScoringResult(
            creator_profile=creator_profile,
            ranked_brands=[ScoredBrand(brand=brand, score=score, accepted=True)],
            rejected_brands=[],
        )


class FakeContactService:
    async def discover(self, brand: Brand) -> list[Contact]:
        return [
            Contact(
                brand_id=str(brand.id),
                brand_name=brand.name,
                name="Sam",
                title="Partnerships Lead",
                email="sam@example.com",
                role=ContactRole.PARTNERSHIPS,
                confidence_score=0.9,
                sources=[ContactSource.APOLLO],
            )
        ]


class FakeEmailEngine:
    async def create_drafts(self, request):
        return OutreachSequenceResult(
            creator_identity="youtube:workflow-lab",
            brand_id=str(request.brand.id),
            brand_name=request.brand.name,
            recipient_email=request.recipient_email,
            drafts=[
                GmailDraftRecord(
                    kind=OutreachDraftKind.INITIAL,
                    subject="Hello",
                    body="Short email.",
                    gmail_draft_id="draft-1",
                )
            ],
        )


@pytest.mark.asyncio
async def test_creator_agent_memory_and_output() -> None:
    agent = CreatorAgent(FakeCreatorService())  # type: ignore[arg-type]
    result = await agent.run(
        CreatorAgentInput(
            analysis_input=CreatorAnalysisInput(youtube_url="https://www.youtube.com/@workflow")
        )
    )

    assert result.output.creator_profile.handle == "workflow-lab"
    assert agent.memory.latest(agent_name="creator", key="last_output") is not None


@pytest.mark.asyncio
async def test_workflow_manager_orchestrates_registered_agents() -> None:
    registry = AgentRegistry()
    registry.register(CreatorAgent(FakeCreatorService()))  # type: ignore[arg-type]
    registry.register(BrandDiscoveryAgent(FakeBrandEngine()))  # type: ignore[arg-type]
    registry.register(ScoringAgent(FakeScoringEngine()))  # type: ignore[arg-type]
    registry.register(ContactAgent(FakeContactService()))
    registry.register(EmailAgent(FakeEmailEngine()))  # type: ignore[arg-type]
    registry.register(CRMAgent())
    manager = WorkflowManager(registry=registry, input_builders=default_input_builders())

    state = await manager.run(
        default_workflow_definition(),
        initial_state=WorkflowState(
            values={
                "creator_input": CreatorAgentInput(
                    analysis_input=CreatorAnalysisInput(
                        youtube_url="https://www.youtube.com/@workflow"
                    )
                )
            }
        ),
    )

    crm_output = state.get_required("crm_output")
    assert crm_output.status.brand_count == 1
    assert crm_output.status.approved_count == 1
    assert crm_output.status.contact_count == 1
    assert crm_output.status.outreach_sequence_count == 1


def _creator_profile() -> CreatorProfile:
    return CreatorProfile(
        platform=CreatorPlatform.YOUTUBE,
        handle="workflow-lab",
        display_name="Workflow Lab",
        subscriber_count=10_000,
        total_views=100_000,
        topics=["workflow"],
        keywords=["workflow", "apps"],
        niche="Productivity tech",
        audience_summary="Creators and remote workers.",
        content_themes=["workflow"],
        collaboration_opportunities=["sponsored video"],
        estimated_pricing="$1,000",
    )


def _brand() -> Brand:
    return Brand(
        name="FlowForge",
        website="https://flowforge.example",
        description="Workflow automation platform.",
        industry="SaaS",
    )
