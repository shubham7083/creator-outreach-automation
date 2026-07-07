from __future__ import annotations

from pathlib import Path

import pytest

from creator_outreach_automation.config import (
    ApolloSettings,
    BrandDiscoverySettings,
    BrandScoringSettings,
    CreatorAnalysisSettings,
    DatabaseSettings,
    GitHubSettings,
    GoogleSettings,
    HttpSettings,
    LoggingSettings,
    OpenAISettings,
    PathSettings,
    PlaywrightSettings,
    Settings,
    SimilarDiscoverySettings,
)
from creator_outreach_automation.database.brand_score_repository import BrandScoreRepository
from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.brand_scoring import BrandScore, BrandScoringInput
from creator_outreach_automation.models.creator_analysis import CreatorPlatform, CreatorProfile
from creator_outreach_automation.services.brand_scoring import (
    BrandScoringEngine,
    CodexBrandScoreClient,
    _parse_brand_score,
)


class FlakyScoreClient:
    def __init__(self) -> None:
        self.calls = 0

    async def score(self, scoring_input: BrandScoringInput) -> BrandScore:
        self.calls += 1
        if scoring_input.brand.name == "Great Fit":
            return BrandScore(
                score=8.5,
                reason="Strong niche and audience fit.",
                campaign_idea="Workflow challenge sponsored integration.",
                estimated_pricing="$1,500-$3,000",
                email_hook="Your workflow product maps directly to this creator's audience.",
            )
        return BrandScore(
            score=4.5,
            reason="Weak niche fit.",
            campaign_idea="Generic awareness post.",
            estimated_pricing="$250-$500",
            email_hook="Testing a small awareness angle could work.",
        )


@pytest.mark.asyncio
async def test_brand_scoring_rejects_ranks_caches_and_saves(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    score_client = FlakyScoreClient()
    repository = BrandScoreRepository(SQLiteDatabase(settings.database.sqlite_path))
    engine = BrandScoringEngine(
        score_client=score_client,
        score_repository=repository,
        settings=settings,
    )
    creator = _creator_profile()
    great = Brand(name="Great Fit", website="https://great.example", description="Workflow software")
    weak = Brand(name="Weak Fit", website="https://weak.example", description="Unrelated product")

    first = await engine.score_brands(
        creator_profile=creator,
        brand_summaries=[
            (weak, "A consumer product unrelated to productivity."),
            (great, "A workflow platform for creators and remote teams."),
        ],
    )
    second = await engine.score_brands(
        creator_profile=creator,
        brand_summaries=[
            (weak, "A consumer product unrelated to productivity."),
            (great, "A workflow platform for creators and remote teams."),
        ],
    )

    assert first == second
    assert [item.brand.name for item in first.ranked_brands] == ["Great Fit"]
    assert [item.brand.name for item in first.rejected_brands] == ["Weak Fit"]
    assert score_client.calls == 2


def test_parse_brand_score_accepts_json_only_contract() -> None:
    score = _parse_brand_score(
        """
        {
          "score": 7,
          "reason": "Good fit.",
          "campaign_idea": "Launch integration.",
          "estimated_pricing": "$1,000",
          "email_hook": "A concise hook."
        }
        """
    )

    assert score.score == 7
    assert score.reason == "Good fit."


@pytest.mark.asyncio
async def test_codex_brand_score_client_retries_until_valid_json() -> None:
    class RetryCodex:
        def __init__(self) -> None:
            self.calls = 0

        async def run_task(self, prompt: str, *, system_prompt: str | None = None) -> str:
            self.calls += 1
            if self.calls == 1:
                return "not json"
            return (
                '{"score": 8, "reason": "Good fit.", "campaign_idea": "Launch series.", '
                '"estimated_pricing": "$1,000", "email_hook": "Great fit."}'
            )

    codex = RetryCodex()
    client = CodexBrandScoreClient(codex, max_retries=2)  # type: ignore[arg-type]

    score = await client.score(
        BrandScoringInput(
            creator_profile=_creator_profile(),
            brand=Brand(name="Retry Brand", website="https://retry.example"),
            website_summary="A relevant workflow product.",
        )
    )

    assert score.score == 8
    assert codex.calls == 2


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
        brand_scoring=BrandScoringSettings(
            cache_ttl_seconds=3600,
            min_score=6,
            max_retries=3,
        ),
    )
