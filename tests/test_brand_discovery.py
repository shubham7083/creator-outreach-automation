from __future__ import annotations

from pathlib import Path

import pytest

from creator_outreach_automation.config import (
    ApolloSettings,
    BrandDiscoverySettings,
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
from creator_outreach_automation.database.brand_repository import BrandRepository, normalize_domain
from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.models.brand_discovery import BrandCandidate, BrandDiscoverySource
from creator_outreach_automation.models.creator_analysis import CreatorPlatform, CreatorProfile
from creator_outreach_automation.services.brand_discovery import BrandDiscoveryEngine


class FakeProvider:
    def __init__(self, candidates: list[BrandCandidate]) -> None:
        self._candidates = candidates
        self.calls = 0

    async def discover(self, niche_terms: list[str], *, limit: int) -> list[BrandCandidate]:
        self.calls += 1
        assert "productivity tech" in niche_terms
        return self._candidates[:limit]


class FakeEnricher:
    async def enrich(self, candidate: BrandCandidate) -> BrandCandidate:
        return candidate.model_copy(
            update={
                "description": candidate.description or "Enriched company description.",
                "socials": {**candidate.socials, "twitter": "https://x.com/example"},
            }
        )


@pytest.mark.asyncio
async def test_brand_discovery_dedupes_persists_and_caches(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    provider = FakeProvider(
        [
            BrandCandidate(
                name="Acme",
                website="https://www.acme.com",
                description="Workflow tools.",
                industry="SaaS",
                source=BrandDiscoverySource.GOOGLE_SEARCH,
                confidence=0.8,
            ),
            BrandCandidate(
                name="Acme Inc",
                website="https://acme.com/pricing",
                source=BrandDiscoverySource.PRODUCT_HUNT,
                confidence=0.9,
            ),
            BrandCandidate(
                name="Bright App",
                website="https://bright.example",
                source=BrandDiscoverySource.Y_COMBINATOR,
                confidence=0.7,
            ),
        ]
    )
    engine = BrandDiscoveryEngine(
        providers=[provider],
        brand_repository=BrandRepository(SQLiteDatabase(settings.database.sqlite_path)),
        website_enricher=FakeEnricher(),
        settings=settings,
    )

    first = await engine.discover(_creator_profile())
    second = await engine.discover(_creator_profile())

    assert first == second
    assert len(first) == 2
    assert {brand.name for brand in first} == {"Acme Inc", "Bright App"}
    assert all(brand.socials.get("twitter") == "https://x.com/example" for brand in first)
    assert provider.calls == 1


def test_normalize_domain_removes_www_and_paths() -> None:
    assert normalize_domain("https://www.example.com/pricing") == "example.com"


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
        brand_discovery=BrandDiscoverySettings(
            cache_ttl_seconds=3600,
            results_per_source=10,
            max_brands=10,
        ),
    )
