from __future__ import annotations

from creator_outreach_automation.api.google_search import candidate_from_url
from creator_outreach_automation.models.creator_analysis import CreatorPlatform
from creator_outreach_automation.models.similar_discovery import DiscoverySource


def test_candidate_from_url_parses_youtube_channel() -> None:
    candidate = candidate_from_url(
        "https://www.youtube.com/channel/UC123",
        discovery_source=DiscoverySource.GOOGLE,
    )

    assert candidate is not None
    assert candidate.platform == CreatorPlatform.YOUTUBE
    assert candidate.handle == "UC123"


def test_candidate_from_url_parses_instagram_profile() -> None:
    candidate = candidate_from_url(
        "https://www.instagram.com/example_creator/",
        discovery_source=DiscoverySource.GOOGLE,
    )

    assert candidate is not None
    assert candidate.platform == CreatorPlatform.INSTAGRAM
    assert candidate.handle == "example_creator"
