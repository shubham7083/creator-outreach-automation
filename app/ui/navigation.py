from __future__ import annotations

import streamlit as st

from app.ui.pages.analytics import render_analytics
from app.ui.pages.brand_list import render_brand_list
from app.ui.pages.brand_score import render_brand_score
from app.ui.pages.campaign_status import render_campaign_status
from app.ui.pages.contact_details import render_contact_details
from app.ui.pages.creator_search import render_creator_search
from app.ui.pages.dashboard import render_dashboard
from app.ui.pages.outreach import render_outreach
from app.ui.pages.settings import render_settings
from app.ui.state import ensure_state
from app.ui.styles import apply_theme
from creator_outreach_automation.config import Settings


PAGES = {
    "Dashboard": render_dashboard,
    "Creator Analysis": render_creator_search,
    "Brand Discovery": render_brand_list,
    "Brand Scoring": render_brand_score,
    "Contact Discovery": render_contact_details,
    "Email Drafts": render_outreach,
    "Campaign Pipeline": render_campaign_status,
    "Analytics": render_analytics,
    "Settings": render_settings,
}


def render_app(settings: Settings) -> None:
    ensure_state()
    apply_theme()

    with st.sidebar:
        st.title(settings.app_name)
        st.caption(settings.app_env)
        page_name = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
        st.divider()
        st.text_input("Search", key="search_query", placeholder="Search brands, contacts, status")
        st.selectbox("Approval", ["All", "Approved", "Rejected", "Unscored"], key="approval_filter")
        st.selectbox("Industry", _industry_options(), key="industry_filter")
        st.divider()
        st.markdown('<span class="status-pill">Draft-only Gmail mode</span>', unsafe_allow_html=True)

    PAGES[page_name](settings)


def _industry_options() -> list[str]:
    brands = st.session_state.get("brands", [])
    industries = sorted({brand.industry for brand in brands if getattr(brand, "industry", None)})
    return ["All", *industries]
