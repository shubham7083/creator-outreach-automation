from __future__ import annotations

from pydantic import Field, HttpUrl

from creator_outreach_automation.models.base import EntityModel


class Brand(EntityModel):
    name: str = Field(min_length=1)
    website: HttpUrl | None = None
    description: str | None = None
    industry: str | None = None
    location: str | None = None
    socials: dict[str, str] = Field(default_factory=dict)
    discovery_sources: list[str] = Field(default_factory=list)
    contact_email: str | None = None
    notes: str | None = None
