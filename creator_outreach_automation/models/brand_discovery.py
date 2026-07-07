from __future__ import annotations

from enum import StrEnum

from pydantic import Field, HttpUrl

from creator_outreach_automation.models.base import AppModel
from creator_outreach_automation.models.brand import Brand


class BrandDiscoverySource(StrEnum):
    PRODUCT_HUNT = "product_hunt"
    Y_COMBINATOR = "y_combinator"
    GOOGLE_SEARCH = "google_search"
    STARTUP_DIRECTORY = "startup_directory"
    COMPANY_WEBSITE = "company_website"
    GITHUB_ORGANIZATION = "github_organization"
    AI_DIRECTORY = "ai_directory"


class BrandCandidate(AppModel):
    name: str
    website: HttpUrl | None = None
    description: str | None = None
    industry: str | None = None
    location: str | None = None
    socials: dict[str, str] = Field(default_factory=dict)
    source: BrandDiscoverySource
    source_url: HttpUrl | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class BrandDiscoveryResult(AppModel):
    creator_identity: str
    brands: list[Brand] = Field(default_factory=list)
