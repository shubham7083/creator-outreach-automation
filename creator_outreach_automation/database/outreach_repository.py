from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite

from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.models.outreach import (
    GmailDraftRecord,
    OutreachGenerationInput,
    OutreachSequenceResult,
)


class OutreachRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database

    async def initialize(self) -> None:
        from pathlib import Path

        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        async with self._database.connect() as connection:
            await connection.executescript(schema)
            await self._ensure_tables(connection)

    async def save_sequence(
        self,
        generation_input: OutreachGenerationInput,
        *,
        creator_identity: str,
        drafts: list[GmailDraftRecord],
    ) -> OutreachSequenceResult:
        now = datetime.now(UTC).isoformat()
        sequence_id = str(uuid4())
        async with self._database.connect() as connection:
            await self._ensure_tables(connection)
            await connection.execute(
                """
                INSERT INTO outreach_sequences (
                    id, creator_identity, brand_id, brand_name, recipient_email,
                    campaign_idea, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sequence_id,
                    creator_identity,
                    str(generation_input.brand.id),
                    generation_input.brand.name,
                    generation_input.recipient_email,
                    generation_input.campaign_idea,
                    now,
                    now,
                ),
            )
            for draft in drafts:
                await connection.execute(
                    """
                    INSERT INTO outreach_drafts (
                        id, sequence_id, draft_kind, subject, body, gmail_draft_id, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        sequence_id,
                        draft.kind,
                        draft.subject,
                        draft.body,
                        draft.gmail_draft_id,
                        now,
                    ),
                )
        return OutreachSequenceResult(
            id=sequence_id,
            creator_identity=creator_identity,
            brand_id=str(generation_input.brand.id),
            brand_name=generation_input.brand.name,
            recipient_email=generation_input.recipient_email,
            drafts=drafts,
        )

    async def _ensure_tables(self, connection: aiosqlite.Connection) -> None:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outreach_sequences (
                id TEXT PRIMARY KEY,
                creator_identity TEXT NOT NULL,
                brand_id TEXT NOT NULL,
                brand_name TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                campaign_idea TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outreach_drafts (
                id TEXT PRIMARY KEY,
                sequence_id TEXT NOT NULL,
                draft_kind TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                gmail_draft_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(sequence_id, draft_kind)
            )
            """
        )
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_outreach_sequences_creator ON outreach_sequences(creator_identity)"
        )
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_outreach_drafts_gmail ON outreach_drafts(gmail_draft_id)"
        )
