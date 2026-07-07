from __future__ import annotations

import logging
from types import TracebackType
from typing import Self

import httpx

logger = logging.getLogger(__name__)


class ApiClientError(RuntimeError):
    """Raised when an HTTP API wrapper cannot return a valid response."""


class AsyncHttpClient:
    def __init__(self, *, base_url: str | None = None, timeout_seconds: float = 30.0) -> None:
        self._client = httpx.AsyncClient(base_url=base_url or "", timeout=timeout_seconds)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def get_json(self, url: str, **kwargs: object) -> dict[str, object]:
        try:
            response = await self._client.get(url, **kwargs)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as error:
            logger.exception("HTTP GET failed for %s", url)
            raise ApiClientError(str(error)) from error
        if not isinstance(payload, dict):
            raise ApiClientError("Expected JSON object response.")
        return payload
