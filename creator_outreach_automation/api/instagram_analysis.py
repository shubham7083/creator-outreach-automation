from __future__ import annotations

import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from creator_outreach_automation.browser.playwright_runner import PlaywrightBrowserRunner
from creator_outreach_automation.models.creator_analysis import InstagramCreatorSnapshot, InstagramPost
from creator_outreach_automation.services.creator_analysis_extraction import HASHTAG_PATTERN

logger = logging.getLogger(__name__)


class InstagramAnalysisError(RuntimeError):
    """Raised when Instagram profile analysis cannot complete."""


class InstagramAnalysisClient:
    def __init__(self, browser_runner: PlaywrightBrowserRunner) -> None:
        self._browser_runner = browser_runner

    async def collect_profile(self, username: str, *, max_posts: int) -> InstagramCreatorSnapshot:
        normalized_username = username.strip().lstrip("@")
        url = f"https://www.instagram.com/{normalized_username}/"
        try:
            async with self._browser_runner.browser() as browser:
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                html = await page.content()
                await page.close()
        except Exception as error:
            logger.warning("Instagram browser collection failed for %s: %s", normalized_username, error)
            raise InstagramAnalysisError(
                "Instagram analysis could not open a browser. Run `python -m playwright install chromium` "
                "or use YouTube analysis until browser automation is available."
            ) from error

        snapshot = parse_instagram_profile_html(
            html,
            username=normalized_username,
            max_posts=max_posts,
        )
        logger.info("Collected Instagram profile username=%s", normalized_username)
        return snapshot


def parse_instagram_profile_html(
    html: str,
    *,
    username: str,
    max_posts: int,
) -> InstagramCreatorSnapshot:
    soup = BeautifulSoup(html, "html.parser")
    description = _meta_content(soup, "description")
    followers = _parse_followers_from_description(description)
    bio = _extract_bio_from_description(description)
    raw_metadata = _extract_json_metadata(soup)
    posts = _extract_posts(raw_metadata, max_posts=max_posts)

    if raw_metadata:
        user = _find_user_object(raw_metadata, username=username) or {}
        bio = str(user.get("biography") or bio)
        followers = _optional_int_from_path(user, "edge_followed_by", "count") or followers
        full_name = user.get("full_name")
        following = _optional_int_from_path(user, "edge_follow", "count")
        posts_count = _optional_int_from_path(user, "edge_owner_to_timeline_media", "count")
    else:
        full_name = None
        following = None
        posts_count = None

    return InstagramCreatorSnapshot(
        username=username,
        full_name=str(full_name) if full_name else None,
        bio=bio,
        followers=followers,
        following=following,
        posts_count=posts_count,
        recent_posts=posts,
        raw_metadata=raw_metadata,
    )


def _meta_content(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"name": name})
    if tag and isinstance(tag.get("content"), str):
        return str(tag["content"])
    tag = soup.find("meta", attrs={"property": f"og:{name}"})
    if tag and isinstance(tag.get("content"), str):
        return str(tag["content"])
    return ""


def _parse_followers_from_description(description: str) -> int | None:
    match = re.search(r"([\d,.]+)\s*([KMB])?\s+Followers", description, re.IGNORECASE)
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(
        (match.group(2) or "").upper(),
        1,
    )
    return int(number * multiplier)


def _extract_bio_from_description(description: str) -> str:
    parts = description.split(" - ", maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    return description.strip()


def _extract_json_metadata(soup: BeautifulSoup) -> dict[str, Any]:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.string or script.get_text()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _find_user_object(payload: dict[str, Any], *, username: str) -> dict[str, Any] | None:
    if payload.get("username") == username:
        return payload
    for value in payload.values():
        if isinstance(value, dict):
            found = _find_user_object(value, username=username)
            if found:
                return found
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    found = _find_user_object(item, username=username)
                    if found:
                        return found
    return None


def _extract_posts(payload: dict[str, Any], *, max_posts: int) -> list[InstagramPost]:
    posts: list[InstagramPost] = []
    nodes = _find_post_nodes(payload)
    for node in nodes[:max_posts]:
        caption = _extract_caption(node)
        shortcode = node.get("shortcode") or node.get("shortCode")
        url = f"https://www.instagram.com/p/{shortcode}/" if shortcode else None
        posts.append(
            InstagramPost(
                shortcode=str(shortcode) if shortcode else None,
                caption=caption,
                hashtags=sorted({tag.lower() for tag in HASHTAG_PATTERN.findall(caption)}),
                like_count=_optional_int_from_path(node, "edge_liked_by", "count")
                or _optional_int_from_path(node, "edge_media_preview_like", "count"),
                comment_count=_optional_int_from_path(node, "edge_media_to_comment", "count"),
                url=url,
                published_at=str(node.get("taken_at_timestamp"))
                if node.get("taken_at_timestamp")
                else None,
            )
        )
    return posts


def _find_post_nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for value in payload.values():
        if isinstance(value, dict):
            if "shortcode" in value or "shortCode" in value:
                nodes.append(value)
            nodes.extend(_find_post_nodes(value))
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    if "shortcode" in item or "shortCode" in item:
                        nodes.append(item)
                    nodes.extend(_find_post_nodes(item))
    return nodes


def _extract_caption(node: dict[str, Any]) -> str:
    edges = node.get("edge_media_to_caption", {}).get("edges", [])
    if edges and isinstance(edges, list):
        first = edges[0]
        if isinstance(first, dict):
            caption = first.get("node", {}).get("text")
            if isinstance(caption, str):
                return caption
    caption = node.get("caption")
    return str(caption) if caption else ""


def _optional_int_from_path(payload: dict[str, Any], *path: str) -> int | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    try:
        return int(current)
    except (TypeError, ValueError):
        return None
