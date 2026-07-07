from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from creator_outreach_automation.config import get_settings
from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.logging.setup import configure_logging

logger = logging.getLogger(__name__)


async def run_migrations() -> None:
    settings = get_settings()
    configure_logging(settings.logging)
    schema_path = Path(__file__).with_name("schema.sql")
    schema = schema_path.read_text(encoding="utf-8")

    database = SQLiteDatabase(settings.database.sqlite_path)
    async with database.connect() as connection:
        await connection.executescript(schema)

    logger.info("Database migrations applied to %s", settings.database.sqlite_path)


def main() -> None:
    asyncio.run(run_migrations())


if __name__ == "__main__":
    main()
