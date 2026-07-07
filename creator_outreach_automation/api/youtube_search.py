from __future__ import annotations

import logging

import httpx

from creator_outreach_automation.config import GoogleSettings, HttpSettings
from creator_outreach_automation.models.creator_analysis import CreatorPlatform
from creator_outreach_automation.models.similar_discovery import DiscoverySource, SimilarCreatorCandidate

logger = logging.getLogger(__name__)


class YouTubeSearchError(RuntimeError):
    """Raised when YouTube creator search fails."""


class YouTubeCreatorSearchClient:
    def __init__(self, google_settings: GoogleSettings, http_settings: HttpSettings) -> None:
        self._google_settings = google_settings
        self._http_settings = http_settings

    async def search_creators(self, query: str, *, limit: int) -> list[SimilarCreatorCandidate]:
        api_key = self._api_key()
        try:
            async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds) as client:
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": query,
                        "type": "channel",
                        "maxResults": min(limit, 50),
                        "key": api_key,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as error:
            logger.exception("YouTube creator search failed")
            raise YouTubeSearchError(str(error)) from error

        candidates: list[SimilarCreatorCandidate] = []
        for item in payload.get("items", []):
            channel_id = item.get("snippet", {}).get("channelId")
            title = item.get("snippet", {}).get("channelTitle")
            if not isinstance(channel_id, str):
                continue
            candidates.append(
                SimilarCreatorCandidate(
                    platform=CreatorPlatform.YOUTUBE,
                    handle=channel_id,
                    source_url=f"https://www.youtube.com/channel/{channel_id}",
                    display_name=title if isinstance(title, str) else None,
                    discovery_source=DiscoverySource.YOUTUBE,
                    match_reasons=[f"YouTube channel search result for query: {query}"],
                )
            )
        return candidates

    def _api_key(self) -> str:
        if self._google_settings.youtube_api_key is None:
            raise YouTubeSearchError("YOUTUBE_API_KEY is required for YouTube discovery.")
        return self._google_settings.youtube_api_key.get_secret_value()
