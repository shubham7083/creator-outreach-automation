from __future__ import annotations

from creator_outreach_automation.config import get_settings


def test_settings_load() -> None:
    settings = get_settings()
    assert settings.app_name
    assert settings.database.url.startswith("sqlite+aiosqlite:///")
