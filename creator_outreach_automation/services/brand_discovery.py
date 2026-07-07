from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from creator_outreach_automation.config import Settings, get_settings
from creator_outreach_automation.database.brand_repository import BrandRepository, normalize_domain
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.brand_discovery import BrandCandidate, BrandDiscoveryResult
from creator_outreach_automation.models.creator_analysis import CreatorProfile
from creator_outreach_automation.utils.cache import JsonCache

logger = logging.getLogger(__name__)


class BrandDiscoveryProvider(Protocol):
    async def discover(self, niche_terms: list[str], *, limit: int) -> list[BrandCandidate]:
        ...


class BrandCandidateEnricher(Protocol):
    async def enrich(self, candidate: BrandCandidate) -> BrandCandidate:
        ...


class BrandDiscoveryEngine:
    def __init__(
        self,
        *,
        providers: list[BrandDiscoveryProvider],
        brand_repository: BrandRepository,
        website_enricher: BrandCandidateEnricher | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._providers = providers
        self._brand_repository = brand_repository
        self._website_enricher = website_enricher
        self._cache = JsonCache(
            self._settings.paths.cache_dir,
            namespace="brand_discovery",
            ttl_seconds=self._settings.brand_discovery.cache_ttl_seconds,
        )

    async def discover(self, creator_profile: CreatorProfile) -> list[Brand]:
        creator_identity = _creator_identity(creator_profile)
        cache_key = _cache_key(creator_profile)
        cached = await self._cache.get_model(cache_key, BrandDiscoveryResult)
        if cached:
            logger.info("Returning cached brand discovery for %s", creator_identity)
            await self._brand_repository.initialize()
            await self._brand_repository.upsert_candidates(
                [_brand_to_candidate(brand) for brand in cached.brands],
                creator_identity=creator_identity,
            )
            return cached.brands

        niche_terms = _niche_terms(creator_profile)
        candidates = await self._discover_candidates(niche_terms)
        deduped = _dedupe_candidates(candidates)
        enriched = await self._enrich_candidates(deduped[: self._settings.brand_discovery.max_brands])

        await self._brand_repository.initialize()
        brands = await self._brand_repository.upsert_candidates(
            enriched,
            creator_identity=creator_identity,
        )
        result = BrandDiscoveryResult(creator_identity=creator_identity, brands=brands)
        await self._cache.set_model(cache_key, result)
        logger.info("Brand discovery completed for %s with %s brands", creator_identity, len(brands))
        return brands

    async def _discover_candidates(self, niche_terms: list[str]) -> list[BrandCandidate]:
        tasks = [
            self._safe_discover(provider, niche_terms)
            for provider in self._providers
        ]
        batches = await asyncio.gather(*tasks)
        return [candidate for batch in batches for candidate in batch]

    async def _safe_discover(
        self,
        provider: BrandDiscoveryProvider,
        niche_terms: list[str],
    ) -> list[BrandCandidate]:
        try:
            return await provider.discover(
                niche_terms,
                limit=self._settings.brand_discovery.results_per_source,
            )
        except Exception as error:
            logger.warning("Brand discovery provider failed: %s", error)
            return []

    async def _enrich_candidates(self, candidates: list[BrandCandidate]) -> list[BrandCandidate]:
        if self._website_enricher is None:
            return candidates
        tasks = [self._safe_enrich(candidate) for candidate in candidates]
        return await asyncio.gather(*tasks)

    async def _safe_enrich(self, candidate: BrandCandidate) -> BrandCandidate:
        if self._website_enricher is None:
            return candidate
        try:
            return await self._website_enricher.enrich(candidate)
        except Exception as error:
            logger.debug("Brand enrichment failed for %s: %s", candidate.name, error)
            return candidate


def _niche_terms(profile: CreatorProfile) -> list[str]:
    terms = [
        profile.niche,
        *profile.content_themes,
        *profile.topics,
        *profile.keywords,
    ]
    cleaned = [term.strip().lower() for term in terms if term.strip()]
    return list(dict.fromkeys(cleaned))[:12]


def _dedupe_candidates(candidates: list[BrandCandidate]) -> list[BrandCandidate]:
    deduped: dict[str, BrandCandidate] = {}
    for candidate in sorted(candidates, key=lambda item: item.confidence, reverse=True):
        key = _candidate_key(candidate)
        if key not in deduped:
            deduped[key] = candidate
            continue
        existing = deduped[key]
        deduped[key] = existing.model_copy(
            update={
                "description": existing.description or candidate.description,
                "industry": existing.industry or candidate.industry,
                "location": existing.location or candidate.location,
                "socials": {**candidate.socials, **existing.socials},
                "confidence": max(existing.confidence, candidate.confidence),
            }
        )
    return list(deduped.values())


def _candidate_key(candidate: BrandCandidate) -> str:
    if candidate.website:
        return normalize_domain(str(candidate.website))
    return "name:" + " ".join(candidate.name.lower().split())


def _creator_identity(profile: CreatorProfile) -> str:
    return f"{profile.platform}:{profile.handle.strip().lower().lstrip('@')}"


def _cache_key(profile: CreatorProfile) -> str:
    return f"brand:{_creator_identity(profile)}:{profile.niche}:{','.join(profile.keywords[:10])}"


def _brand_to_candidate(brand: Brand) -> BrandCandidate:
    from creator_outreach_automation.models.brand_discovery import BrandDiscoverySource

    return BrandCandidate(
        name=brand.name,
        website=brand.website,
        description=brand.description,
        industry=brand.industry,
        location=brand.location,
        socials=brand.socials,
        source=BrandDiscoverySource.COMPANY_WEBSITE,
        confidence=1.0,
    )
