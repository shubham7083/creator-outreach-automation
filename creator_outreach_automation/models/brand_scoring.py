from __future__ import annotations

from pydantic import Field

from creator_outreach_automation.models.base import AppModel
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.creator_analysis import CreatorProfile


class BrandScoringInput(AppModel):
    creator_profile: CreatorProfile
    brand: Brand
    website_summary: str = Field(min_length=1)


class BrandScore(AppModel):
    score: float = Field(ge=0.0, le=10.0)
    reason: str = Field(min_length=1)
    campaign_idea: str = Field(min_length=1)
    estimated_pricing: str = Field(min_length=1)
    email_hook: str = Field(min_length=1)


class ScoredBrand(AppModel):
    brand: Brand
    score: BrandScore
    accepted: bool


class BrandScoringResult(AppModel):
    creator_profile: CreatorProfile
    ranked_brands: list[ScoredBrand] = Field(default_factory=list)
    rejected_brands: list[ScoredBrand] = Field(default_factory=list)
