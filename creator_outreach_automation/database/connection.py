from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


class SQLiteDatabase:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = await aiosqlite.connect(self._database_path)
        connection.row_factory = aiosqlite.Row
        try:
            await connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            await connection.commit()
        except Exception:
            await connection.rollback()
            raise
        finally:
            await connection.close()
