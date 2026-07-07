from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, HttpUrl, model_validator

from creator_outreach_automation.models.base import AppModel


class CreatorPlatform(StrEnum):
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


class CreatorAnalysisInput(AppModel):
    instagram_username: str | None = None
    youtube_url: str | None = None

    @model_validator(mode="after")
    def validate_single_source(self) -> CreatorAnalysisInput:
        if bool(self.instagram_username) == bool(self.youtube_url):
            raise ValueError("Provide exactly one of instagram_username or youtube_url.")
        return self

    @property
    def platform(self) -> CreatorPlatform:
        if self.youtube_url:
            return CreatorPlatform.YOUTUBE
        if self.instagram_username:
            return CreatorPlatform.INSTAGRAM
        raise ValueError("Either instagram_username or youtube_url is required.")

    @property
    def cache_identity(self) -> str:
        if self.youtube_url:
            return f"youtube:{self.youtube_url.strip().lower()}"
        if self.instagram_username:
            return f"instagram:{self.instagram_username.strip().lower().lstrip('@')}"
        raise ValueError("Either instagram_username or youtube_url is required.")


class YouTubeVideo(AppModel):
    video_id: str
    title: str
    description: str = ""
    url: HttpUrl | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    published_at: str | None = None


class YouTubeCreatorSnapshot(AppModel):
    platform: CreatorPlatform = CreatorPlatform.YOUTUBE
    channel_id: str
    channel_title: str
    channel_url: HttpUrl | None = None
    subscriber_count: int | None = None
    view_count: int | None = None
    videos: list[YouTubeVideo] = Field(default_factory=list)


class InstagramPost(AppModel):
    shortcode: str | None = None
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    like_count: int | None = None
    comment_count: int | None = None
    url: HttpUrl | None = None
    published_at: str | None = None


class InstagramCreatorSnapshot(AppModel):
    platform: CreatorPlatform = CreatorPlatform.INSTAGRAM
    username: str
    full_name: str | None = None
    bio: str = ""
    followers: int | None = None
    following: int | None = None
    posts_count: int | None = None
    recent_posts: list[InstagramPost] = Field(default_factory=list)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class CreatorAnalysisExtracts(AppModel):
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    brand_mentions: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    existing_sponsors: list[str] = Field(default_factory=list)
    average_engagement: float | None = None
    engagement_rate: float | None = None


class CreatorProfile(AppModel):
    platform: CreatorPlatform
    handle: str
    display_name: str | None = None
    source_url: HttpUrl | None = None
    subscriber_count: int | None = None
    follower_count: int | None = None
    total_views: int | None = None
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    brand_mentions: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    existing_sponsors: list[str] = Field(default_factory=list)
    average_engagement: float | None = None
    engagement_rate: float | None = None
    niche: str
    audience_summary: str
    content_themes: list[str] = Field(default_factory=list)
    previous_sponsors: list[str] = Field(default_factory=list)
    collaboration_opportunities: list[str] = Field(default_factory=list)
    estimated_pricing: str
    raw_summary: str | None = None
