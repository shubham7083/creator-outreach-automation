from __future__ import annotations

import logging
from collections.abc import Sequence

from creator_outreach_automation.models.creator import Creator

logger = logging.getLogger(__name__)


class CreatorDiscoveryService:
    async def discover(self, query: str) -> Sequence[Creator]:
        logger.info("Preparing creator discovery for query=%s", query)
        return []
