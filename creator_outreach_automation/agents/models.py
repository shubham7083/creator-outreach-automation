from __future__ import annotations

from pydantic import Field

from creator_outreach_automation.models.base import AppModel
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.brand_scoring import BrandScoringResult, ScoredBrand
from creator_outreach_automation.models.contact import Contact
from creator_outreach_automation.models.creator_analysis import CreatorAnalysisInput, CreatorProfile
from creator_outreach_automation.models.outreach import OutreachGenerationInput, OutreachSequenceResult


class CreatorAgentInput(AppModel):
    analysis_input: CreatorAnalysisInput


class CreatorAgentOutput(AppModel):
    creator_profile: CreatorProfile


class BrandDiscoveryAgentInput(AppModel):
    creator_profile: CreatorProfile


class BrandDiscoveryAgentOutput(AppModel):
    brands: list[Brand] = Field(default_factory=list)


class BrandWebsiteSummary(AppModel):
    brand: Brand
    website_summary: str = Field(min_length=1)


class ScoringAgentInput(AppModel):
    creator_profile: CreatorProfile
    brand_summaries: list[BrandWebsiteSummary] = Field(default_factory=list)


class ScoringAgentOutput(AppModel):
    scoring_result: BrandScoringResult


class ContactAgentInput(AppModel):
    brands: list[Brand] = Field(default_factory=list)


class ContactAgentOutput(AppModel):
    contacts: list[Contact] = Field(default_factory=list)


class EmailAgentInput(AppModel):
    outreach_requests: list[OutreachGenerationInput] = Field(default_factory=list)


class EmailAgentOutput(AppModel):
    sequences: list[OutreachSequenceResult] = Field(default_factory=list)


class CRMStatus(AppModel):
    creator_handle: str | None = None
    brand_count: int = 0
    scored_count: int = 0
    approved_count: int = 0
    contact_count: int = 0
    outreach_sequence_count: int = 0
    next_actions: list[str] = Field(default_factory=list)


class CRMAgentInput(AppModel):
    creator_profile: CreatorProfile | None = None
    brands: list[Brand] = Field(default_factory=list)
    scored_brands: list[ScoredBrand] = Field(default_factory=list)
    contacts: list[Contact] = Field(default_factory=list)
    outreach_sequences: list[OutreachSequenceResult] = Field(default_factory=list)


class CRMAgentOutput(AppModel):
    status: CRMStatus
