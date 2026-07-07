from __future__ import annotations

from enum import StrEnum

from pydantic import Field, HttpUrl

from creator_outreach_automation.models.base import EntityModel


class ContactRole(StrEnum):
    MARKETING = "marketing"
    GROWTH = "growth"
    PARTNERSHIPS = "partnerships"
    CREATOR_MANAGER = "creator_manager"
    INFLUENCER_MANAGER = "influencer_manager"


class ContactSource(StrEnum):
    APOLLO = "apollo"
    COMPANY_WEBSITE = "company_website"
    LINKEDIN_SEARCH = "linkedin_search"


class Contact(EntityModel):
    brand_id: str
    brand_name: str
    name: str | None = None
    title: str | None = None
    email: str | None = None
    linkedin: HttpUrl | None = None
    role: ContactRole | None = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    sources: list[ContactSource] = Field(default_factory=list)


class ContactDiscoveryResult(EntityModel):
    brand_id: str
    brand_name: str
    contacts: list[Contact] = Field(default_factory=list)
