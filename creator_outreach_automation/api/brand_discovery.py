from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from creator_outreach_automation.config import GitHubSettings, GoogleSettings, HttpSettings
from creator_outreach_automation.database.brand_repository import normalize_domain
from creator_outreach_automation.models.brand_discovery import BrandCandidate, BrandDiscoverySource

logger = logging.getLogger(__name__)


class BrandDiscoveryProviderError(RuntimeError):
    """Raised when a brand discovery provider fails."""


class GoogleBrandSearchClient:
    def __init__(self, google_settings: GoogleSettings, http_settings: HttpSettings) -> None:
        self._google_settings = google_settings
        self._http_settings = http_settings

    async def search(self, query: str, *, limit: int, source: BrandDiscoverySource) -> list[BrandCandidate]:
        api_key = self._api_key()
        search_engine_id = self._search_engine_id()
        try:
            async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds) as client:
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": api_key,
                        "cx": search_engine_id,
                        "q": query,
                        "num": min(limit, 10),
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as error:
            logger.exception("Google brand search failed")
            raise BrandDiscoveryProviderError(str(error)) from error

        candidates: list[BrandCandidate] = []
        for item in payload.get("items", []):
            link = item.get("link")
            title = item.get("title")
            snippet = item.get("snippet")
            if not isinstance(link, str) or _is_non_company_url(link):
                continue
            name = _clean_name(str(title or normalize_domain(link)))
            candidates.append(
                BrandCandidate(
                    name=name,
                    website=link,
                    description=str(snippet) if isinstance(snippet, str) else None,
                    source=source,
                    source_url=link,
                    confidence=0.65,
                )
            )
        return candidates

    def _api_key(self) -> str:
        if self._google_settings.search_api_key is None:
            raise BrandDiscoveryProviderError("GOOGLE_SEARCH_API_KEY is required for brand discovery.")
        return self._google_settings.search_api_key.get_secret_value()

    def _search_engine_id(self) -> str:
        if not self._google_settings.search_engine_id:
            raise BrandDiscoveryProviderError("GOOGLE_SEARCH_ENGINE_ID is required for brand discovery.")
        return self._google_settings.search_engine_id


class QueryBrandDiscoveryProvider:
    def __init__(
        self,
        *,
        search_client: GoogleBrandSearchClient,
        source: BrandDiscoverySource,
        query_templates: list[str],
    ) -> None:
        self._search_client = search_client
        self._source = source
        self._query_templates = query_templates

    async def discover(self, niche_terms: list[str], *, limit: int) -> list[BrandCandidate]:
        candidates: list[BrandCandidate] = []
        for query in _render_queries(self._query_templates, niche_terms):
            try:
                candidates.extend(await self._search_client.search(query, limit=limit, source=self._source))
            except BrandDiscoveryProviderError as error:
                logger.warning("Brand provider %s failed for query=%s: %s", self._source, query, error)
        return candidates


class GitHubOrganizationBrandProvider:
    def __init__(self, github_settings: GitHubSettings, http_settings: HttpSettings) -> None:
        self._github_settings = github_settings
        self._http_settings = http_settings

    async def discover(self, niche_terms: list[str], *, limit: int) -> list[BrandCandidate]:
        query = " ".join(niche_terms[:5]) or "startup"
        headers = {"Accept": "application/vnd.github+json"}
        if self._github_settings.token is not None:
            headers["Authorization"] = f"Bearer {self._github_settings.token.get_secret_value()}"
        try:
            async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds, headers=headers) as client:
                response = await client.get(
                    "https://api.github.com/search/users",
                    params={"q": f"{query} type:org", "per_page": min(limit, 30)},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as error:
            logger.warning("GitHub organization search failed: %s", error)
            return []

        candidates: list[BrandCandidate] = []
        for item in payload.get("items", []):
            login = item.get("login")
            html_url = item.get("html_url")
            if not isinstance(login, str) or not isinstance(html_url, str):
                continue
            candidates.append(
                BrandCandidate(
                    name=_clean_name(login),
                    website=html_url,
                    description="GitHub organization discovered from niche search.",
                    source=BrandDiscoverySource.GITHUB_ORGANIZATION,
                    source_url=html_url,
                    socials={"github": html_url},
                    confidence=0.55,
                )
            )
        return candidates


class CompanyWebsiteEnricher:
    def __init__(self, http_settings: HttpSettings) -> None:
        self._http_settings = http_settings

    async def enrich(self, candidate: BrandCandidate) -> BrandCandidate:
        if candidate.website is None:
            return candidate
        try:
            async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(str(candidate.website))
                response.raise_for_status()
        except httpx.HTTPError:
            return candidate

        soup = BeautifulSoup(response.text, "html.parser")
        description = _meta(soup, "description") or candidate.description
        socials = {**candidate.socials, **_social_links(soup, str(response.url))}
        return candidate.model_copy(
            update={
                "description": description,
                "socials": socials,
            }
        )


def create_default_brand_providers(
    *,
    google_settings: GoogleSettings,
    github_settings: GitHubSettings,
    http_settings: HttpSettings,
) -> list[object]:
    google_client = GoogleBrandSearchClient(google_settings, http_settings)
    return [
        QueryBrandDiscoveryProvider(
            search_client=google_client,
            source=BrandDiscoverySource.PRODUCT_HUNT,
            query_templates=["site:producthunt.com/products {niche} startup"],
        ),
        QueryBrandDiscoveryProvider(
            search_client=google_client,
            source=BrandDiscoverySource.Y_COMBINATOR,
            query_templates=["site:ycombinator.com/companies {niche}"],
        ),
        QueryBrandDiscoveryProvider(
            search_client=google_client,
            source=BrandDiscoverySource.GOOGLE_SEARCH,
            query_templates=["{niche} startups brands companies sponsor creators"],
        ),
        QueryBrandDiscoveryProvider(
            search_client=google_client,
            source=BrandDiscoverySource.STARTUP_DIRECTORY,
            query_templates=[
                "site:wellfound.com/company {niche}",
                "site:betalist.com/startups {niche}",
                "site:crunchbase.com/organization {niche}",
            ],
        ),
        QueryBrandDiscoveryProvider(
            search_client=google_client,
            source=BrandDiscoverySource.AI_DIRECTORY,
            query_templates=[
                "site:futurepedia.io {niche}",
                "site:theresanaiforthat.com {niche}",
                "site:aitools.fyi {niche}",
            ],
        ),
        GitHubOrganizationBrandProvider(github_settings, http_settings),
    ]


def _render_queries(templates: list[str], niche_terms: list[str]) -> list[str]:
    niche = " ".join(niche_terms[:6]).strip() or "startup"
    return [template.format(niche=niche) for template in templates]


def _clean_name(value: str) -> str:
    cleaned = value.split("|")[0].split("-")[0].strip()
    return " ".join(cleaned.split()) or value


def _is_non_company_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return any(part in path for part in ["/blog/", "/news/", "/posts/", "/jobs/"])


def _meta(soup: BeautifulSoup, name: str) -> str | None:
    tag = soup.find("meta", attrs={"name": name})
    if tag and isinstance(tag.get("content"), str):
        return str(tag["content"]).strip()
    tag = soup.find("meta", attrs={"property": f"og:{name}"})
    if tag and isinstance(tag.get("content"), str):
        return str(tag["content"]).strip()
    return None


def _social_links(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    socials: dict[str, str] = {}
    platforms = {
        "twitter.com": "twitter",
        "x.com": "x",
        "linkedin.com": "linkedin",
        "instagram.com": "instagram",
        "youtube.com": "youtube",
        "github.com": "github",
        "tiktok.com": "tiktok",
    }
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        for domain, platform in platforms.items():
            if domain in href and platform not in socials:
                socials[platform] = href
    return socials
