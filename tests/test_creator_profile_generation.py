from __future__ import annotations

import json

import pytest

from creator_outreach_automation.models.creator_analysis import (
    CreatorAnalysisExtracts,
    CreatorPlatform,
    CreatorProfile,
    YouTubeCreatorSnapshot,
)
from creator_outreach_automation.services.creator_profile_generation import CreatorProfileGenerator


class FakeCodexClient:
    async def run_task(self, prompt: str, *, system_prompt: str | None = None) -> str:
        assert "Create a creator profile" in prompt
        assert system_prompt is not None
        return json.dumps(
            {
                "niche": "Productivity tech",
                "audience_summary": "Creators and remote workers improving workflows.",
                "content_themes": ["desk setup", "workflow", "apps"],
                "previous_sponsors": ["acme gear"],
                "collaboration_opportunities": ["software demos", "desk accessories"],
                "estimated_pricing": "$1,000-$2,500 per integration",
                "raw_summary": "Strong fit for productivity brands.",
            }
        )


@pytest.mark.asyncio
async def test_creator_profile_generator_returns_structured_profile() -> None:
    generator = CreatorProfileGenerator(FakeCodexClient())  # type: ignore[arg-type]
    snapshot = YouTubeCreatorSnapshot(
        channel_id="UC123",
        channel_title="Workflow Lab",
        subscriber_count=20_000,
        view_count=1_000_000,
    )
    extracts = CreatorAnalysisExtracts(
        topics=["workflow"],
        keywords=["workflow", "apps"],
        existing_sponsors=["acme gear"],
        average_engagement=250,
        engagement_rate=0.0125,
    )

    profile = await generator.generate(snapshot=snapshot, extracts=extracts)

    assert isinstance(profile, CreatorProfile)
    assert profile.platform == CreatorPlatform.YOUTUBE
    assert profile.handle == "UC123"
    assert profile.niche == "Productivity tech"
    assert profile.previous_sponsors == ["acme gear"]
