from __future__ import annotations

import streamlit as st

from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.brand_scoring import ScoredBrand
from creator_outreach_automation.models.contact import Contact
from creator_outreach_automation.models.creator_analysis import CreatorProfile
from creator_outreach_automation.models.outreach import OutreachSequenceResult


def ensure_state() -> None:
    defaults: dict[str, object] = {
        "creator_profile": None,
        "brands": [],
        "scored_brands": [],
        "approved_brands": [],
        "contacts": [],
        "outreach_sequences": [],
        "campaign_events": [],
        "search_query": "",
        "industry_filter": "All",
        "approval_filter": "All",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def creator_profile() -> CreatorProfile | None:
    value = st.session_state.get("creator_profile")
    return value if isinstance(value, CreatorProfile) else None


def brands() -> list[Brand]:
    return list(st.session_state.get("brands", []))


def scored_brands() -> list[ScoredBrand]:
    return list(st.session_state.get("scored_brands", []))


def approved_brands() -> list[ScoredBrand]:
    return list(st.session_state.get("approved_brands", []))


def contacts() -> list[Contact]:
    return list(st.session_state.get("contacts", []))


def outreach_sequences() -> list[OutreachSequenceResult]:
    return list(st.session_state.get("outreach_sequences", []))


def add_campaign_event(message: str) -> None:
    events = list(st.session_state.get("campaign_events", []))
    events.insert(0, message)
    st.session_state["campaign_events"] = events[:50]
