from __future__ import annotations

import asyncio
import logging
from collections import Counter
from typing import Protocol

from creator_outreach_automation.config import Settings, get_settings
from creator_outreach_automation.database.sponsor_knowledge_base import (
    SponsorKnowledgeBase,
    creator_identity,
    normalize_brand,
    sponsor_records_from_profile,
)
from creator_outreach_automation.models.creator_analysis import (
    CreatorAnalysisInput,
    CreatorPlatform,
    CreatorProfile,
)
from creator_outreach_automation.models.similar_discovery import (
    RankedSimilarCreator,
    SimilarCreatorCandidate,
    SimilarCreatorDiscoveryResult,
)
from creator_outreach_automation.services.creator_analysis import CreatorAnalysisService
from creator_outreach_automation.utils.cache import JsonCache

logger = logging.getLogger(__name__)


class CreatorSearchClient(Protocol):
    async def search_creators(self, query: str, *, limit: int) -> list[SimilarCreatorCandidate]:
        ...


class SimilarCreatorDiscoveryService:
    def __init__(
        self,
        *,
        google_search_client: CreatorSearchClient,
        youtube_search_client: CreatorSearchClient,
        creator_analysis_service: CreatorAnalysisService,
        sponsor_knowledge_base: SponsorKnowledgeBase,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._google_search_client = google_search_client
        self._youtube_search_client = youtube_search_client
        self._creator_analysis_service = creator_analysis_service
        self._sponsor_knowledge_base = sponsor_knowledge_base
        self._cache = JsonCache(
            self._settings.paths.cache_dir,
            namespace="similar_creator_discovery",
            ttl_seconds=self._settings.similar_discovery.cache_ttl_seconds,
        )

    async def discover(self, seed_profile: CreatorProfile) -> SimilarCreatorDiscoveryResult:
        cache_key = _cache_key(seed_profile)
        cached = await self._cache.get_model(cache_key, SimilarCreatorDiscoveryResult)
        if cached:
            logger.info("Returning cached similar creators for %s", cache_key)
            await self._sponsor_knowledge_base.initialize()
            await self._store_profile(cached.seed_profile)
            for ranked_creator in cached.ranked_creators:
                await self._store_profile(ranked_creator.profile)
            return cached

        await self._sponsor_knowledge_base.initialize()
        await self._store_profile(seed_profile)

        candidates = await self._discover_candidates(seed_profile)
        profiles = await self._analyze_candidates(candidates)
        for profile in profiles:
            await self._store_profile(profile)

        recurring_brands = _recurring_brands([seed_profile, *profiles])
        kb_recurring_brands = await self._sponsor_knowledge_base.recurring_brands()
        all_recurring_brands = sorted(set(recurring_brands) | set(kb_recurring_brands))

        ranked = [
            _rank_profile(seed_profile=seed_profile, candidate=profile, recurring_brands=all_recurring_brands)
            for profile in profiles
        ]
        ranked.sort(key=lambda item: item.score, reverse=True)

        result = SimilarCreatorDiscoveryResult(
            seed_profile=seed_profile,
            ranked_creators=ranked,
            recurring_brands=all_recurring_brands,
            analyzed_creator_count=len(profiles),
            sponsor_record_count=sum(len(sponsor_records_from_profile(profile)) for profile in profiles),
        )
        await self._cache.set_model(cache_key, result)
        logger.info("Similar creator discovery completed for %s", cache_key)
        return result

    async def _discover_candidates(self, seed_profile: CreatorProfile) -> list[SimilarCreatorCandidate]:
        queries = _build_queries(seed_profile)
        google_tasks = [
            self._safe_search(
                self._google_search_client,
                query,
                limit=self._settings.similar_discovery.google_result_limit,
            )
            for query in queries
        ]
        youtube_tasks = [
            self._safe_search(
                self._youtube_search_client,
                query,
                limit=self._settings.similar_discovery.youtube_result_limit,
            )
            for query in queries
        ]
        results = await asyncio.gather(*google_tasks, *youtube_tasks)
        discovered = [candidate for batch in results for candidate in batch]
        deduped = _dedupe_candidates(discovered)
        seed_identity = creator_identity(seed_profile)
        filtered = [candidate for candidate in deduped if candidate.identity != seed_identity]
        return filtered[: self._settings.similar_discovery.max_creators_to_analyze]

    async def _analyze_candidates(
        self,
        candidates: list[SimilarCreatorCandidate],
    ) -> list[CreatorProfile]:
        profiles: list[CreatorProfile] = []
        for candidate in candidates:
            analysis_input = _candidate_to_analysis_input(candidate)
            try:
                profile = await self._creator_analysis_service.analyze(analysis_input)
            except Exception as error:
                logger.warning("Skipping candidate %s after analysis failure: %s", candidate.identity, error)
                continue
            profiles.append(profile)
        return _dedupe_profiles(profiles)

    async def _safe_search(
        self,
        client: CreatorSearchClient,
        query: str,
        *,
        limit: int,
    ) -> list[SimilarCreatorCandidate]:
        try:
            return await client.search_creators(query, limit=limit)
        except Exception as error:
            logger.warning("Creator search failed for query=%s: %s", query, error)
            return []

    async def _store_profile(self, profile: CreatorProfile) -> None:
        await self._sponsor_knowledge_base.upsert_creator_profile(profile)
        await self._sponsor_knowledge_base.upsert_sponsor_mentions(sponsor_records_from_profile(profile))


def _build_queries(profile: CreatorProfile) -> list[str]:
    query_parts = [profile.niche, *profile.content_themes[:3], *profile.keywords[:5]]
    cleaned = [part.strip() for part in query_parts if part.strip()]
    base_terms = list(dict.fromkeys(cleaned))[:6]
    if not base_terms:
        base_terms = [profile.handle]
    queries = [f"{term} creator similar channels instagram youtube" for term in base_terms]
    for sponsor in profile.previous_sponsors[:2] + profile.existing_sponsors[:2]:
        queries.append(f"{sponsor} sponsored creator {profile.niche}")
    return list(dict.fromkeys(queries))


def _dedupe_candidates(candidates: list[SimilarCreatorCandidate]) -> list[SimilarCreatorCandidate]:
    deduped: dict[str, SimilarCreatorCandidate] = {}
    for candidate in candidates:
        if candidate.identity not in deduped:
            deduped[candidate.identity] = candidate
            continue
        existing = deduped[candidate.identity]
        deduped[candidate.identity] = existing.model_copy(
            update={
                "match_reasons": list(dict.fromkeys(existing.match_reasons + candidate.match_reasons)),
                "display_name": existing.display_name or candidate.display_name,
            }
        )
    return list(deduped.values())


def _dedupe_profiles(profiles: list[CreatorProfile]) -> list[CreatorProfile]:
    deduped: dict[str, CreatorProfile] = {}
    for profile in profiles:
        deduped.setdefault(creator_identity(profile), profile)
    return list(deduped.values())


def _candidate_to_analysis_input(candidate: SimilarCreatorCandidate) -> CreatorAnalysisInput:
    if candidate.platform == CreatorPlatform.YOUTUBE:
        return CreatorAnalysisInput(youtube_url=str(candidate.source_url))
    return CreatorAnalysisInput(instagram_username=candidate.handle)


def _rank_profile(
    *,
    seed_profile: CreatorProfile,
    candidate: CreatorProfile,
    recurring_brands: list[str],
) -> RankedSimilarCreator:
    reasons: list[str] = []
    score = 0.0

    keyword_overlap = _overlap(seed_profile.keywords, candidate.keywords)
    if keyword_overlap:
        score += min(len(keyword_overlap) * 8.0, 32.0)
        reasons.append(f"Keyword overlap: {', '.join(keyword_overlap[:5])}")

    theme_overlap = _overlap(seed_profile.content_themes + seed_profile.topics, candidate.content_themes + candidate.topics)
    if theme_overlap:
        score += min(len(theme_overlap) * 10.0, 30.0)
        reasons.append(f"Theme overlap: {', '.join(theme_overlap[:5])}")

    if _niche_similarity(seed_profile.niche, candidate.niche):
        score += 20.0
        reasons.append("Similar niche")

    sponsor_overlap = _overlap(_brands(seed_profile), _brands(candidate))
    if sponsor_overlap:
        score += min(len(sponsor_overlap) * 12.0, 24.0)
        reasons.append(f"Sponsor overlap: {', '.join(sponsor_overlap[:5])}")

    candidate_recurring = sorted(set(_brands(candidate)).intersection(set(recurring_brands)))
    if candidate_recurring:
        score += min(len(candidate_recurring) * 5.0, 15.0)
        reasons.append(f"Recurring brands: {', '.join(candidate_recurring[:5])}")

    if candidate.engagement_rate:
        score += min(candidate.engagement_rate * 100.0, 10.0)
        reasons.append("Has measurable engagement")

    return RankedSimilarCreator(
        profile=candidate,
        score=round(score, 4),
        reasons=reasons or ["Discovered from related creator search"],
        recurring_brands=candidate_recurring,
    )


def _overlap(left: list[str], right: list[str]) -> list[str]:
    left_set = {value.strip().lower() for value in left if value.strip()}
    right_set = {value.strip().lower() for value in right if value.strip()}
    return sorted(left_set.intersection(right_set))


def _niche_similarity(left: str, right: str) -> bool:
    return bool(_overlap(left.split(), right.split()))


def _brands(profile: CreatorProfile) -> list[str]:
    return [
        normalize_brand(value)
        for value in profile.existing_sponsors + profile.previous_sponsors + profile.brand_mentions
        if value.strip()
    ]


def _recurring_brands(profiles: list[CreatorProfile]) -> list[str]:
    brand_to_creators: dict[str, set[str]] = {}
    for profile in profiles:
        identity = creator_identity(profile)
        for brand in _brands(profile):
            brand_to_creators.setdefault(brand, set()).add(identity)
    counts = Counter({brand: len(creators) for brand, creators in brand_to_creators.items()})
    return [brand for brand, count in counts.most_common() if count >= 2]


def _cache_key(seed_profile: CreatorProfile) -> str:
    return f"similar:{creator_identity(seed_profile)}:{seed_profile.niche}:{','.join(seed_profile.keywords[:10])}"
