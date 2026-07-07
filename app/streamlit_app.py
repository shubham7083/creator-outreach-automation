from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.ui.navigation import render_app
from app.ui.runtime import run_async
from creator_outreach_automation.config import get_settings
from creator_outreach_automation.database.migrations import run_migrations
from creator_outreach_automation.logging.setup import configure_logging


def load_streamlit_secrets_into_environment() -> None:
    try:
        secret_items = st.secrets.items()
    except Exception:
        return
    for key, value in secret_items:
        if isinstance(value, str) and key not in os.environ:
            os.environ[key] = value


def main() -> None:
    load_streamlit_secrets_into_environment()
    settings = get_settings()
    configure_logging(settings.logging)
    run_async(run_migrations())
    st.set_page_config(page_title=settings.app_name, layout="wide")
    render_app(settings)


if __name__ == "__main__":
    main()
