from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            color-scheme: dark;
        }
        .stApp {
            background: #0b0f14;
            color: #e6edf3;
        }
        [data-testid="stSidebar"] {
            background: #0f1620;
            border-right: 1px solid #202b38;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        .metric-card {
            border: 1px solid #202b38;
            background: #111923;
            border-radius: 8px;
            padding: 16px;
            min-height: 100px;
        }
        .muted {
            color: #8b949e;
            font-size: 0.92rem;
        }
        .status-pill {
            display: inline-block;
            border: 1px solid #304050;
            border-radius: 999px;
            padding: 4px 10px;
            background: #121b26;
            color: #c9d1d9;
            font-size: 0.82rem;
        }
        div[data-testid="stButton"] button {
            border-radius: 7px;
            border: 1px solid #2f4154;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #202b38;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    st.subheader(title)
    if subtitle:
        st.markdown(f'<div class="muted">{subtitle}</div>', unsafe_allow_html=True)
