from __future__ import annotations

import streamlit as st

from app.ui.runtime import run_async
from app.ui.state import add_campaign_event, approved_brands, brands, creator_profile, scored_brands
from app.ui.styles import section_header
from creator_outreach_automation.config import Settings
from creator_outreach_automation.models.brand import Brand
from creator_outreach_automation.models.brand_scoring import ScoredBrand
from creator_outreach_automation.services.factory import create_brand_scoring_engine


def render_brand_score(settings: Settings) -> None:
    st.title("Brand Scoring")
    section_header("Fit Scoring and Approval", "Score brand fit, approve winners, and reject weak matches.")

    available = brands()
    if not available:
        st.warning("Add or discover brands first.")
        return

    selected_name = st.selectbox("Brand", [brand.name for brand in available])
    brand = next(item for item in available if item.name == selected_name)
    website_summary = st.text_area(
        "Website summary",
        value=brand.description or "",
        placeholder="Summarize the brand website and offer.",
    )

    if st.button("Score brand", type="primary"):
        profile = creator_profile()
        if profile is None:
            st.error("Analyze a creator first.")
        elif not website_summary.strip():
            st.error("Website summary is required.")
        else:
            try:
                engine = create_brand_scoring_engine(settings)
                with st.spinner("Scoring brand"):
                    result = run_async(
                        engine.score_brands(
                            creator_profile=profile,
                            brand_summaries=[(brand, website_summary.strip())],
                        )
                    )
                scored = scored_brands()
                scored.extend(result.ranked_brands + result.rejected_brands)
                st.session_state["scored_brands"] = _dedupe_scored(scored)
                add_campaign_event(f"Scored {brand.name}.")
                st.success("Brand scored.")
            except Exception as error:
                st.error(f"Brand scoring failed: {error}")

    st.divider()
    for item in _filtered_scores(scored_brands()):
        _score_card(item)


def _score_card(item: ScoredBrand) -> None:
    with st.container(border=True):
        cols = st.columns([2, 1, 1, 1])
        cols[0].subheader(item.brand.name)
        cols[1].metric("Score", f"{item.score.score:.1f}")
        cols[2].write("Accepted" if item.accepted else "Rejected")
        if cols[3].button("Approve", key=f"approve-{item.brand.id}", width="stretch"):
            approved = approved_brands()
            approved.append(item.model_copy(update={"accepted": True}))
            st.session_state["approved_brands"] = _dedupe_scored(approved)
            add_campaign_event(f"Approved {item.brand.name}.")
            st.success("Approved.")
        st.write(item.score.reason)
        st.caption(item.score.campaign_idea)


def _filtered_scores(items: list[ScoredBrand]) -> list[ScoredBrand]:
    approval_filter = st.session_state.get("approval_filter", "All")
    if approval_filter == "Approved":
        approved_ids = {str(item.brand.id) for item in approved_brands()}
        return [item for item in items if str(item.brand.id) in approved_ids]
    if approval_filter == "Rejected":
        return [item for item in items if not item.accepted]
    if approval_filter == "Unscored":
        return []
    return sorted(items, key=lambda item: item.score.score, reverse=True)


def _dedupe_scored(items: list[ScoredBrand]) -> list[ScoredBrand]:
    deduped: dict[str, ScoredBrand] = {}
    for item in items:
        deduped[str(item.brand.id)] = item
    return list(deduped.values())
