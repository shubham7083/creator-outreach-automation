from __future__ import annotations

import hashlib
import json
import logging
from typing import Protocol

from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from creator_outreach_automation.api.openai_codex import CodexTaskClient
from creator_outreach_automation.config import Settings, get_settings
from creator_outreach_automation.database.brand_score_repository import BrandScoreRepository
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.brand_scoring import (
    BrandScore,
    BrandScoringInput,
    BrandScoringResult,
    ScoredBrand,
)
from creator_outreach_automation.models.creator_analysis import CreatorProfile
from creator_outreach_automation.utils.cache import JsonCache

logger = logging.getLogger(__name__)


class BrandScoringError(RuntimeError):
    """Raised when brand scoring cannot produce a valid result."""


class BrandScoreClient(Protocol):
    async def score(self, scoring_input: BrandScoringInput) -> BrandScore:
        ...


class CodexBrandScoreClient:
    def __init__(self, codex_client: CodexTaskClient, *, max_retries: int) -> None:
        self._codex_client = codex_client
        self._max_retries = max_retries

    async def score(self, scoring_input: BrandScoringInput) -> BrandScore:
        return await self._score_with_retry(scoring_input)

    async def _score_with_retry(self, scoring_input: BrandScoringInput) -> BrandScore:
        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            reraise=True,
        )
        async def run() -> BrandScore:
            response_text = await self._codex_client.run_task(
                _build_prompt(scoring_input),
                system_prompt=(
                    "You score brand collaboration fit. Return structured JSON only. "
                    "Do not include markdown, prose, code fences, comments, or extra keys."
                ),
            )
            return _parse_brand_score(response_text)

        try:
            return await run()
        except Exception as error:
            logger.exception("Brand scoring failed for brand=%s", scoring_input.brand.name)
            raise BrandScoringError(str(error)) from error


class BrandScoringEngine:
    def __init__(
        self,
        *,
        score_client: BrandScoreClient,
        score_repository: BrandScoreRepository,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._score_client = score_client
        self._score_repository = score_repository
        self._cache = JsonCache(
            self._settings.paths.cache_dir,
            namespace="brand_scores",
            ttl_seconds=self._settings.brand_scoring.cache_ttl_seconds,
        )

    async def score_brand(
        self,
        *,
        creator_profile: CreatorProfile,
        brand: Brand,
        website_summary: str,
    ) -> ScoredBrand:
        scoring_input = BrandScoringInput(
            creator_profile=creator_profile,
            brand=brand,
            website_summary=website_summary,
        )
        score = await self._cached_score(scoring_input)
        scored_brand = ScoredBrand(
            brand=brand,
            score=score,
            accepted=score.score >= self._settings.brand_scoring.min_score,
        )
        await self._score_repository.initialize()
        await self._score_repository.save_score(
            scoring_input,
            scored_brand,
            creator_identity=_creator_identity(creator_profile),
        )
        return scored_brand

    async def score_brands(
        self,
        *,
        creator_profile: CreatorProfile,
        brand_summaries: list[tuple[Brand, str]],
    ) -> BrandScoringResult:
        scored = [
            await self.score_brand(
                creator_profile=creator_profile,
                brand=brand,
                website_summary=website_summary,
            )
            for brand, website_summary in brand_summaries
        ]
        accepted = sorted(
            [item for item in scored if item.accepted],
            key=lambda item: item.score.score,
            reverse=True,
        )
        rejected = sorted(
            [item for item in scored if not item.accepted],
            key=lambda item: item.score.score,
            reverse=True,
        )
        return BrandScoringResult(
            creator_profile=creator_profile,
            ranked_brands=accepted,
            rejected_brands=rejected,
        )

    async def _cached_score(self, scoring_input: BrandScoringInput) -> BrandScore:
        cache_key = _cache_key(scoring_input)
        cached = await self._cache.get_model(cache_key, BrandScore)
        if cached:
            logger.info("Returning cached brand score for brand=%s", scoring_input.brand.name)
            return cached
        score = await self._score_client.score(scoring_input)
        await self._cache.set_model(cache_key, score)
        return score


def _build_prompt(scoring_input: BrandScoringInput) -> str:
    payload = {
        "task": "Score this brand for creator outreach fit.",
        "output_contract": {
            "score": "number from 0 to 10",
            "reason": "short explanation",
            "campaign_idea": "specific campaign concept",
            "estimated_pricing": "pricing recommendation for this collaboration",
            "email_hook": "one concise personalized outreach hook",
        },
        "rules": [
            "Return JSON only.",
            "Use no markdown.",
            "Reject weak fit by giving score below 6.",
            "Base pricing on creator size, engagement, niche fit, and brand value.",
        ],
        "creator_profile": scoring_input.creator_profile.model_dump(mode="json"),
        "brand": scoring_input.brand.model_dump(mode="json"),
        "website_summary": scoring_input.website_summary,
    }
    return json.dumps(payload, indent=2)


def _parse_brand_score(response_text: str) -> BrandScore:
    try:
        payload = _parse_json_object(response_text)
        return BrandScore.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
        raise BrandScoringError(f"Invalid structured JSON from Codex: {error}") from error


def _parse_json_object(text: str) -> dict[str, object]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object.")
    return payload


def _creator_identity(profile: CreatorProfile) -> str:
    return f"{profile.platform}:{profile.handle.strip().lower().lstrip('@')}"


def _cache_key(scoring_input: BrandScoringInput) -> str:
    summary_digest = hashlib.sha256(scoring_input.website_summary.encode("utf-8")).hexdigest()
    brand_key = str(scoring_input.brand.website or scoring_input.brand.id or scoring_input.brand.name).lower()
    return (
        f"brand-score:{_creator_identity(scoring_input.creator_profile)}:"
        f"{brand_key}:{summary_digest}"
    )
