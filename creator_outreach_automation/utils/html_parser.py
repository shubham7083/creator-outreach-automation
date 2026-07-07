from __future__ import annotations

from bs4 import BeautifulSoup


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def extract_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        str(anchor["href"])
        for anchor in soup.find_all("a", href=True)
        if isinstance(anchor.get("href"), str)
    ]
