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
)
from creator_outreach_automation.models.creator_analysis import (
    CreatorAnalysisExtracts,
    CreatorAnalysisInput,
    CreatorProfile,
    InstagramCreatorSnapshot,
    YouTubeCreatorSnapshot,
    YouTubeVideo,
)
from creator_outreach_automation.services.creator_analysis import CreatorAnalysisService


class FakeYouTubeCollector:
    def __init__(self) -> None:
        self.calls = 0

    async def collect_channel(self, youtube_url: str, *, max_videos: int) -> YouTubeCreatorSnapshot:
        self.calls += 1
        assert max_videos == 20
        return YouTubeCreatorSnapshot(
            channel_id="UC123",
            channel_title="Workflow Lab",
            subscriber_count=1_000,
            view_count=100_000,
            videos=[
                YouTubeVideo(
                    video_id="v1",
                    title="Workflow with @Acme #productivity",
                    description="Sponsored by Acme.",
                    like_count=80,
                    comment_count=20,
                )
            ],
        )


class FakeInstagramCollector:
    async def collect_profile(self, username: str, *, max_posts: int) -> InstagramCreatorSnapshot:
        raise AssertionError("Instagram collector should not be called")


class FakeProfileGenerator:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(
        self,
        *,
        snapshot: YouTubeCreatorSnapshot | InstagramCreatorSnapshot,
        extracts: CreatorAnalysisExtracts,
    ) -> CreatorProfile:
        self.calls += 1
        assert extracts.average_engagement == 100
        return CreatorProfile(
            platform=snapshot.platform,
            handle="UC123",
            display_name="Workflow Lab",
            subscriber_count=1_000,
            total_views=100_000,
            topics=extracts.topics,
            keywords=extracts.keywords,
            brand_mentions=extracts.brand_mentions,
            hashtags=extracts.hashtags,
            existing_sponsors=extracts.existing_sponsors,
            average_engagement=extracts.average_engagement,
            engagement_rate=extracts.engagement_rate,
            niche="Productivity",
            audience_summary="Remote workers and creators.",
            content_themes=["workflow"],
            previous_sponsors=extracts.existing_sponsors,
            collaboration_opportunities=["app walkthroughs"],
            estimated_pricing="$500-$1,500",
        )


@pytest.mark.asyncio
async def test_creator_analysis_service_caches_profile(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    youtube_collector = FakeYouTubeCollector()
    profile_generator = FakeProfileGenerator()
    service = CreatorAnalysisService(
        youtube_collector=youtube_collector,
        instagram_collector=FakeInstagramCollector(),
        profile_generator=profile_generator,  # type: ignore[arg-type]
        settings=settings,
    )
    analysis_input = CreatorAnalysisInput(youtube_url="https://www.youtube.com/channel/UC123")

    first = await service.analyze(analysis_input)
    second = await service.analyze(analysis_input)

    assert first == second
    assert youtube_collector.calls == 1
    assert profile_generator.calls == 1


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
    )
