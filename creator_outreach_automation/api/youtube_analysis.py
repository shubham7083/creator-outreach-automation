from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlparse

import httpx

from creator_outreach_automation.config import GoogleSettings, HttpSettings
from creator_outreach_automation.models.creator_analysis import YouTubeCreatorSnapshot, YouTubeVideo

logger = logging.getLogger(__name__)


class YouTubeAnalysisError(RuntimeError):
    """Raised when YouTube creator analysis fails."""


class YouTubeAnalysisClient:
    def __init__(self, google_settings: GoogleSettings, http_settings: HttpSettings) -> None:
        self._google_settings = google_settings
        self._http_settings = http_settings

    async def collect_channel(self, youtube_url: str, *, max_videos: int) -> YouTubeCreatorSnapshot:
        api_key = self._api_key()
        channel_id = await self._resolve_channel_id(youtube_url, api_key=api_key)
        async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds) as client:
            channel_payload = await self._get_json(
                client,
                "https://www.googleapis.com/youtube/v3/channels",
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": channel_id,
                    "key": api_key,
                },
            )
            items = channel_payload.get("items", [])
            if not items:
                raise YouTubeAnalysisError(f"YouTube channel not found: {youtube_url}")

            channel = items[0]
            snippet = channel["snippet"]
            statistics = channel.get("statistics", {})
            uploads_playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]
            videos = await self._latest_videos(
                client,
                uploads_playlist_id=uploads_playlist,
                api_key=api_key,
                max_videos=max_videos,
            )

        return YouTubeCreatorSnapshot(
            channel_id=channel_id,
            channel_title=snippet.get("title", ""),
            channel_url=f"https://www.youtube.com/channel/{channel_id}",
            subscriber_count=_optional_int(statistics.get("subscriberCount")),
            view_count=_optional_int(statistics.get("viewCount")),
            videos=videos,
        )

    async def _resolve_channel_id(self, youtube_url: str, *, api_key: str) -> str:
        direct_id = _extract_channel_id(youtube_url)
        if direct_id:
            return direct_id

        handle = _extract_handle(youtube_url)
        if not handle:
            video_id = _extract_video_id(youtube_url)
            if video_id:
                return await self._channel_id_from_video(video_id, api_key=api_key)
            raise YouTubeAnalysisError(f"Unable to resolve YouTube URL: {youtube_url}")

        async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds) as client:
            payload = await self._get_json(
                client,
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": handle,
                    "type": "channel",
                    "maxResults": 1,
                    "key": api_key,
                },
            )
        items = payload.get("items", [])
        if not items:
            raise YouTubeAnalysisError(f"No YouTube channel found for handle: {handle}")
        return items[0]["snippet"]["channelId"]

    async def _channel_id_from_video(self, video_id: str, *, api_key: str) -> str:
        async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds) as client:
            payload = await self._get_json(
                client,
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "snippet", "id": video_id, "key": api_key},
            )
        items = payload.get("items", [])
        if not items:
            raise YouTubeAnalysisError(f"No YouTube video found for id: {video_id}")
        return items[0]["snippet"]["channelId"]

    async def _latest_videos(
        self,
        client: httpx.AsyncClient,
        *,
        uploads_playlist_id: str,
        api_key: str,
        max_videos: int,
    ) -> list[YouTubeVideo]:
        playlist_payload = await self._get_json(
            client,
            "https://www.googleapis.com/youtube/v3/playlistItems",
            params={
                "part": "snippet",
                "playlistId": uploads_playlist_id,
                "maxResults": max_videos,
                "key": api_key,
            },
        )
        video_ids = [
            item["snippet"]["resourceId"]["videoId"]
            for item in playlist_payload.get("items", [])
            if item.get("snippet", {}).get("resourceId", {}).get("videoId")
        ]
        if not video_ids:
            return []

        videos_payload = await self._get_json(
            client,
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,statistics",
                "id": ",".join(video_ids),
                "key": api_key,
            },
        )
        videos: list[YouTubeVideo] = []
        for item in videos_payload.get("items", []):
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            video_id = item["id"]
            videos.append(
                YouTubeVideo(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    view_count=_optional_int(statistics.get("viewCount")),
                    like_count=_optional_int(statistics.get("likeCount")),
                    comment_count=_optional_int(statistics.get("commentCount")),
                    published_at=snippet.get("publishedAt"),
                )
            )
        return videos

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        params: dict[str, object],
    ) -> dict[str, object]:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as error:
            logger.exception("YouTube API request failed")
            raise YouTubeAnalysisError(str(error)) from error
        if not isinstance(payload, dict):
            raise YouTubeAnalysisError("YouTube API returned a non-object JSON payload.")
        return payload

    def _api_key(self) -> str:
        if self._google_settings.youtube_api_key is None:
            raise YouTubeAnalysisError("YOUTUBE_API_KEY is required for YouTube creator analysis.")
        return self._google_settings.youtube_api_key.get_secret_value()


def _extract_channel_id(youtube_url: str) -> str | None:
    parsed = urlparse(youtube_url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "channel":
        return parts[1]
    return None


def _extract_handle(youtube_url: str) -> str | None:
    parsed = urlparse(youtube_url)
    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0].startswith("@"):
        return parts[0]
    if len(parts) >= 2 and parts[0] in {"c", "user"}:
        return parts[1]
    return None


def _extract_video_id(youtube_url: str) -> str | None:
    parsed = urlparse(youtube_url)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.strip("/") or None
    query_id = parse_qs(parsed.query).get("v")
    if query_id:
        return query_id[0]
    return None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
