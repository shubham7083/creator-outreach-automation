from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite

from creator_outreach_automation.database.brand_repository import normalize_domain
from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.contact import Contact, ContactSource


class ContactRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    async def initialize(self) -> None:
        from pathlib import Path

        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        async with self._database.connect() as connection:
            await connection.executescript(schema)
            await self._ensure_columns(connection)

    async def upsert_contacts(self, brand: Brand, contacts: list[Contact]) -> list[Contact]:
        if not contacts:
            return []
        now = datetime.now(UTC).isoformat()
        async with self._database.connect() as connection:
            await self._ensure_columns(connection)
            await self._ensure_brand(connection, brand, now)
            saved: list[Contact] = []
            for contact in contacts:
                saved.append(await self._upsert_contact(connection, contact, now))
        return saved

    async def _upsert_contact(
        self,
        connection: aiosqlite.Connection,
        contact: Contact,
        now: str,
    ) -> Contact:
        dedupe_key = contact_dedupe_key(contact)
        existing = await self._find_existing(connection, contact.brand_id, dedupe_key)
        contact_id = str(existing["id"]) if existing else str(contact.id)
        sources = _merge_sources(str(existing["sources_json"]) if existing else "[]", contact.sources)
        confidence = max(
            float(existing["confidence_score"]) if existing else 0.0,
            contact.confidence_score,
        )
        if existing:
            await connection.execute(
                """
                UPDATE contacts SET
                    brand_name = ?,
                    name = COALESCE(?, name),
                    title = COALESCE(?, title),
                    email = COALESCE(?, email),
                    linkedin = COALESCE(?, linkedin),
                    role = COALESCE(?, role),
                    confidence_score = ?,
                    sources_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    contact.brand_name,
                    contact.name,
                    contact.title,
                    contact.email,
                    str(contact.linkedin) if contact.linkedin else None,
                    contact.role,
                    confidence,
                    json.dumps([str(source) for source in sources]),
                    now,
                    contact_id,
                ),
            )
        else:
            await connection.execute(
                """
                INSERT INTO contacts (
                    id, brand_id, brand_name, dedupe_key, name, title, email, linkedin,
                    role, confidence_score, sources_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contact_id,
                    contact.brand_id,
                    contact.brand_name,
                    dedupe_key,
                    contact.name,
                    contact.title,
                    contact.email,
                    str(contact.linkedin) if contact.linkedin else None,
                    contact.role,
                    confidence,
                    json.dumps([str(source) for source in sources]),
                    now,
                    now,
                ),
            )
        return contact.model_copy(update={"id": contact_id, "confidence_score": confidence, "sources": sources})

    async def _find_existing(
        self,
        connection: aiosqlite.Connection,
        brand_id: str,
        dedupe_key: str,
    ) -> aiosqlite.Row | None:
        cursor = await connection.execute(
            "SELECT * FROM contacts WHERE brand_id = ? AND dedupe_key = ?",
            (brand_id, dedupe_key),
        )
        return await cursor.fetchone()

    async def _ensure_columns(self, connection: aiosqlite.Connection) -> None:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                brand_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                dedupe_key TEXT NOT NULL,
                name TEXT,
                title TEXT,
                email TEXT,
                linkedin TEXT,
                role TEXT,
                confidence_score REAL NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(brand_id, dedupe_key)
            )
            """
        )
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_contacts_brand ON contacts(brand_id)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)")

    async def _ensure_brand(self, connection: aiosqlite.Connection, brand: Brand, now: str) -> None:
        website = str(brand.website) if brand.website else None
        normalized_domain = normalize_domain(website) if website else None
        await connection.execute(
            """
            INSERT INTO brands (
                id, name, website, normalized_domain, description, industry, location,
                socials_json, discovery_sources_json, contact_email, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                website = COALESCE(excluded.website, website),
                normalized_domain = COALESCE(excluded.normalized_domain, normalized_domain),
                description = COALESCE(excluded.description, description),
                industry = COALESCE(excluded.industry, industry),
                location = COALESCE(excluded.location, location),
                contact_email = COALESCE(excluded.contact_email, contact_email),
                notes = COALESCE(excluded.notes, notes),
                updated_at = excluded.updated_at
            """,
            (
                str(brand.id),
                brand.name,
                website,
                normalized_domain,
                brand.description,
                brand.industry,
                brand.location,
                json.dumps(brand.socials),
                json.dumps(brand.discovery_sources),
                brand.contact_email,
                brand.notes,
                now,
                now,
            ),
        )


def contact_dedupe_key(contact: Contact) -> str:
    if contact.email:
        return f"email:{contact.email.strip().lower()}"
    if contact.linkedin:
        return f"linkedin:{str(contact.linkedin).strip().lower().rstrip('/')}"
    name = (contact.name or "").strip().lower()
    title = (contact.title or "").strip().lower()
    return f"name-title:{name}:{title}"


def _merge_sources(existing_json: str, new_sources: list[ContactSource]) -> list[ContactSource]:
    try:
        existing = json.loads(existing_json)
    except json.JSONDecodeError:
        existing = []
    values = [str(source) for source in existing] + [str(source) for source in new_sources]
    return [ContactSource(value) for value in dict.fromkeys(values)]
