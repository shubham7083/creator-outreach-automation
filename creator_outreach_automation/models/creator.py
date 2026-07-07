from __future__ import annotations

from pydantic import Field, HttpUrl

from creator_outreach_automation.models.base import EntityModel


class Creator(EntityModel):
    display_name: str = Field(min_length=1)
    handle: str | None = None
    channel_url: HttpUrl | None = None
    email: str | None = None
    niche: str | None = None
    notes: str | None = None
