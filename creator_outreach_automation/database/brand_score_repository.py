from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite

from creator_outreach_automation.database.brand_repository import normalize_domain
from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.models.brand_scoring import BrandScoringInput, ScoredBrand


class BrandScoreRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    async def initialize(self) -> None:
        from pathlib import Path

        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        async with self._database.connect() as connection:
            await connection.executescript(schema)
            await self._ensure_columns(connection)

    async def save_score(
        self,
        scoring_input: BrandScoringInput,
        scored_brand: ScoredBrand,
        *,
        creator_identity: str,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        async with self._database.connect() as connection:
            await self._ensure_columns(connection)
            stored_brand_id = await self._ensure_brand(connection, scoring_input, now)
            await connection.execute(
                """
                INSERT INTO brand_scores (
                    id, creator_identity, brand_id, brand_name, score, accepted, reason,
                    campaign_idea, estimated_pricing, email_hook, website_summary,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(creator_identity, brand_id) DO UPDATE SET
                    brand_name = excluded.brand_name,
                    score = excluded.score,
                    accepted = excluded.accepted,
                    reason = excluded.reason,
                    campaign_idea = excluded.campaign_idea,
                    estimated_pricing = excluded.estimated_pricing,
                    email_hook = excluded.email_hook,
                    website_summary = excluded.website_summary,
                    updated_at = excluded.updated_at
                """,
                (
                    str(uuid4()),
                    creator_identity,
                    stored_brand_id,
                    scoring_input.brand.name,
                    scored_brand.score.score,
                    int(scored_brand.accepted),
                    scored_brand.score.reason,
                    scored_brand.score.campaign_idea,
                    scored_brand.score.estimated_pricing,
                    scored_brand.score.email_hook,
                    scoring_input.website_summary,
                    now,
                    now,
                ),
            )

    async def _ensure_columns(self, connection: aiosqlite.Connection) -> None:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS brand_scores (
                id TEXT PRIMARY KEY,
                creator_identity TEXT NOT NULL,
                brand_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                score REAL NOT NULL,
                accepted INTEGER NOT NULL,
                reason TEXT NOT NULL,
                campaign_idea TEXT NOT NULL,
                estimated_pricing TEXT NOT NULL,
                email_hook TEXT NOT NULL,
                website_summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(creator_identity, brand_id)
            )
            """
        )
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_brand_scores_creator ON brand_scores(creator_identity)"
        )
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_brand_scores_score ON brand_scores(score)")

    async def _ensure_brand(
        self,
        connection: aiosqlite.Connection,
        scoring_input: BrandScoringInput,
        now: str,
    ) -> str:
        website = str(scoring_input.brand.website) if scoring_input.brand.website else None
        normalized_domain = normalize_domain(website) if website else None
        existing_id = await self._find_brand_id(
            connection,
            brand_id=str(scoring_input.brand.id),
            normalized_domain=normalized_domain,
        )
        stored_brand_id = existing_id or str(scoring_input.brand.id)
        if existing_id:
            await connection.execute(
                """
                UPDATE brands SET
                    name = ?,
                    website = COALESCE(?, website),
                    normalized_domain = COALESCE(?, normalized_domain),
                    description = COALESCE(?, description),
                    industry = COALESCE(?, industry),
                    location = COALESCE(?, location),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    scoring_input.brand.name,
                    website,
                    normalized_domain,
                    scoring_input.brand.description,
                    scoring_input.brand.industry,
                    scoring_input.brand.location,
                    now,
                    stored_brand_id,
                ),
            )
            return stored_brand_id

        await connection.execute(
            """
            INSERT INTO brands (
                id, name, website, normalized_domain, description, industry, location,
                socials_json, discovery_sources_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, '{}', '[]', ?, ?)
            """,
            (
                stored_brand_id,
                scoring_input.brand.name,
                website,
                normalized_domain,
                scoring_input.brand.description,
                scoring_input.brand.industry,
                scoring_input.brand.location,
                now,
                now,
            ),
        )
        return stored_brand_id

    async def _find_brand_id(
        self,
        connection: aiosqlite.Connection,
        *,
        brand_id: str,
        normalized_domain: str | None,
    ) -> str | None:
        cursor = await connection.execute("SELECT id FROM brands WHERE id = ?", (brand_id,))
        row = await cursor.fetchone()
        if row:
            return str(row["id"])
        if normalized_domain:
            cursor = await connection.execute(
                "SELECT id FROM brands WHERE normalized_domain = ?",
                (normalized_domain,),
            )
            row = await cursor.fetchone()
            if row:
                return str(row["id"])
        return None
