from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from creator_outreach_automation.models.base import EntityModel
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.creator_analysis import CreatorProfile


class OutreachStatus(StrEnum):
    NEW = "new"
    DRAFTED = "drafted"
    SENT = "sent"
    REPLIED = "replied"
    FAILED = "failed"


class OutreachMessage(EntityModel):
    creator_id: str
    brand_id: str
    campaign_id: str | None = None
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    status: OutreachStatus = OutreachStatus.NEW
    provider_draft_id: str | None = None


class OutreachDraftKind(StrEnum):
    INITIAL = "initial"
    FOLLOW_UP = "follow_up"
    FINAL_FOLLOW_UP = "final_follow_up"


class OutreachGenerationInput(EntityModel):
    creator_profile: CreatorProfile
    brand: Brand
    campaign_idea: str = Field(min_length=1)
    recipient_email: str = Field(min_length=3)
    recipient_name: str | None = None
    recipient_title: str | None = None


class OutreachDraftContent(EntityModel):
    kind: OutreachDraftKind
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_word_count(self) -> "OutreachDraftContent":
        if len(self.body.split()) > 150:
            raise ValueError("Outreach draft body must be under 150 words.")
        return self


class OutreachSequenceContent(EntityModel):
    subject: str = Field(min_length=1)
    email: str = Field(min_length=1)
    follow_up: str = Field(min_length=1)
    final_follow_up: str = Field(min_length=1)


class GmailDraftRecord(EntityModel):
    kind: OutreachDraftKind
    subject: str
    body: str
    gmail_draft_id: str


class OutreachSequenceResult(EntityModel):
    creator_identity: str
    brand_id: str
    brand_name: str
    recipient_email: str
    drafts: list[GmailDraftRecord] = Field(default_factory=list)
