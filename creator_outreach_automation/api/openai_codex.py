from __future__ import annotations

import logging

from creator_outreach_automation.config import OpenAISettings

logger = logging.getLogger(__name__)


class CodexTaskError(RuntimeError):
    """Raised when an OpenAI task cannot complete."""


class CodexTaskClient:
    def __init__(self, settings: OpenAISettings) -> None:
        self._settings = settings

    async def run_task(self, prompt: str, *, system_prompt: str | None = None) -> str:
        logger.info("Preparing AI task using model=%s", self._settings.model)
        if self._settings.api_key is None:
            raise CodexTaskError("OPENAI_API_KEY is required for Codex creator analysis tasks.")

        try:
            from openai import AsyncOpenAI
        except ImportError as error:
            raise CodexTaskError("The openai package is required for Codex tasks.") from error

        client = AsyncOpenAI(api_key=self._settings.api_key.get_secret_value())
        try:
            response = await client.responses.create(
                model=self._settings.model,
                instructions=system_prompt,
                input=prompt,
            )
        except Exception as error:
            logger.exception("Codex task failed")
            raise CodexTaskError(str(error)) from error

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise CodexTaskError("Codex task returned an empty response.")
        return output_text
