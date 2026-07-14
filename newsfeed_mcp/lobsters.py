"""Lobste.rs client (official JSON API)."""

import re
from dataclasses import dataclass
from datetime import datetime

import requests

_HOTTEST_URL = "https://lobste.rs/hottest.json"
_STORY_URL = "https://lobste.rs/s/{}.json"

_PAGE_SIZE = 10
_COMMENT_PAGE_SIZE = 50
_COMMENT_MAX_LEN = 600


@dataclass
class Story:
    title: str
    url: str
    points: int
    num_comments: int
    published_at: datetime
    lobsters_url: str


@dataclass
class Comment:
    author: str
    text: str
    depth: int
    comment_url: str


def _fetch(url: str, **kwargs) -> requests.Response:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, **kwargs)
    resp.raise_for_status()
    return resp


def _truncate(text: str, max_len: int) -> str:
    return text[:max_len].rstrip() + "…" if len(text) > max_len else text


def _extract_short_id(url_or_id: str) -> str:
    s = str(url_or_id).strip()
    m = re.search(r"lobste\.rs/s/([A-Za-z0-9]+)", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9]+", s):
        return s
    raise ValueError(
        f"Could not find a Lobste.rs short id in {url_or_id!r}. Pass the story's Lobste.rs URL "
        "(https://lobste.rs/s/<short_id>/...) or the short id itself."
    )


def _fetch_news() -> list[Story]:
    items = _fetch(_HOTTEST_URL).json()
    stories = []
    for item in items:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        short_id = item.get("short_id", "")
        lobsters_url = item.get("short_id_url") or f"https://lobste.rs/s/{short_id}"
        stories.append(Story(
            title=title,
            url=item.get("url") or lobsters_url,
            points=item.get("score") or 0,
            num_comments=item.get("comment_count") or 0,
            published_at=datetime.fromisoformat(item["created_at"]),
            lobsters_url=lobsters_url,
        ))
    return stories


def _format_page(stories: list[Story], page: int) -> str:
    if not stories:
        return "No Lobste.rs stories found."
    total = len(stories)
    start = (page - 1) * _PAGE_SIZE
    page_stories = stories[start:start + _PAGE_SIZE]
    if not page_stories:
        return f"No more stories on page {page}."
    lines = []
    for idx, s in enumerate(page_stories, start + 1):
        lines.append(f"{idx}. {s.title} ({s.url})")
        lines.append(f"   {s.points} pts | {s.num_comments} comments | {s.lobsters_url}")
        lines.append("")
    end = start + len(page_stories)
    if end < total:
        lines.append(f"Showing {start + 1}–{end} of {total}. Ask for page {page + 1} to see more.")
    return "\n".join(lines).rstrip()


def _fetch_comments(short_id: str) -> list[Comment]:
    data = _fetch(_STORY_URL.format(short_id)).json()
    comments = []
    for c in data.get("comments", []):
        if c.get("is_deleted") or c.get("is_moderated"):
            continue
        text = (c.get("comment_plain") or "").strip()
        if not text:
            continue
        comments.append(Comment(
            author=c.get("commenting_user", "[unknown]"),
            text=_truncate(text, _COMMENT_MAX_LEN),
            depth=c.get("depth", 0),
            comment_url=c.get("url", ""),
        ))
    return comments


def _format_comment_page(comments: list[Comment], page: int) -> str:
    if not comments:
        return "No comments found."
    total = len(comments)
    start = (page - 1) * _COMMENT_PAGE_SIZE
    page_comments = comments[start:start + _COMMENT_PAGE_SIZE]
    if not page_comments:
        return f"No more comments on page {page}."
    lines = []
    for idx, c in enumerate(page_comments, start + 1):
        indent = "  " * c.depth
        lines.append(f"{indent}{idx}. {c.author}: {c.text}")
        lines.append(f"{indent}   {c.comment_url}")
        lines.append("")
    end = start + len(page_comments)
    if end < total:
        lines.append(f"Showing {start + 1}–{end} of {total}. Ask for page {page + 1} to see more.")
    return "\n".join(lines).rstrip()


def feed(page: int = 1) -> str:
    """Fetches the current Lobste.rs front page (hottest stories) via the official API,
    returning title, URL, points, comment count, and discussion link for each story, 10
    per page, in the site's actual live rank order.
    Use when the user wants to see what's currently popular or trending on Lobste.rs, a
    programming and tech-focused link aggregator.
    Does not support past dates (the API exposes no historical rankings) or return article
    text/comments — use a general-purpose web page fetching tool for a linked story's
    body, or `lobsters_comments` for the discussion.
    """
    page = max(1, int(page))
    return _format_page(_fetch_news(), page)


def comments(url: str, page: int = 1) -> str:
    """Fetches all comments from a Lobste.rs story discussion, including nested replies,
    preserving the site's own nested reply structure, 50 comments per page.
    Use when the user wants to see what people are saying, discussing, or debating about
    a Lobste.rs story, or wants a specific comment sub-thread.
    Does not fetch the linked story's content — use a general-purpose web page fetching
    tool for that; accepts a story's Lobste.rs URL (https://lobste.rs/s/<short_id>/...) or
    its short id, not the front page itself.
    """
    short_id = _extract_short_id(url)
    page = max(1, int(page))
    return _format_comment_page(_fetch_comments(short_id), page)
