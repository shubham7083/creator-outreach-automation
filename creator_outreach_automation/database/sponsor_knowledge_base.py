from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.models.creator_analysis import CreatorProfile
from creator_outreach_automation.models.similar_discovery import (
    SponsorKnowledgeBaseRecord,
    SponsorMentionType,
)


class SponsorKnowledgeBase:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    async def initialize(self) -> None:
        from pathlib import Path

        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        async with self._database.connect() as connection:
            await connection.executescript(schema)

    async def upsert_creator_profile(self, profile: CreatorProfile) -> str:
        identity = creator_identity(profile)
        now = datetime.now(UTC).isoformat()
        async with self._database.connect() as connection:
            await connection.execute(
                """
                INSERT INTO creator_profiles (
                    identity, platform, handle, display_name, source_url, niche, audience_summary,
                    keywords_json, topics_json, sponsors_json, brand_mentions_json,
                    follower_count, subscriber_count, average_engagement, engagement_rate, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(identity) DO UPDATE SET
                    display_name = excluded.display_name,
                    source_url = excluded.source_url,
                    niche = excluded.niche,
                    audience_summary = excluded.audience_summary,
                    keywords_json = excluded.keywords_json,
                    topics_json = excluded.topics_json,
                    sponsors_json = excluded.sponsors_json,
                    brand_mentions_json = excluded.brand_mentions_json,
                    follower_count = excluded.follower_count,
                    subscriber_count = excluded.subscriber_count,
                    average_engagement = excluded.average_engagement,
                    engagement_rate = excluded.engagement_rate,
                    updated_at = excluded.updated_at
                """,
                (
                    identity,
                    profile.platform,
                    profile.handle,
                    profile.display_name,
                    str(profile.source_url) if profile.source_url else None,
                    profile.niche,
                    profile.audience_summary,
                    json.dumps(profile.keywords),
                    json.dumps(profile.topics),
                    json.dumps(_all_sponsors(profile)),
                    json.dumps(profile.brand_mentions),
                    profile.follower_count,
                    profile.subscriber_count,
                    profile.average_engagement,
                    profile.engagement_rate,
                    now,
                ),
            )
        return identity

    async def upsert_sponsor_mentions(self, records: list[SponsorKnowledgeBaseRecord]) -> int:
        if not records:
            return 0
        now = datetime.now(UTC).isoformat()
        async with self._database.connect() as connection:
            for record in records:
                await connection.execute(
                    """
                    INSERT INTO sponsor_mentions (
                        id, sponsor_name, creator_identity, source_platform,
                        mention_type, context, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sponsor_name, creator_identity, mention_type) DO UPDATE SET
                        context = excluded.context
                    """,
                    (
                        str(uuid4()),
                        normalize_brand(record.sponsor_name),
                        record.creator_identity,
                        record.source_platform,
                        record.mention_type,
                        record.context,
                        now,
                    ),
                )
        return len(records)

    async def recurring_brands(self, *, minimum_creators: int = 2) -> list[str]:
        async with self._database.connect() as connection:
            cursor = await connection.execute(
                """
                SELECT sponsor_name, COUNT(DISTINCT creator_identity) AS creator_count
                FROM sponsor_mentions
                GROUP BY sponsor_name
                HAVING creator_count >= ?
                ORDER BY creator_count DESC, sponsor_name ASC
                """,
                (minimum_creators,),
            )
            rows = await cursor.fetchall()
        return [str(row["sponsor_name"]) for row in rows]


def creator_identity(profile: CreatorProfile) -> str:
    return f"{profile.platform}:{profile.handle.strip().lower().lstrip('@')}"


def normalize_brand(value: str) -> str:
    return " ".join(value.strip().lower().split())


def sponsor_records_from_profile(profile: CreatorProfile) -> list[SponsorKnowledgeBaseRecord]:
    identity = creator_identity(profile)
    records: list[SponsorKnowledgeBaseRecord] = []
    for sponsor in profile.existing_sponsors:
        records.append(
            SponsorKnowledgeBaseRecord(
                sponsor_name=sponsor,
                creator_identity=identity,
                source_platform=profile.platform,
                mention_type=SponsorMentionType.EXISTING_SPONSOR,
                context=profile.niche,
            )
        )
    for sponsor in profile.previous_sponsors:
        records.append(
            SponsorKnowledgeBaseRecord(
                sponsor_name=sponsor,
                creator_identity=identity,
                source_platform=profile.platform,
                mention_type=SponsorMentionType.PREVIOUS_SPONSOR,
                context=profile.niche,
            )
        )
    for brand in profile.brand_mentions:
        records.append(
            SponsorKnowledgeBaseRecord(
                sponsor_name=brand,
                creator_identity=identity,
                source_platform=profile.platform,
                mention_type=SponsorMentionType.BRAND_MENTION,
                context=profile.niche,
            )
        )
    return records


def _all_sponsors(profile: CreatorProfile) -> list[str]:
    return sorted({normalize_brand(value) for value in profile.existing_sponsors + profile.previous_sponsors})
