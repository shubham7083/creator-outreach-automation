from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, TypeVar

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from creator_outreach_automation.models.brand import Brand  # noqa: E402


ElementT = TypeVar("ElementT")


def main() -> None:
    app = AppTest.from_file(str(ROOT_DIR / "app" / "streamlit_app.py"))
    app.run(timeout=15)
    _assert_ok(app)

    _go_to(app, "Creator Analysis")
    _click(app, "Analyze")
    _assert_ok(app)

    _go_to(app, "Brand Discovery")
    _click(app, "Discover brands")
    _assert_ok(app)

    _text_input(app, "Brand name").set_value("Example Brand")
    _text_input(app, "Website").set_value("https://example.com")
    _text_area(app, "Description").set_value("Workflow software for creator teams.")
    _text_input(app, "Industry").set_value("Creator Tools")
    _click(app, "Add brand")
    _assert_ok(app)

    app.session_state["brands"] = [
        Brand(
            name="Example Brand",
            website="https://example.com",
            description="Workflow software for creator teams.",
            industry="Creator Tools",
            discovery_sources=["manual"],
        )
    ]
    _go_to(app, "Brand Scoring")
    _click(app, "Score brand")
    _assert_ok(app)

    _go_to(app, "Contact Discovery")
    _text_input(app, "Name").set_value("Alex Partner")
    _text_input(app, "Title").set_value("Partnerships Lead")
    _text_input(app, "Email").set_value("alex@example.com")
    _click(app, "Save contact")
    _assert_ok(app)

    _go_to(app, "Email Drafts")
    _assert_ok(app)

    print("verified form smoke paths")


def _go_to(app: AppTest, page: str) -> None:
    navigation = next(radio for radio in app.radio if "Dashboard" in radio.options)
    navigation.set_value(page).run(timeout=15)
    _assert_ok(app)


def _click(app: AppTest, label: str) -> None:
    button = _find(app.button, label)
    button.click().run(timeout=15)


def _text_input(app: AppTest, label: str):
    return _find(app.text_input, label)


def _text_area(app: AppTest, label: str):
    return _find(app.text_area, label)


def _find(elements: Iterable[ElementT], label: str) -> ElementT:
    for element in elements:
        if getattr(element, "label", None) == label:
            return element
    raise RuntimeError(f"Element not found: {label}")


def _assert_ok(app: AppTest) -> None:
    if app.exception:
        raise RuntimeError(app.exception)


if __name__ == "__main__":
    main()
