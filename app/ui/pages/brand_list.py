from __future__ import annotations

import streamlit as st

from app.ui.runtime import run_async
from app.ui.state import add_campaign_event, brands, creator_profile
from app.ui.styles import section_header
from creator_outreach_automation.config import Settings
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.services.factory import create_brand_discovery_engine


def render_brand_list(settings: Settings) -> None:
    st.title("Brand Discovery")
    section_header("Discovery and Filters", "Discover, search, and curate brands for outreach.")

    if st.button("Discover brands", type="primary"):
        profile = creator_profile()
        if profile is None:
            st.error("Analyze a creator first.")
        else:
            try:
                engine = create_brand_discovery_engine(settings)
                with st.spinner("Discovering brands"):
                    discovered = run_async(engine.discover(profile))
                st.session_state["brands"] = discovered
                add_campaign_event(f"Discovered {len(discovered)} brands.")
                st.success("Brand discovery complete.")
            except Exception as error:
                st.error(f"Brand discovery failed: {error}")

    with st.expander("Add brand manually"):
        name = st.text_input("Brand name")
        website = st.text_input("Website")
        description = st.text_area("Description")
        industry = st.text_input("Industry")
        if st.button("Add brand"):
            if not name.strip():
                st.error("Brand name is required.")
            else:
                current = brands()
                current.append(
                    Brand(
                        name=name.strip(),
                        website=website.strip() or None,
                        description=description.strip() or None,
                        industry=industry.strip() or None,
                        discovery_sources=["manual"],
                    )
                )
                st.session_state["brands"] = current
                add_campaign_event(f"Added brand {name.strip()}.")
                st.success("Brand added.")

    st.divider()
    _render_brand_table()


def _render_brand_table() -> None:
    query = str(st.session_state.get("search_query", "")).lower()
    industry_filter = st.session_state.get("industry_filter", "All")
    rows = []
    for brand in brands():
        if query and query not in brand.name.lower() and query not in (brand.description or "").lower():
            continue
        if industry_filter != "All" and brand.industry != industry_filter:
            continue
        rows.append(
            {
                "name": brand.name,
                "website": str(brand.website) if brand.website else "",
                "industry": brand.industry or "",
                "location": brand.location or "",
                "description": brand.description or "",
            }
        )
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("No brands match the current filters.")
