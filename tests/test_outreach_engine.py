from __future__ import annotations

from pathlib import Path

import pytest

from creator_outreach_automation.api.gmail import GmailDraftRequest, GmailDraftResponse
from creator_outreach_automation.config import (
    ApolloSettings,
    BrandDiscoverySettings,
    BrandScoringSettings,
    ContactDiscoverySettings,
    CreatorAnalysisSettings,
    DatabaseSettings,
    GitHubSettings,
    GoogleSettings,
    HttpSettings,
    LoggingSettings,
    OpenAISettings,
    OutreachSettings,
    PathSettings,
    PlaywrightSettings,
    Settings,
    SimilarDiscoverySettings,
)
from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.database.outreach_repository import OutreachRepository
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.creator_analysis import CreatorPlatform, CreatorProfile
from creator_outreach_automation.models.outreach import (
    OutreachGenerationInput,
    OutreachSequenceContent,
)
from creator_outreach_automation.services.outreach_engine import (
    OutreachEngine,
    OutreachGenerationError,
    _parse_sequence,
)


class FakeContentGenerator:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, generation_input: OutreachGenerationInput) -> OutreachSequenceContent:
        self.calls += 1
        return OutreachSequenceContent(
            subject="Workflow collaboration idea",
            email="Hi Sam, I represent Workflow Lab. Your product fits our creator audience well. We would like to explore a useful sponsored workflow segment.",
            follow_up="Hi Sam, just following up on the workflow segment idea. It could show practical use cases without feeling forced.",
            final_follow_up="Hi Sam, final note from me. Happy to close the loop if partnerships are not a priority right now.",
        )


class FakeGmailClient:
    def __init__(self) -> None:
        self.requests: list[GmailDraftRequest] = []

    async def create_draft(self, request: GmailDraftRequest) -> GmailDraftResponse:
        self.requests.append(request)
        return GmailDraftResponse(draft_id=f"draft-{len(self.requests)}")


@pytest.mark.asyncio
async def test_outreach_engine_creates_drafts_caches_and_saves_ids(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    generator = FakeContentGenerator()
    gmail = FakeGmailClient()
    engine = OutreachEngine(
        content_generator=generator,
        gmail_client=gmail,  # type: ignore[arg-type]
        outreach_repository=OutreachRepository(SQLiteDatabase(settings.database.sqlite_path)),
        settings=settings,
    )

    first = await engine.create_drafts(_input())
    second = await engine.create_drafts(_input())

    assert generator.calls == 1
    assert len(gmail.requests) == 6
    assert [draft.gmail_draft_id for draft in first.drafts] == ["draft-1", "draft-2", "draft-3"]
    assert [draft.gmail_draft_id for draft in second.drafts] == ["draft-4", "draft-5", "draft-6"]
    assert all(len(request.body.split()) <= 150 for request in gmail.requests)


def test_parse_sequence_rejects_over_word_limit() -> None:
    too_long = " ".join(["word"] * 151)
    with pytest.raises(OutreachGenerationError):
        _parse_sequence(
            (
                '{"subject":"Hi","email":"'
                + too_long
                + '","follow_up":"short","final_follow_up":"short"}'
            ),
            max_words=150,
        )


def _input() -> OutreachGenerationInput:
    return OutreachGenerationInput(
        creator_profile=_creator_profile(),
        brand=Brand(name="Great Fit", website="https://great.example"),
        campaign_idea="A useful workflow walkthrough for creators.",
        recipient_email="sam@great.example",
        recipient_name="Sam",
        recipient_title="Partnerships Lead",
    )


def _creator_profile() -> CreatorProfile:
    return CreatorProfile(
        platform=CreatorPlatform.YOUTUBE,
        handle="UC123",
        display_name="Workflow Lab",
        source_url="https://www.youtube.com/channel/UC123",
        subscriber_count=10_000,
        total_views=100_000,
        topics=["workflow"],
        keywords=["workflow", "apps"],
        brand_mentions=[],
        hashtags=[],
        existing_sponsors=[],
        average_engagement=500,
        engagement_rate=0.05,
        niche="Productivity tech",
        audience_summary="Creators and remote workers.",
        content_themes=["workflow", "apps"],
        previous_sponsors=[],
        collaboration_opportunities=["sponsored videos"],
        estimated_pricing="$1,000-$2,000",
    )


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        app_name="Test",
        app_env="test",
        logging=LoggingSettings(level="INFO"),
        database=DatabaseSettings(url=f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite3'}"),
        paths=PathSettings(
            cache_dir=tmp_path / "cache",
            output_dir=tmp_path / "outputs",
            prompts_dir=tmp_path / "prompts",
        ),
        http=HttpSettings(timeout_seconds=1, max_retries=1),
        openai=OpenAISettings(api_key=None, model="test-model"),
        google=GoogleSettings(),
        apollo=ApolloSettings(),
        github=GitHubSettings(),
        playwright=PlaywrightSettings(headless=True),
        creator_analysis=CreatorAnalysisSettings(),
        similar_discovery=SimilarDiscoverySettings(),
        brand_discovery=BrandDiscoverySettings(),
        brand_scoring=BrandScoringSettings(),
        contact_discovery=ContactDiscoverySettings(),
        outreach=OutreachSettings(cache_ttl_seconds=3600, max_words=150),
    )
