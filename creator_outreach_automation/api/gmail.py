from __future__ import annotations

import logging
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from email.message import EmailMessage

import asyncio

from creator_outreach_automation.config import GoogleSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GmailDraftRequest:
    to_email: str
    subject: str
    body: str


@dataclass(frozen=True, slots=True)
class GmailDraftResponse:
    draft_id: str


class GmailDraftError(RuntimeError):
    """Raised when Gmail draft creation fails."""


class GmailDraftClient:
    def __init__(self, settings: GoogleSettings) -> None:
        self._settings = settings

    async def create_draft(self, request: GmailDraftRequest) -> GmailDraftResponse:
        logger.info("Creating Gmail draft for recipient=%s", request.to_email)
        return await asyncio.to_thread(self._create_draft_sync, request)

    def _create_draft_sync(self, request: GmailDraftRequest) -> GmailDraftResponse:
        if (
            self._settings.client_id is None
            or self._settings.client_secret is None
            or self._settings.refresh_token is None
            or not self._settings.gmail_sender_email
        ):
            raise GmailDraftError(
                "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN, "
                "and GMAIL_SENDER_EMAIL are required to create Gmail drafts."
            )

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as error:
            raise GmailDraftError("Google API packages are required for Gmail drafts.") from error

        credentials = Credentials(
            token=None,
            refresh_token=self._settings.refresh_token.get_secret_value(),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._settings.client_id.get_secret_value(),
            client_secret=self._settings.client_secret.get_secret_value(),
            scopes=["https://www.googleapis.com/auth/gmail.compose"],
        )
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        message = EmailMessage()
        message["To"] = request.to_email
        message["From"] = self._settings.gmail_sender_email
        message["Subject"] = request.subject
        message.set_content(request.body)
        encoded = urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        try:
            draft = (
                service.users()
                .drafts()
                .create(userId="me", body={"message": {"raw": encoded}})
                .execute()
            )
        except Exception as error:
            logger.exception("Gmail draft creation failed")
            raise GmailDraftError(str(error)) from error

        draft_id = draft.get("id")
        if not isinstance(draft_id, str) or not draft_id:
            raise GmailDraftError("Gmail API did not return a draft id.")
        return GmailDraftResponse(draft_id=draft_id)
