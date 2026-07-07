from __future__ import annotations

import streamlit as st

from app.ui import state
from app.ui.styles import section_header
from creator_outreach_automation.config import Settings


def render_dashboard(settings: Settings) -> None:
    st.title("Dashboard")
    section_header("Pipeline Overview", "Monitor creator analysis, brand fit, contacts, drafts, and campaign progress.")

    creator = state.creator_profile()
    brands = state.brands()
    scored = state.scored_brands()
    approved = state.approved_brands()
    contacts = state.contacts()
    drafts = state.outreach_sequences()

    cols = st.columns(5)
    cols[0].metric("Creator", "Ready" if creator else "Missing")
    cols[1].metric("Brands", len(brands))
    cols[2].metric("Scored", len(scored))
    cols[3].metric("Approved", len(approved))
    cols[4].metric("Drafts", sum(len(sequence.drafts) for sequence in drafts))

    left, right = st.columns([1.2, 1])
    with left:
        section_header("Recent Activity")
        events = st.session_state.get("campaign_events", [])
        if not events:
            st.info("No campaign activity yet.")
        for event in events[:8]:
            st.write(event)

    with right:
        section_header("Creator Snapshot")
        if not creator:
            st.warning("Analyze or load a creator profile to begin.")
            return
        st.write(
            {
                "handle": creator.handle,
                "niche": creator.niche,
                "audience": creator.audience_summary,
                "estimated_pricing": creator.estimated_pricing,
            }
        )
