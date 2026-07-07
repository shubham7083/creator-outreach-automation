from __future__ import annotations

from enum import StrEnum

from pydantic import Field, HttpUrl

from creator_outreach_automation.models.base import AppModel
from creator_outreach_automation.models.creator_analysis import CreatorPlatform, CreatorProfile


class DiscoverySource(StrEnum):
    GOOGLE = "google"
    YOUTUBE = "youtube"


class SponsorMentionType(StrEnum):
    EXISTING_SPONSOR = "existing_sponsor"
    PREVIOUS_SPONSOR = "previous_sponsor"
    BRAND_MENTION = "brand_mention"
    RECURRING_BRAND = "recurring_brand"


class SimilarCreatorCandidate(AppModel):
    platform: CreatorPlatform
    handle: str
    source_url: HttpUrl
    display_name: str | None = None
    discovery_source: DiscoverySource
    match_reasons: list[str] = Field(default_factory=list)

    @property
    def identity(self) -> str:
        return f"{self.platform}:{self.handle.strip().lower().lstrip('@')}"


class RankedSimilarCreator(AppModel):
    profile: CreatorProfile
    score: float
    reasons: list[str] = Field(default_factory=list)
    recurring_brands: list[str] = Field(default_factory=list)


class SponsorKnowledgeBaseRecord(AppModel):
    sponsor_name: str
    creator_identity: str
    source_platform: CreatorPlatform
    mention_type: SponsorMentionType
    context: str | None = None


class SimilarCreatorDiscoveryResult(AppModel):
    seed_profile: CreatorProfile
    ranked_creators: list[RankedSimilarCreator] = Field(default_factory=list)
    recurring_brands: list[str] = Field(default_factory=list)
    analyzed_creator_count: int = 0
    sponsor_record_count: int = 0
