from __future__ import annotations

import streamlit as st

from app.ui.state import approved_brands, contacts, outreach_sequences, scored_brands
from app.ui.styles import section_header
from creator_outreach_automation.config import Settings


def render_campaign_status(settings: Settings) -> None:
    st.title("Campaign Pipeline")
    section_header("Operations View", "Review scoring, approvals, contacts, and draft status.")

    rows = []
    approved_ids = {str(item.brand.id) for item in approved_brands()}
    contact_brand_ids = {item.brand_id for item in contacts()}
    draft_brand_ids = {item.brand_id for item in outreach_sequences()}
    for item in scored_brands():
        rows.append(
            {
                "brand": item.brand.name,
                "score": item.score.score,
                "fit": "accepted" if item.accepted else "rejected",
                "approval": "approved" if str(item.brand.id) in approved_ids else "pending",
                "contact": "ready" if str(item.brand.id) in contact_brand_ids else "missing",
                "gmail_drafts": "created" if str(item.brand.id) in draft_brand_ids else "not created",
            }
        )

    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("No campaign status yet.")
