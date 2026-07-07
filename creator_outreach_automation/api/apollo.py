from __future__ import annotations

import logging

import httpx

from creator_outreach_automation.config import ApolloSettings, HttpSettings

logger = logging.getLogger(__name__)


class ApolloClient:
    def __init__(self, apollo_settings: ApolloSettings, http_settings: HttpSettings) -> None:
        self._apollo_settings = apollo_settings
        self._http_settings = http_settings

    async def enrich_contact(self, email_or_domain: str) -> dict[str, object]:
        logger.info("Preparing Apollo enrichment request for identifier=%s", email_or_domain)
        if self._apollo_settings.api_key is None:
            logger.warning("Skipping Apollo enrichment because APOLLO_API_KEY is not configured.")
            return {}

        headers = {
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "X-Api-Key": self._apollo_settings.api_key.get_secret_value(),
        }
        payload = {"q_organization_domains": email_or_domain, "page": 1, "per_page": 10}
        try:
            async with httpx.AsyncClient(timeout=self._http_settings.timeout_seconds) as client:
                response = await client.post(
                    f"{self._apollo_settings.base_url.rstrip('/')}/api/v1/mixed_people/search",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as error:
            logger.warning("Apollo enrichment failed for %s: %s", email_or_domain, error)
            return {}
        return data if isinstance(data, dict) else {}
