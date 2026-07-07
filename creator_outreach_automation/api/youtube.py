from __future__ import annotations

import logging

from creator_outreach_automation.config import GoogleSettings, HttpSettings

logger = logging.getLogger(__name__)


class YouTubeDataClient:
    def __init__(self, google_settings: GoogleSettings, http_settings: HttpSettings) -> None:
        self._google_settings = google_settings
        self._http_settings = http_settings

    async def search_channels(self, query: str, *, max_results: int = 10) -> dict[str, object]:
        logger.info("Searching YouTube channels for query=%s max_results=%s", query, max_results)
        if self._google_settings.youtube_api_key is None:
            logger.warning("Skipping YouTube search because YOUTUBE_API_KEY is not configured.")
            return {"items": []}

        import httpx

        try:
            async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds) as client:
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": query,
                        "type": "channel",
                        "maxResults": max_results,
                        "key": self._google_settings.youtube_api_key.get_secret_value(),
                    },
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as error:
            logger.warning("YouTube search failed for query=%s: %s", query, error)
            return {"items": []}
        return data if isinstance(data, dict) else {"items": []}
