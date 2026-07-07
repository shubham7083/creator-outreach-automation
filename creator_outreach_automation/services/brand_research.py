from __future__ import annotations

import logging

from creator_outreach_automation.models.brand import Brand

logger = logging.getLogger(__name__)


class BrandResearchService:
    async def research(self, brand: Brand) -> Brand:
        logger.info("Preparing brand research for brand_id=%s", brand.id)
        return brand
