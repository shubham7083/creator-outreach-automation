from __future__ import annotations

import logging

from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.creator import Creator
from creator_outreach_automation.models.outreach import OutreachMessage

logger = logging.getLogger(__name__)


class OutreachDraftingService:
    async def draft(self, creator: Creator, brand: Brand) -> OutreachMessage:
        logger.info("Preparing outreach draft for creator_id=%s brand_id=%s", creator.id, brand.id)
        subject = f"Collaboration idea for {brand.name}"
        body = (
            f"Hi {brand.name} team,\n\n"
            f"I represent {creator.display_name}. We think there may be a thoughtful collaboration "
            "opportunity around content that is useful to the audience and aligned with your brand.\n\n"
            "Would you be open to a quick conversation?"
        )
        return OutreachMessage(
            creator_id=str(creator.id),
            brand_id=str(brand.id),
            subject=subject,
            body=body,
        )
