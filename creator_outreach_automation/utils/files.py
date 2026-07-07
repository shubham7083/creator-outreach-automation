from __future__ import annotations

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")
