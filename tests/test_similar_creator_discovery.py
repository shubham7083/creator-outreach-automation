from __future__ import annotations

from pathlib import Path

import pytest

from creator_outreach_automation.config import (
    ApolloSettings,
    CreatorAnalysisSettings,
    DatabaseSettings,
    GoogleSettings,
    HttpSettings,
    LoggingSettings,
    OpenAISettings,
    PathSettings,
    PlaywrightSettings,
    Settings,
    SimilarDiscoverySettings,
)
from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.database.sponsor_knowledge_base import SponsorKnowledgeBase
from creator_outreach_automation.models.creator_analysis import (
    CreatorAnalysisInput,
    CreatorPlatform,
    CreatorProfile,
)
from creator_outreach_automation.models.similar_discovery import (
    DiscoverySource,
    SimilarCreatorCandidate,
)
from creator_outreach_automation.services.similar_creator_discovery import (
    SimilarCreatorDiscoveryService,
)


class FakeSearchClient:
    def __init__(self, candidates: list[SimilarCreatorCandidate]) -> None:
        self._candidates = candidates
        self.calls = 0

    async def search_creators(self, query: str, *, limit: int) -> list[SimilarCreatorCandidate]:
        self.calls += 1
        return self._candidates[:limit]


class FakeAnalysisService:
    def __init__(self) -> None:
        self.calls: list[CreatorAnalysisInput] = []

    async def analyze(self, analysis_input: CreatorAnalysisInput) -> CreatorProfile:
        self.calls.append(analysis_input)
        if analysis_input.youtube_url and "UC-A" in analysis_input.youtube_url:
            return _profile(
                handle="UC-A",
                niche="Productivity tech",
                keywords=["workflow", "apps", "desk"],
                themes=["workflow", "desk setup"],
                sponsors=["acme"],
                mentions=["bright app"],
                engagement_rate=0.04,
            )
        return _profile(
            handle="UC-B",
            niche="Fitness cooking",
            keywords=["fitness", "meals"],
            themes=["meal prep"],
            sponsors=["fresh box"],
            mentions=[],
            engagement_rate=0.01,
        )


@pytest.mark.asyncio
async def test_similar_creator_discovery_ranks_and_caches(tmp_path: Path) -> None:
    seed = _profile(
        handle="UC-SEED",
        niche="Productivity tech",
        keywords=["workflow", "apps"],
        themes=["workflow"],
        sponsors=["acme"],
        mentions=["bright app"],
        engagement_rate=0.03,
    )
    duplicate = SimilarCreatorCandidate(
        platform=CreatorPlatform.YOUTUBE,
        handle="UC-A",
        source_url="https://www.youtube.com/channel/UC-A",
        discovery_source=DiscoverySource.GOOGLE,
        match_reasons=["google"],
    )
    google_search = FakeSearchClient([duplicate, duplicate])
    youtube_search = FakeSearchClient(
        [
            SimilarCreatorCandidate(
                platform=CreatorPlatform.YOUTUBE,
                handle="UC-A",
                source_url="https://www.youtube.com/channel/UC-A",
                discovery_source=DiscoverySource.YOUTUBE,
                match_reasons=["youtube"],
            ),
            SimilarCreatorCandidate(
                platform=CreatorPlatform.YOUTUBE,
                handle="UC-B",
                source_url="https://www.youtube.com/channel/UC-B",
                discovery_source=DiscoverySource.YOUTUBE,
                match_reasons=["youtube"],
            ),
        ]
    )
    analysis = FakeAnalysisService()
    settings = _settings(tmp_path)
    service = SimilarCreatorDiscoveryService(
        google_search_client=google_search,
        youtube_search_client=youtube_search,
        creator_analysis_service=analysis,  # type: ignore[arg-type]
        sponsor_knowledge_base=SponsorKnowledgeBase(SQLiteDatabase(settings.database.sqlite_path)),
        settings=settings,
    )

    first = await service.discover(seed)
    second = await service.discover(seed)

    assert first == second
    assert len(first.ranked_creators) == 2
    assert first.ranked_creators[0].profile.handle == "UC-A"
    assert first.ranked_creators[0].score > first.ranked_creators[1].score
    assert "acme" in first.recurring_brands
    assert len(analysis.calls) == 2
    assert google_search.calls > 0
    assert youtube_search.calls > 0


def _profile(
    *,
    handle: str,
    niche: str,
    keywords: list[str],
    themes: list[str],
    sponsors: list[str],
    mentions: list[str],
    engagement_rate: float,
) -> CreatorProfile:
    return CreatorProfile(
        platform=CreatorPlatform.YOUTUBE,
        handle=handle,
        display_name=handle,
        source_url=f"https://www.youtube.com/channel/{handle}",
        subscriber_count=10_000,
        total_views=100_000,
        topics=keywords[:2],
        keywords=keywords,
        brand_mentions=mentions,
        hashtags=[],
        existing_sponsors=sponsors,
        average_engagement=400,
        engagement_rate=engagement_rate,
        niche=niche,
        audience_summary="Creators and buyers in the niche.",
        content_themes=themes,
        previous_sponsors=sponsors,
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
        playwright=PlaywrightSettings(headless=True),
        creator_analysis=CreatorAnalysisSettings(
            cache_ttl_seconds=3600,
            youtube_video_count=20,
            instagram_post_count=12,
            keyword_limit=20,
        ),
        similar_discovery=SimilarDiscoverySettings(
            cache_ttl_seconds=3600,
            google_result_limit=10,
            youtube_result_limit=10,
            max_creators_to_analyze=10,
        ),
    )
