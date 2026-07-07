from __future__ import annotations

import logging

from creator_outreach_automation.api.gmail import GmailDraftClient, GmailDraftRequest, GmailDraftResponse
from creator_outreach_automation.models.outreach import OutreachMessage

logger = logging.getLogger(__name__)


class GmailDraftService:
    def __init__(self, client: GmailDraftClient) -> None:
        self._client = client

    async def create_draft(self, message: OutreachMessage, recipient_email: str) -> GmailDraftResponse:
        logger.info("Preparing Gmail draft for outreach_message_id=%s", message.id)
        return await self._client.create_draft(
            GmailDraftRequest(
                to_email=recipient_email,
                subject=message.subject,
                body=message.body,
            )
        )
