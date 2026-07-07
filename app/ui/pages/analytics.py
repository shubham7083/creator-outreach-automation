from __future__ import annotations

from collections import Counter

import streamlit as st

from app.ui.state import approved_brands, brands, contacts, outreach_sequences, scored_brands
from app.ui.styles import section_header
from creator_outreach_automation.config import Settings


def render_analytics(settings: Settings) -> None:
    st.title("Analytics")
    section_header("Pipeline Analytics", "Measure brand fit and campaign readiness.")

    scored = scored_brands()
    cols = st.columns(4)
    cols[0].metric("Brands", len(brands()))
    cols[1].metric("Average score", f"{_average_score(scored):.1f}" if scored else "0.0")
    cols[2].metric("Approval rate", f"{_approval_rate():.0%}")
    cols[3].metric("Contacts", len(contacts()))

    if scored:
        st.bar_chart({item.brand.name: item.score.score for item in scored})

    industry_counts = Counter(brand.industry or "Unknown" for brand in brands())
    if industry_counts:
        st.subheader("Brands by Industry")
        st.bar_chart(dict(industry_counts))

    draft_counts = {sequence.brand_name: len(sequence.drafts) for sequence in outreach_sequences()}
    if draft_counts:
        st.subheader("Gmail Drafts by Brand")
        st.bar_chart(draft_counts)


def _average_score(items) -> float:
    if not items:
        return 0.0
    return sum(item.score.score for item in items) / len(items)


def _approval_rate() -> float:
    total = len(scored_brands())
    if not total:
        return 0.0
    return len(approved_brands()) / total
