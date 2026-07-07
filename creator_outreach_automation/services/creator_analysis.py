from __future__ import annotations

import logging
from typing import Protocol

from creator_outreach_automation.config import Settings, get_settings
from creator_outreach_automation.models.creator_analysis import (
    CreatorAnalysisInput,
    CreatorPlatform,
    CreatorProfile,
    InstagramCreatorSnapshot,
    YouTubeCreatorSnapshot,
)
from creator_outreach_automation.services.creator_analysis_extraction import CreatorSignalExtractor
from creator_outreach_automation.services.creator_profile_generation import CreatorProfileGenerator
from creator_outreach_automation.utils.cache import JsonCache

logger = logging.getLogger(__name__)


class YouTubeCollector(Protocol):
    async def collect_channel(self, youtube_url: str, *, max_videos: int) -> YouTubeCreatorSnapshot:
        ...


class InstagramCollector(Protocol):
    async def collect_profile(self, username: str, *, max_posts: int) -> InstagramCreatorSnapshot:
        ...


class CreatorAnalysisService:
    def __init__(
        self,
        *,
        youtube_collector: YouTubeCollector,
        instagram_collector: InstagramCollector,
        profile_generator: CreatorProfileGenerator,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._youtube_collector = youtube_collector
        self._instagram_collector = instagram_collector
        self._profile_generator = profile_generator
        self._extractor = CreatorSignalExtractor(
            keyword_limit=self._settings.creator_analysis.keyword_limit,
        )
        self._profile_cache = JsonCache(
            self._settings.paths.cache_dir,
            namespace="creator_profiles",
            ttl_seconds=self._settings.creator_analysis.cache_ttl_seconds,
        )
        self._youtube_cache = JsonCache(
            self._settings.paths.cache_dir,
            namespace="youtube_snapshots",
            ttl_seconds=self._settings.creator_analysis.cache_ttl_seconds,
        )
        self._instagram_cache = JsonCache(
            self._settings.paths.cache_dir,
            namespace="instagram_snapshots",
            ttl_seconds=self._settings.creator_analysis.cache_ttl_seconds,
        )

    async def analyze(self, analysis_input: CreatorAnalysisInput) -> CreatorProfile:
        cached_profile = await self._profile_cache.get_model(
            analysis_input.cache_identity,
            CreatorProfile,
        )
        if cached_profile:
            logger.info("Returning cached creator profile for %s", analysis_input.cache_identity)
            return cached_profile

        if analysis_input.platform == CreatorPlatform.YOUTUBE:
            snapshot = await self._youtube_snapshot(analysis_input)
            extracts = self._extractor.extract_from_youtube(snapshot)
        else:
            snapshot = await self._instagram_snapshot(analysis_input)
            extracts = self._extractor.extract_from_instagram(snapshot)

        profile = await self._profile_generator.generate(snapshot=snapshot, extracts=extracts)
        await self._profile_cache.set_model(analysis_input.cache_identity, profile)
        logger.info("Creator analysis completed for %s", analysis_input.cache_identity)
        return profile

    async def _youtube_snapshot(self, analysis_input: CreatorAnalysisInput) -> YouTubeCreatorSnapshot:
        if analysis_input.youtube_url is None:
            raise ValueError("youtube_url is required for YouTube creator analysis.")

        cached = await self._youtube_cache.get_model(
            analysis_input.cache_identity,
            YouTubeCreatorSnapshot,
        )
        if cached:
            logger.info("Returning cached YouTube snapshot for %s", analysis_input.cache_identity)
            return cached

        snapshot = await self._youtube_collector.collect_channel(
            analysis_input.youtube_url,
            max_videos=self._settings.creator_analysis.youtube_video_count,
        )
        await self._youtube_cache.set_model(analysis_input.cache_identity, snapshot)
        return snapshot

    async def _instagram_snapshot(
        self,
        analysis_input: CreatorAnalysisInput,
    ) -> InstagramCreatorSnapshot:
        if analysis_input.instagram_username is None:
            raise ValueError("instagram_username is required for Instagram creator analysis.")

        cached = await self._instagram_cache.get_model(
            analysis_input.cache_identity,
            InstagramCreatorSnapshot,
        )
        if cached:
            logger.info("Returning cached Instagram snapshot for %s", analysis_input.cache_identity)
            return cached

        snapshot = await self._instagram_collector.collect_profile(
            analysis_input.instagram_username,
            max_posts=self._settings.creator_analysis.instagram_post_count,
        )
        await self._instagram_cache.set_model(analysis_input.cache_identity, snapshot)
        return snapshot
