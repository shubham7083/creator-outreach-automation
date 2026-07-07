from __future__ import annotations

from creator_outreach_automation.models.creator_analysis import (
    InstagramCreatorSnapshot,
    InstagramPost,
    YouTubeCreatorSnapshot,
    YouTubeVideo,
)
from creator_outreach_automation.services.creator_analysis_extraction import CreatorSignalExtractor


def test_youtube_extraction_collects_signals_and_engagement() -> None:
    snapshot = YouTubeCreatorSnapshot(
        channel_id="UC123",
        channel_title="Smart Home Studio",
        subscriber_count=10_000,
        view_count=500_000,
        videos=[
            YouTubeVideo(
                video_id="v1",
                title="Best desk setup with @AcmeGear #desksetup",
                description="Sponsored by Acme Gear. Productivity and creator workflow.",
                view_count=1_000,
                like_count=100,
                comment_count=20,
            ),
            YouTubeVideo(
                video_id="v2",
                title="Creator workflow apps #productivity",
                description="Partnered with Bright App for this creator workflow.",
                view_count=2_000,
                like_count=200,
                comment_count=40,
            ),
        ],
    )

    extracts = CreatorSignalExtractor(keyword_limit=10).extract_from_youtube(snapshot)

    assert "creator" in extracts.keywords
    assert "desksetup" in extracts.hashtags
    assert "acmegear" in extracts.brand_mentions
    assert "acme gear" in extracts.existing_sponsors
    assert extracts.average_engagement == 180
    assert extracts.engagement_rate == 0.018


def test_instagram_extraction_collects_hashtags_and_rate() -> None:
    snapshot = InstagramCreatorSnapshot(
        username="creator",
        bio="Fitness routines and meal prep with @FitBrand",
        followers=1_000,
        recent_posts=[
            InstagramPost(caption="Morning workout #fitness #ad", like_count=90, comment_count=10),
            InstagramPost(caption="Meal prep partnered with Fresh Box", like_count=45, comment_count=5),
        ],
    )

    extracts = CreatorSignalExtractor(keyword_limit=10).extract_from_instagram(snapshot)

    assert "fitness" in extracts.hashtags
    assert "fitbrand" in extracts.brand_mentions
    assert "fresh box" in extracts.existing_sponsors
    assert "undisclosed brand partner" in extracts.existing_sponsors
    assert extracts.average_engagement == 75
    assert extracts.engagement_rate == 0.075
