from __future__ import annotations

import streamlit as st

from app.ui.styles import section_header
from creator_outreach_automation.config import Settings


def render_settings(settings: Settings) -> None:
    st.title("Settings")
    section_header("Runtime Configuration", "Credential-backed features are disabled gracefully when keys are missing.")

    rows = [
        ("OpenAI scoring and email generation", settings.openai.api_key is not None, "OPENAI_API_KEY"),
        ("YouTube Data API", settings.google.youtube_api_key is not None, "YOUTUBE_API_KEY"),
        ("Google Search", settings.google.search_api_key is not None and bool(settings.google.search_engine_id), "GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID"),
        ("Apollo contact discovery", settings.apollo.api_key is not None, "APOLLO_API_KEY"),
        ("Gmail draft creation", _gmail_ready(settings), "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN, GMAIL_SENDER_EMAIL"),
        ("GitHub organization search", settings.github.token is not None, "GITHUB_TOKEN optional"),
    ]

    for label, enabled, requirement in rows:
        status = "Enabled" if enabled else "Disabled"
        st.write(
            {
                "feature": label,
                "status": status,
                "configuration": requirement,
            }
        )

    st.divider()
    st.subheader("Paths")
    st.json(
        {
            "database": settings.database.safe_url,
            "cache": str(settings.paths.cache_dir),
            "outputs": str(settings.paths.output_dir),
            "prompts": str(settings.paths.prompts_dir),
        }
    )


def _gmail_ready(settings: Settings) -> bool:
    return (
        settings.google.client_id is not None
        and settings.google.client_secret is not None
        and settings.google.refresh_token is not None
        and bool(settings.google.gmail_sender_email)
    )
