from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Iterable

from creator_outreach_automation.models.creator_analysis import (
    CreatorAnalysisExtracts,
    InstagramCreatorSnapshot,
    YouTubeCreatorSnapshot,
)

logger = logging.getLogger(__name__)

HASHTAG_PATTERN = re.compile(r"(?<!\w)#([A-Za-z0-9_]{2,64})")
MENTION_PATTERN = re.compile(r"(?<!\w)@([A-Za-z0-9_.]{2,64})")
SPONSOR_PATTERN = re.compile(
    r"\b(?:sponsored\s+by|partner(?:ed|ship)?\s+with|in\s+collaboration\s+with|thanks\s+to)\s+([^.\n,!?:;#@]{2,80})",
    re.IGNORECASE,
)
TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9'-]{2,}")

STOP_WORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "also",
        "and",
        "are",
        "because",
        "been",
        "but",
        "can",
        "for",
        "from",
        "get",
        "has",
        "have",
        "how",
        "into",
        "like",
        "more",
        "new",
        "not",
        "our",
        "out",
        "the",
        "this",
        "that",
        "their",
        "they",
        "with",
        "you",
        "your",
    }
)


class CreatorSignalExtractor:
    def __init__(self, *, keyword_limit: int) -> None:
        self._keyword_limit = keyword_limit

    def extract_from_youtube(self, snapshot: YouTubeCreatorSnapshot) -> CreatorAnalysisExtracts:
        texts = [snapshot.channel_title]
        texts.extend(video.title for video in snapshot.videos)
        texts.extend(video.description for video in snapshot.videos)
        combined_text = "\n".join(texts)

        video_engagements = [
            sum(value or 0 for value in (video.like_count, video.comment_count))
            for video in snapshot.videos
            if video.like_count is not None or video.comment_count is not None
        ]
        average_engagement = _average(video_engagements)
        engagement_rate = None
        if average_engagement is not None and snapshot.subscriber_count:
            engagement_rate = average_engagement / snapshot.subscriber_count

        return CreatorAnalysisExtracts(
            topics=self._topics(combined_text),
            keywords=self._keywords(combined_text),
            brand_mentions=self._brand_mentions(combined_text),
            hashtags=self._hashtags(combined_text),
            existing_sponsors=self._sponsors(combined_text),
            average_engagement=average_engagement,
            engagement_rate=engagement_rate,
        )

    def extract_from_instagram(self, snapshot: InstagramCreatorSnapshot) -> CreatorAnalysisExtracts:
        texts = [snapshot.bio]
        texts.extend(post.caption for post in snapshot.recent_posts)
        combined_text = "\n".join(texts)

        post_engagements = [
            sum(value or 0 for value in (post.like_count, post.comment_count))
            for post in snapshot.recent_posts
            if post.like_count is not None or post.comment_count is not None
        ]
        average_engagement = _average(post_engagements)
        engagement_rate = None
        if average_engagement is not None and snapshot.followers:
            engagement_rate = average_engagement / snapshot.followers

        hashtags = set(self._hashtags(combined_text))
        for post in snapshot.recent_posts:
            hashtags.update(tag.lower().lstrip("#") for tag in post.hashtags)

        return CreatorAnalysisExtracts(
            topics=self._topics(combined_text),
            keywords=self._keywords(combined_text),
            brand_mentions=self._brand_mentions(combined_text, excluded_mentions={snapshot.username}),
            hashtags=sorted(hashtags),
            existing_sponsors=self._sponsors(combined_text),
            average_engagement=average_engagement,
            engagement_rate=engagement_rate,
        )

    def _keywords(self, text: str) -> list[str]:
        tokens = [
            token.lower().strip("'")
            for token in TOKEN_PATTERN.findall(text)
            if token.lower() not in STOP_WORDS
        ]
        return [word for word, _count in Counter(tokens).most_common(self._keyword_limit)]

    def _topics(self, text: str) -> list[str]:
        keywords = self._keywords(text)
        return keywords[: min(10, len(keywords))]

    def _hashtags(self, text: str) -> list[str]:
        return sorted({match.lower() for match in HASHTAG_PATTERN.findall(text)})

    def _brand_mentions(self, text: str, *, excluded_mentions: set[str] | None = None) -> list[str]:
        excluded = {value.lower().lstrip("@") for value in excluded_mentions or set()}
        mentions = {
            match.lower()
            for match in MENTION_PATTERN.findall(text)
            if match.lower().lstrip("@") not in excluded
        }
        sponsors = {sponsor.lower() for sponsor in self._sponsors(text)}
        return sorted(mentions | sponsors)

    def _sponsors(self, text: str) -> list[str]:
        sponsors = {_clean_sponsor(match) for match in SPONSOR_PATTERN.findall(text)}
        sponsor_tags = {"ad", "sponsored", "paidpartnership", "partner"}
        if sponsor_tags.intersection(set(self._hashtags(text))):
            sponsors.add("undisclosed brand partner")
        return sorted(sponsor for sponsor in sponsors if sponsor)


def _average(values: Iterable[int]) -> float | None:
    value_list = list(values)
    if not value_list:
        return None
    return sum(value_list) / len(value_list)


def _clean_sponsor(value: str) -> str:
    cleaned = value.strip(" .,!?:;-\n\t")
    cleaned = re.split(
        r"\s+\b(?:for|on|to|this|that|today|because|where|when|while)\b\s+",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return cleaned.strip(" .,!?:;-\n\t").lower()
