from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite

from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.brand_discovery import BrandCandidate


class BrandRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    async def initialize(self) -> None:
        from pathlib import Path

        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        async with self._database.connect() as connection:
            await connection.executescript(schema)
            await self._ensure_brand_columns(connection)

    async def upsert_candidates(
        self,
        candidates: list[BrandCandidate],
        *,
        creator_identity: str,
    ) -> list[Brand]:
        brands: list[Brand] = []
        async with self._database.connect() as connection:
            await self._ensure_brand_columns(connection)
            for candidate in candidates:
                brand = await self._upsert_candidate(
                    connection,
                    candidate,
                    creator_identity=creator_identity,
                )
                brands.append(brand)
        return brands

    async def _upsert_candidate(
        self,
        connection: aiosqlite.Connection,
        candidate: BrandCandidate,
        *,
        creator_identity: str,
    ) -> Brand:
        now = datetime.now(UTC).isoformat()
        normalized_domain = normalize_domain(str(candidate.website)) if candidate.website else None
        existing = await self._find_existing(connection, candidate, normalized_domain)
        brand_id = str(existing["id"]) if existing else str(uuid4())
        discovery_sources = _merge_json_list(
            str(existing["discovery_sources_json"]) if existing else "[]",
            candidate.source,
        )
        socials = _merge_json_dict(str(existing["socials_json"]) if existing else "{}", candidate.socials)

        if existing:
            await connection.execute(
                """
                UPDATE brands SET
                    name = COALESCE(?, name),
                    website = COALESCE(?, website),
                    normalized_domain = COALESCE(?, normalized_domain),
                    description = COALESCE(?, description),
                    industry = COALESCE(?, industry),
                    location = COALESCE(?, location),
                    socials_json = ?,
                    discovery_sources_json = ?,
                    discovered_for_creator_identity = COALESCE(discovered_for_creator_identity, ?),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    candidate.name,
                    str(candidate.website) if candidate.website else None,
                    normalized_domain,
                    candidate.description,
                    candidate.industry,
                    candidate.location,
                    json.dumps(socials),
                    json.dumps(discovery_sources),
                    creator_identity,
                    now,
                    brand_id,
                ),
            )
        else:
            await connection.execute(
                """
                INSERT INTO brands (
                    id, name, website, normalized_domain, description, industry, location,
                    socials_json, discovery_sources_json, discovered_for_creator_identity,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brand_id,
                    candidate.name,
                    str(candidate.website) if candidate.website else None,
                    normalized_domain,
                    candidate.description,
                    candidate.industry,
                    candidate.location,
                    json.dumps(socials),
                    json.dumps(discovery_sources),
                    creator_identity,
                    now,
                    now,
                ),
            )

        await connection.execute(
            """
            INSERT INTO brand_discovery_sources (
                id, brand_id, source, source_url, creator_identity, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(brand_id, source, creator_identity) DO UPDATE SET
                confidence = MAX(confidence, excluded.confidence),
                source_url = COALESCE(excluded.source_url, source_url)
            """,
            (
                str(uuid4()),
                brand_id,
                candidate.source,
                str(candidate.source_url) if candidate.source_url else None,
                creator_identity,
                candidate.confidence,
                now,
            ),
        )
        return Brand(
            id=brand_id,
            name=candidate.name,
            website=candidate.website,
            description=candidate.description or (str(existing["description"]) if existing and existing["description"] else None),
            industry=candidate.industry or (str(existing["industry"]) if existing and existing["industry"] else None),
            location=candidate.location or (str(existing["location"]) if existing and existing["location"] else None),
            socials=socials,
            discovery_sources=discovery_sources,
            updated_at=datetime.fromisoformat(now),
        )

    async def _find_existing(
        self,
        connection: aiosqlite.Connection,
        candidate: BrandCandidate,
        normalized_domain: str | None,
    ) -> aiosqlite.Row | None:
        if normalized_domain:
            cursor = await connection.execute(
                "SELECT * FROM brands WHERE normalized_domain = ?",
                (normalized_domain,),
            )
            row = await cursor.fetchone()
            if row:
                return row
        cursor = await connection.execute(
            "SELECT * FROM brands WHERE lower(name) = lower(?) AND normalized_domain IS NULL",
            (candidate.name,),
        )
        return await cursor.fetchone()

    async def _ensure_brand_columns(self, connection: aiosqlite.Connection) -> None:
        cursor = await connection.execute("PRAGMA table_info(brands)")
        columns = {str(row["name"]) for row in await cursor.fetchall()}
        additions = {
            "normalized_domain": "ALTER TABLE brands ADD COLUMN normalized_domain TEXT",
            "description": "ALTER TABLE brands ADD COLUMN description TEXT",
            "location": "ALTER TABLE brands ADD COLUMN location TEXT",
            "socials_json": "ALTER TABLE brands ADD COLUMN socials_json TEXT NOT NULL DEFAULT '{}'",
            "discovery_sources_json": "ALTER TABLE brands ADD COLUMN discovery_sources_json TEXT NOT NULL DEFAULT '[]'",
            "discovered_for_creator_identity": "ALTER TABLE brands ADD COLUMN discovered_for_creator_identity TEXT",
        }
        for column, statement in additions.items():
            if column not in columns:
                await connection.execute(statement)
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_brands_domain ON brands(normalized_domain)")


def normalize_domain(url: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    hostname = parsed.netloc or parsed.path
    hostname = hostname.lower().removeprefix("www.")
    return hostname.split("/")[0]


def _merge_json_list(existing_json: str, value: str) -> list[str]:
    try:
        existing = json.loads(existing_json)
    except json.JSONDecodeError:
        existing = []
    values = [str(item) for item in existing if str(item).strip()]
    values.append(str(value))
    return list(dict.fromkeys(values))


def _merge_json_dict(existing_json: str, values: dict[str, str]) -> dict[str, str]:
    try:
        existing = json.loads(existing_json)
    except json.JSONDecodeError:
        existing = {}
    if not isinstance(existing, dict):
        existing = {}
    return {**{str(key): str(value) for key, value in existing.items()}, **values}
