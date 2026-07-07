from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from creator_outreach_automation.api.openai_codex import CodexTaskClient
from creator_outreach_automation.models.creator_analysis import (
    CreatorAnalysisExtracts,
    CreatorPlatform,
    CreatorProfile,
    InstagramCreatorSnapshot,
    YouTubeCreatorSnapshot,
)

logger = logging.getLogger(__name__)


class CreatorProfileGenerationError(RuntimeError):
    """Raised when creator profile generation cannot produce valid output."""


class CreatorProfileGenerator:
    def __init__(self, codex_client: CodexTaskClient) -> None:
        self._codex_client = codex_client

    async def generate(
        self,
        *,
        snapshot: YouTubeCreatorSnapshot | InstagramCreatorSnapshot,
        extracts: CreatorAnalysisExtracts,
    ) -> CreatorProfile:
        prompt = _build_profile_prompt(snapshot=snapshot, extracts=extracts)
        response_text = await self._codex_client.run_task(
            prompt,
            system_prompt=(
                "You generate structured creator analysis. Return only valid JSON matching the "
                "requested schema. Do not include markdown fences."
            ),
        )
        try:
            payload = _parse_json_object(response_text)
            merged = _base_profile_payload(snapshot=snapshot, extracts=extracts) | payload
            return CreatorProfile.model_validate(merged)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
            logger.exception("Failed to parse CreatorProfile from Codex response")
            raise CreatorProfileGenerationError(str(error)) from error


def _build_profile_prompt(
    *,
    snapshot: YouTubeCreatorSnapshot | InstagramCreatorSnapshot,
    extracts: CreatorAnalysisExtracts,
) -> str:
    return json.dumps(
        {
            "task": "Create a creator profile for brand outreach.",
            "required_json_fields": {
                "niche": "string",
                "audience_summary": "string",
                "content_themes": ["string"],
                "previous_sponsors": ["string"],
                "collaboration_opportunities": ["string"],
                "estimated_pricing": "string",
                "raw_summary": "string",
            },
            "snapshot": snapshot.model_dump(mode="json"),
            "extracts": extracts.model_dump(mode="json"),
        },
        indent=2,
    )


def _base_profile_payload(
    *,
    snapshot: YouTubeCreatorSnapshot | InstagramCreatorSnapshot,
    extracts: CreatorAnalysisExtracts,
) -> dict[str, Any]:
    if snapshot.platform == CreatorPlatform.YOUTUBE:
        assert isinstance(snapshot, YouTubeCreatorSnapshot)
        return {
            "platform": snapshot.platform,
            "handle": snapshot.channel_id,
            "display_name": snapshot.channel_title,
            "source_url": snapshot.channel_url,
            "subscriber_count": snapshot.subscriber_count,
            "total_views": snapshot.view_count,
            "topics": extracts.topics,
            "keywords": extracts.keywords,
            "brand_mentions": extracts.brand_mentions,
            "hashtags": extracts.hashtags,
            "existing_sponsors": extracts.existing_sponsors,
            "average_engagement": extracts.average_engagement,
            "engagement_rate": extracts.engagement_rate,
        }
    assert isinstance(snapshot, InstagramCreatorSnapshot)
    return {
        "platform": snapshot.platform,
        "handle": snapshot.username,
        "display_name": snapshot.full_name,
        "source_url": f"https://www.instagram.com/{snapshot.username}/",
        "follower_count": snapshot.followers,
        "topics": extracts.topics,
        "keywords": extracts.keywords,
        "brand_mentions": extracts.brand_mentions,
        "hashtags": extracts.hashtags,
        "existing_sponsors": extracts.existing_sponsors,
        "average_engagement": extracts.average_engagement,
        "engagement_rate": extracts.engagement_rate,
    }


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    return payload
