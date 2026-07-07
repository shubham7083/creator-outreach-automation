from __future__ import annotations

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import Radio


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

PAGES = [
    "Dashboard",
    "Creator Analysis",
    "Brand Discovery",
    "Brand Scoring",
    "Contact Discovery",
    "Email Drafts",
    "Campaign Pipeline",
    "Analytics",
    "Settings",
]


def main() -> None:
    app = AppTest.from_file(str(ROOT_DIR / "app" / "streamlit_app.py"))
    app.run(timeout=15)
    if app.exception:
        raise RuntimeError(app.exception)

    for page in PAGES[1:]:
        navigation = _navigation_radio(app.radio)
        navigation.set_value(page).run(timeout=15)
        if app.exception:
            raise RuntimeError(f"{page} failed: {app.exception}")

    print("verified pages: " + ", ".join(PAGES))


def _navigation_radio(radios: list[Radio]) -> Radio:
    for radio in radios:
        if list(radio.options) == PAGES:
            return radio
    raise RuntimeError("Navigation radio was not rendered")


if __name__ == "__main__":
    main()
