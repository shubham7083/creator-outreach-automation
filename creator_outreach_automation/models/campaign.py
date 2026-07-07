from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import Field

from creator_outreach_automation.models.base import EntityModel


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class Campaign(EntityModel):
    name: str = Field(min_length=1)
    brand_id: str | None = None
    status: CampaignStatus = CampaignStatus.DRAFT
    starts_on: date | None = None
    ends_on: date | None = None
    objective: str | None = None
