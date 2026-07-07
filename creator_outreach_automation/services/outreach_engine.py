from __future__ import annotations

import hashlib
import json
import logging
from typing import Protocol

from pydantic import ValidationError

from creator_outreach_automation.api.gmail import GmailDraftClient, GmailDraftRequest
from creator_outreach_automation.api.openai_codex import CodexTaskClient
from creator_outreach_automation.config import Settings, get_settings
from creator_outreach_automation.database.outreach_repository import OutreachRepository
from creator_outreach_automation.models.outreach import (
    GmailDraftRecord,
    OutreachDraftContent,
    OutreachDraftKind,
    OutreachGenerationInput,
    OutreachSequenceContent,
    OutreachSequenceResult,
)
from creator_outreach_automation.utils.cache import JsonCache

logger = logging.getLogger(__name__)


class OutreachGenerationError(RuntimeError):
    """Raised when outreach generation cannot produce valid copy."""


class OutreachContentGenerator(Protocol):
    async def generate(self, generation_input: OutreachGenerationInput) -> OutreachSequenceContent:
        ...


class CodexOutreachContentGenerator:
    def __init__(self, codex_client: CodexTaskClient, *, max_words: int) -> None:
        self._codex_client = codex_client
        self._max_words = max_words

    async def generate(self, generation_input: OutreachGenerationInput) -> OutreachSequenceContent:
        response_text = await self._codex_client.run_task(
            _build_prompt(generation_input, max_words=self._max_words),
            system_prompt=(
                "You write professional creator outreach. Return structured JSON only. "
                "No markdown, no prose outside JSON, no auto-send language."
            ),
        )
        return _parse_sequence(response_text, max_words=self._max_words)


class OutreachEngine:
    def __init__(
        self,
        *,
        content_generator: OutreachContentGenerator,
        gmail_client: GmailDraftClient,
        outreach_repository: OutreachRepository,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._content_generator = content_generator
        self._gmail_client = gmail_client
        self._outreach_repository = outreach_repository
        self._cache = JsonCache(
            self._settings.paths.cache_dir,
            namespace="outreach_sequences",
            ttl_seconds=self._settings.outreach.cache_ttl_seconds,
        )

    async def create_drafts(self, generation_input: OutreachGenerationInput) -> OutreachSequenceResult:
        sequence = await self._cached_sequence(generation_input)
        draft_contents = _sequence_to_drafts(sequence, max_words=self._settings.outreach.max_words)
        gmail_records: list[GmailDraftRecord] = []
        for draft in draft_contents:
            response = await self._gmail_client.create_draft(
                GmailDraftRequest(
                    to_email=generation_input.recipient_email,
                    subject=draft.subject,
                    body=draft.body,
                )
            )
            gmail_records.append(
                GmailDraftRecord(
                    kind=draft.kind,
                    subject=draft.subject,
                    body=draft.body,
                    gmail_draft_id=response.draft_id,
                )
            )

        await self._outreach_repository.initialize()
        return await self._outreach_repository.save_sequence(
            generation_input,
            creator_identity=_creator_identity(generation_input),
            drafts=gmail_records,
        )

    async def _cached_sequence(self, generation_input: OutreachGenerationInput) -> OutreachSequenceContent:
        cache_key = _cache_key(generation_input)
        cached = await self._cache.get_model(cache_key, OutreachSequenceContent)
        if cached:
            logger.info("Returning cached outreach copy for brand=%s", generation_input.brand.name)
            return cached
        sequence = await self._content_generator.generate(generation_input)
        _validate_sequence(sequence, max_words=self._settings.outreach.max_words)
        await self._cache.set_model(cache_key, sequence)
        return sequence


def _build_prompt(generation_input: OutreachGenerationInput, *, max_words: int) -> str:
    payload = {
        "task": "Generate creator outreach drafts for a brand collaboration.",
        "output_contract": {
            "subject": "one natural email subject",
            "email": f"initial email body under {max_words} words",
            "follow_up": f"follow-up email body under {max_words} words",
            "final_follow_up": f"final follow-up body under {max_words} words",
        },
        "rules": [
            "Represent the creator professionally.",
            "Write naturally and avoid hype.",
            "Do not imply the email has been sent.",
            "Create drafts only.",
            f"Each body must be under {max_words} words.",
        ],
        "creator_profile": generation_input.creator_profile.model_dump(mode="json"),
        "brand": generation_input.brand.model_dump(mode="json"),
        "campaign_idea": generation_input.campaign_idea,
        "recipient": {
            "name": generation_input.recipient_name,
            "title": generation_input.recipient_title,
            "email": generation_input.recipient_email,
        },
    }
    return json.dumps(payload, indent=2)


def _parse_sequence(response_text: str, *, max_words: int) -> OutreachSequenceContent:
    try:
        payload = _parse_json_object(response_text)
        sequence = OutreachSequenceContent.model_validate(payload)
        _validate_sequence(sequence, max_words=max_words)
        return sequence
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
        raise OutreachGenerationError(f"Invalid outreach JSON: {error}") from error


def _parse_json_object(text: str) -> dict[str, object]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object.")
    return payload


def _sequence_to_drafts(sequence: OutreachSequenceContent, *, max_words: int) -> list[OutreachDraftContent]:
    drafts = [
        OutreachDraftContent(kind=OutreachDraftKind.INITIAL, subject=sequence.subject, body=sequence.email),
        OutreachDraftContent(
            kind=OutreachDraftKind.FOLLOW_UP,
            subject=f"Following up: {sequence.subject}",
            body=sequence.follow_up,
        ),
        OutreachDraftContent(
            kind=OutreachDraftKind.FINAL_FOLLOW_UP,
            subject=f"Final follow-up: {sequence.subject}",
            body=sequence.final_follow_up,
        ),
    ]
    for draft in drafts:
        _validate_body(draft.body, max_words=max_words)
    return drafts


def _validate_sequence(sequence: OutreachSequenceContent, *, max_words: int) -> None:
    for body in [sequence.email, sequence.follow_up, sequence.final_follow_up]:
        _validate_body(body, max_words=max_words)


def _validate_body(body: str, *, max_words: int) -> None:
    if len(body.split()) > max_words:
        raise OutreachGenerationError(f"Outreach body exceeds {max_words} words.")


def _creator_identity(generation_input: OutreachGenerationInput) -> str:
    profile = generation_input.creator_profile
    return f"{profile.platform}:{profile.handle.strip().lower().lstrip('@')}"


def _cache_key(generation_input: OutreachGenerationInput) -> str:
    payload = {
        "creator": _creator_identity(generation_input),
        "brand": str(generation_input.brand.website or generation_input.brand.id or generation_input.brand.name),
        "campaign_idea": generation_input.campaign_idea,
        "recipient_title": generation_input.recipient_title,
    }
    return "outreach:" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
