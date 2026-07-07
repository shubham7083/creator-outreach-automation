from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


class JsonCache:
    def __init__(self, cache_dir: Path, *, namespace: str, ttl_seconds: int) -> None:
        self._cache_dir = cache_dir / namespace
        self._ttl_seconds = ttl_seconds
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    async def get_model(self, key: str, model_type: type[TModel]) -> TModel | None:
        path = self._path_for_key(key)
        if not path.exists():
            return None

        try:
            payload = await asyncio.to_thread(path.read_text, encoding="utf-8")
            parsed = json.loads(payload)
            cached_at = datetime.fromisoformat(parsed["cached_at"])
            age_seconds = (datetime.now(UTC) - cached_at).total_seconds()
            if age_seconds > self._ttl_seconds:
                logger.info("Cache expired for key=%s", key)
                return None
            return model_type.model_validate(parsed["data"])
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            logger.warning("Ignoring invalid cache file %s: %s", path, error)
            return None

    async def set_model(self, key: str, model: BaseModel) -> None:
        path = self._path_for_key(key)
        payload = {
            "cached_at": datetime.now(UTC).isoformat(),
            "data": model.model_dump(mode="json"),
        }
        await asyncio.to_thread(path.write_text, json.dumps(payload, indent=2), encoding="utf-8")

    def _path_for_key(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{digest}.json"
