from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from creator_outreach_automation.config import GoogleSettings, HttpSettings
from creator_outreach_automation.models.creator_analysis import CreatorPlatform
from creator_outreach_automation.models.similar_discovery import DiscoverySource, SimilarCreatorCandidate

logger = logging.getLogger(__name__)


class GoogleSearchError(RuntimeError):
    """Raised when Google creator search fails."""


class GoogleCreatorSearchClient:
    def __init__(self, google_settings: GoogleSettings, http_settings: HttpSettings) -> None:
        self._google_settings = google_settings
        self._http_settings = http_settings

    async def search_creators(self, query: str, *, limit: int) -> list[SimilarCreatorCandidate]:
        api_key = self._api_key()
        search_engine_id = self._search_engine_id()
        try:
            async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds) as client:
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": api_key,
                        "cx": search_engine_id,
                        "q": query,
                        "num": min(limit, 10),
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as error:
            logger.exception("Google creator search failed")
            raise GoogleSearchError(str(error)) from error

        candidates: list[SimilarCreatorCandidate] = []
        for item in payload.get("items", []):
            link = item.get("link")
            title = item.get("title")
            if not isinstance(link, str):
                continue
            candidate = candidate_from_url(
                link,
                discovery_source=DiscoverySource.GOOGLE,
                display_name=title if isinstance(title, str) else None,
                match_reasons=[f"Google result for query: {query}"],
            )
            if candidate:
                candidates.append(candidate)
        return candidates

    def _api_key(self) -> str:
        if self._google_settings.search_api_key is None:
            raise GoogleSearchError("GOOGLE_SEARCH_API_KEY is required for Google discovery.")
        return self._google_settings.search_api_key.get_secret_value()

    def _search_engine_id(self) -> str:
        if not self._google_settings.search_engine_id:
            raise GoogleSearchError("GOOGLE_SEARCH_ENGINE_ID is required for Google discovery.")
        return self._google_settings.search_engine_id


def candidate_from_url(
    url: str,
    *,
    discovery_source: DiscoverySource,
    display_name: str | None = None,
    match_reasons: list[str] | None = None,
) -> SimilarCreatorCandidate | None:
    parsed = urlparse(url)
    hostname = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    reasons = match_reasons or []

    if "youtube.com" in hostname or "youtu.be" in hostname:
        handle = _youtube_handle(path_parts, url)
        if handle:
            return SimilarCreatorCandidate(
                platform=CreatorPlatform.YOUTUBE,
                handle=handle,
                source_url=url,
                display_name=display_name,
                discovery_source=discovery_source,
                match_reasons=reasons,
            )

    if "instagram.com" in hostname and path_parts:
        username = path_parts[0].strip().lstrip("@")
        if username and username not in {"p", "reel", "tv", "stories"}:
            return SimilarCreatorCandidate(
                platform=CreatorPlatform.INSTAGRAM,
                handle=username,
                source_url=f"https://www.instagram.com/{username}/",
                display_name=display_name,
                discovery_source=discovery_source,
                match_reasons=reasons,
            )
    return None


def _youtube_handle(path_parts: list[str], original_url: str) -> str | None:
    if not path_parts:
        return None
    if path_parts[0].startswith("@"):
        return path_parts[0]
    if len(path_parts) >= 2 and path_parts[0] in {"channel", "c", "user"}:
        return path_parts[1]
    if "youtu.be" in original_url:
        return None
    return path_parts[0] if path_parts[0] else None
