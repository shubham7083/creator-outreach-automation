from __future__ import annotations

import streamlit as st

from app.ui.runtime import run_async
from app.ui.state import add_campaign_event
from app.ui.styles import section_header
from creator_outreach_automation.config import Settings
from creator_outreach_automation.models.creator_analysis import CreatorAnalysisInput, CreatorProfile
from creator_outreach_automation.services.factory import create_creator_analysis_service


def render_creator_search(settings: Settings) -> None:
    st.title("Creator Analysis")
    section_header("Analyze Creator", "Start with an Instagram username or YouTube URL.")

    source = st.radio("Source", ["YouTube", "Instagram"], horizontal=True)
    value = st.text_input(
        "Creator",
        placeholder="https://www.youtube.com/@example" if source == "YouTube" else "instagram_username",
    )

    actions = st.columns([1, 5])
    if actions[0].button("Analyze", type="primary", width="stretch"):
        if not value.strip():
            st.error("Enter a creator source first.")
        else:
            _analyze_creator(settings, source, value)

    creator = st.session_state.get("creator_profile")
    if isinstance(creator, CreatorProfile):
        st.divider()
        section_header("Current Creator")
        st.json(creator.model_dump(mode="json"))


def _analyze_creator(settings: Settings, source: str, value: str) -> None:
    try:
        service = create_creator_analysis_service(settings)
        analysis_input = (
            CreatorAnalysisInput(youtube_url=value.strip())
            if source == "YouTube"
            else CreatorAnalysisInput(instagram_username=value.strip())
        )
        with st.spinner("Analyzing creator"):
            profile = run_async(service.analyze(analysis_input))
        st.session_state["creator_profile"] = profile
        add_campaign_event(f"Analyzed creator {profile.handle}.")
        st.success("Creator profile ready.")
    except Exception as error:
        st.warning(str(error))
