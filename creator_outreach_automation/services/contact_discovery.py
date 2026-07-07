from __future__ import annotations

import logging
import re
from typing import Protocol

import httpx
from bs4 import BeautifulSoup

from creator_outreach_automation.api.apollo import ApolloClient
from creator_outreach_automation.config import GoogleSettings, HttpSettings, Settings, get_settings
from creator_outreach_automation.database.contact_repository import ContactRepository
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.contact import Contact, ContactRole, ContactSource

logger = logging.getLogger(__name__)

ROLE_KEYWORDS: dict[ContactRole, tuple[str, ...]] = {
    ContactRole.MARKETING: ("marketing", "demand generation", "brand"),
    ContactRole.GROWTH: ("growth", "revenue", "acquisition"),
    ContactRole.PARTNERSHIPS: ("partnership", "business development", "alliances"),
    ContactRole.CREATOR_MANAGER: ("creator", "creator partnerships", "creator manager"),
    ContactRole.INFLUENCER_MANAGER: ("influencer", "influencer marketing", "social media"),
}
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


class ContactProvider(Protocol):
    async def discover(self, brand: Brand) -> list[Contact]:
        ...


class ApolloContactProvider:
    def __init__(self, client: ApolloClient) -> None:
        self._client = client

    async def discover(self, brand: Brand) -> list[Contact]:
        domain = _brand_domain(brand)
        if not domain:
            return []
        payload = await self._client.enrich_contact(domain)
        contacts: list[Contact] = []
        for person in payload.get("people", []) or payload.get("contacts", []):
            if not isinstance(person, dict):
                continue
            title = _optional_str(person.get("title"))
            role = infer_role(title or "")
            if role is None:
                continue
            contacts.append(
                Contact(
                    brand_id=str(brand.id),
                    brand_name=brand.name,
                    name=_optional_str(person.get("name")),
                    title=title,
                    email=_optional_str(person.get("email")),
                    linkedin=_optional_str(person.get("linkedin_url")),
                    role=role,
                    confidence_score=0.9 if person.get("email") else 0.78,
                    sources=[ContactSource.APOLLO],
                )
            )
        return contacts


class WebsiteContactProvider:
    def __init__(self, http_settings: HttpSettings) -> None:
        self._http_settings = http_settings

    async def discover(self, brand: Brand) -> list[Contact]:
        if brand.website is None:
            return []
        urls = [str(brand.website), str(brand.website).rstrip("/") + "/contact"]
        contacts: list[Contact] = []
        async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds, follow_redirects=True) as client:
            for url in urls:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                except httpx.HTTPError:
                    continue
                contacts.extend(_contacts_from_html(brand, response.text))
        return contacts


class LinkedInSearchContactProvider:
    def __init__(self, google_settings: GoogleSettings, http_settings: HttpSettings) -> None:
        self._google_settings = google_settings
        self._http_settings = http_settings

    async def discover(self, brand: Brand) -> list[Contact]:
        if self._google_settings.search_api_key is None or not self._google_settings.search_engine_id:
            logger.warning("Skipping LinkedIn search because Google Search credentials are not configured.")
            return []
        queries = [
            f'site:linkedin.com/in "{brand.name}" "{label}"'
            for label in ["marketing", "growth", "partnerships", "creator manager", "influencer manager"]
        ]
        contacts: list[Contact] = []
        async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds) as client:
            for query in queries:
                try:
                    response = await client.get(
                        "https://www.googleapis.com/customsearch/v1",
                        params={
                            "key": self._google_settings.search_api_key.get_secret_value(),
                            "cx": self._google_settings.search_engine_id,
                            "q": query,
                            "num": 5,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPError as error:
                    logger.warning("LinkedIn search failed for %s: %s", brand.name, error)
                    continue
                for item in payload.get("items", []):
                    if not isinstance(item, dict):
                        continue
                    link = _optional_str(item.get("link"))
                    title = _optional_str(item.get("title"))
                    if not link or "linkedin.com/in" not in link:
                        continue
                    contacts.append(
                        Contact(
                            brand_id=str(brand.id),
                            brand_name=brand.name,
                            name=_name_from_linkedin_title(title or ""),
                            title=title,
                            linkedin=link,
                            role=infer_role(title or ""),
                            confidence_score=0.62,
                            sources=[ContactSource.LINKEDIN_SEARCH],
                        )
                    )
        return contacts


class ContactDiscoveryService:
    def __init__(
        self,
        *,
        providers: list[ContactProvider],
        repository: ContactRepository,
        settings: Settings | None = None,
    ) -> None:
        self._providers = providers
        self._repository = repository
        self._settings = settings or get_settings()

    async def discover(self, brand: Brand) -> list[Contact]:
        discovered: list[Contact] = []
        for provider in self._providers:
            try:
                discovered.extend(await provider.discover(brand))
            except Exception as error:
                logger.warning("Contact provider failed for %s: %s", brand.name, error)
        deduped = _dedupe_contacts(discovered)
        ranked = sorted(deduped, key=lambda item: item.confidence_score, reverse=True)[
            : self._settings.contact_discovery.max_contacts
        ]
        await self._repository.initialize()
        return await self._repository.upsert_contacts(brand, ranked)


def create_contact_providers(settings: Settings) -> list[ContactProvider]:
    return [
        ApolloContactProvider(ApolloClient(settings.apollo, settings.http)),
        WebsiteContactProvider(settings.http),
        LinkedInSearchContactProvider(settings.google, settings.http),
    ]


def infer_role(title: str) -> ContactRole | None:
    normalized = title.lower()
    for role, keywords in ROLE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return role
    return None


def _contacts_from_html(brand: Brand, html: str) -> list[Contact]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    emails = sorted(set(EMAIL_PATTERN.findall(text + " " + html)))
    contacts: list[Contact] = []
    for email in emails:
        local_part = email.split("@", maxsplit=1)[0].replace(".", " ").replace("_", " ")
        role = infer_role(local_part)
        confidence = 0.72 if role else 0.45
        contacts.append(
            Contact(
                brand_id=str(brand.id),
                brand_name=brand.name,
                name=None,
                title=local_part.title(),
                email=email,
                role=role,
                confidence_score=confidence,
                sources=[ContactSource.COMPANY_WEBSITE],
            )
        )
    return contacts


def _dedupe_contacts(contacts: list[Contact]) -> list[Contact]:
    deduped: dict[str, Contact] = {}
    for contact in contacts:
        key = (contact.email or str(contact.linkedin or "") or f"{contact.name}:{contact.title}").lower()
        if key not in deduped or contact.confidence_score > deduped[key].confidence_score:
            deduped[key] = contact
    return list(deduped.values())


def _brand_domain(brand: Brand) -> str | None:
    if brand.website is None:
        return None
    from urllib.parse import urlparse

    parsed = urlparse(str(brand.website))
    return parsed.netloc.removeprefix("www.") or None


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _name_from_linkedin_title(title: str) -> str | None:
    if not title:
        return None
    return title.split("-")[0].split("|")[0].strip() or None
