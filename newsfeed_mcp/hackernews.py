"""Hacker News client (official Firebase API)."""

import html as html_lib
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
_UTC = timezone.utc

_MAX_ITEMS = 100
_PAGE_SIZE = 10
_MAX_COMMENTS = 500
_COMMENT_PAGE_SIZE = 50
_COMMENT_MAX_LEN = 600


@dataclass
class Story:
    title: str
    url: str
    points: int
    num_comments: int
    published_at: datetime
    hn_url: str


def _fetch(url: str, **kwargs) -> requests.Response:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15, **kwargs)
    resp.raise_for_status()
    return resp


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _truncate(text: str, max_len: int) -> str:
    return text[:max_len].rstrip() + "…" if len(text) > max_len else text


@dataclass
class Comment:
    author: str
    text: str
    depth: int
    comment_url: str


def _extract_item_id(url_or_id: str) -> int:
    s = str(url_or_id).strip()
    m = re.search(r"[?&]id=(\d+)", s)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    raise ValueError(
        f"Could not find a Hacker News item id in {url_or_id!r}. Pass the HN discussion URL "
        "(https://news.ycombinator.com/item?id=...) or a numeric id."
    )


def _clean_comment_text(text: str) -> str:
    text = re.sub(r"<p>", "\n\n", text)
    text = _strip_html(text)
    return html_lib.unescape(text).strip()


def _fetch_news() -> list[Story]:
    """Fetch the live front page in its actual rank order, matching news.ycombinator.com."""
    ids = _fetch(_TOP_STORIES_URL).json()[:_MAX_ITEMS]

    with ThreadPoolExecutor(max_workers=20) as pool:
        items = list(pool.map(lambda i: _fetch(_ITEM_URL.format(i)).json(), ids))

    stories = []
    for item in items:
        if not item or item.get("type") != "story" or item.get("dead") or item.get("deleted"):
            continue
        title = (item.get("title") or "").strip()
        if not title:
            continue
        object_id = item.get("id", "")
        hn_url = f"https://news.ycombinator.com/item?id={object_id}"
        stories.append(Story(
            title=title,
            url=item.get("url") or hn_url,
            points=item.get("score") or 0,
            num_comments=item.get("descendants") or 0,
            published_at=datetime.fromtimestamp(item["time"], tz=_UTC),
            hn_url=hn_url,
        ))
    return stories


def _format_page(stories: list[Story], page: int) -> str:
    if not stories:
        return "No Hacker News stories found."
    total = len(stories)
    start = (page - 1) * _PAGE_SIZE
    page_stories = stories[start:start + _PAGE_SIZE]
    if not page_stories:
        return f"No more stories on page {page}."
    lines = []
    for idx, s in enumerate(page_stories, start + 1):
        lines.append(f"{idx}. {s.title} ({s.url})")
        lines.append(f"   {s.points} pts | {s.num_comments} comments | {s.hn_url}")
        lines.append("")
    end = start + len(page_stories)
    if end < total:
        lines.append(f"Showing {start + 1}–{end} of {total}. Ask for page {page + 1} to see more.")
    return "\n".join(lines).rstrip()


def _fetch_comments(item_id: int) -> tuple[list[Comment], bool]:
    """Fetch a story's (or comment's) entire nested reply tree, in the site's own order."""
    root = _fetch(_ITEM_URL.format(item_id)).json()
    if not root:
        raise ValueError(f"No Hacker News item found for id {item_id}.")

    start_ids = root.get("kids", []) if root.get("type") == "story" else [item_id]

    fetched = {}
    frontier = list(start_ids)
    truncated = False
    while frontier:
        remaining = _MAX_COMMENTS - len(fetched)
        if remaining <= 0:
            truncated = True
            break
        batch = frontier[:remaining]
        if len(frontier) > remaining:
            truncated = True

        with ThreadPoolExecutor(max_workers=20) as pool:
            items = list(pool.map(lambda i: _fetch(_ITEM_URL.format(i)).json(), batch))

        next_frontier = []
        for cid, item in zip(batch, items):
            fetched[cid] = item
            if item and not item.get("dead") and not item.get("deleted"):
                next_frontier.extend(item.get("kids", []))
        frontier = next_frontier

    comments = []

    def walk(cid: int, depth: int) -> None:
        item = fetched.get(cid)
        if not item or item.get("dead") or item.get("deleted"):
            return
        text = _clean_comment_text(item.get("text", ""))
        if text:
            comments.append(Comment(
                author=item.get("by", "[unknown]"),
                text=_truncate(text, _COMMENT_MAX_LEN),
                depth=depth,
                comment_url=f"https://news.ycombinator.com/item?id={cid}",
            ))
        for kid in item.get("kids", []):
            walk(kid, depth + 1)

    for cid in start_ids:
        walk(cid, 0)

    return comments, truncated


def _format_comment_page(comments: list[Comment], page: int, truncated: bool) -> str:
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
    elif truncated:
        lines.append(f"Truncated at {_MAX_COMMENTS} comments to bound the fetch.")
    return "\n".join(lines).rstrip()


def feed(page: int = 1) -> str:
    """Fetches the current Hacker News front page via the official API, returning title,
    URL, points, comment count, and HN discussion link for each story, 10 per page, in
    the site's actual live rank order (matching news.ycombinator.com).
    Use when the user wants to see what's currently popular or trending on Hacker News.
    Does not support past dates (HN exposes no historical rankings) or return article
    text/comments — use a general-purpose web page fetching tool for a linked article's
    body, or `hackernews_comments` for the discussion.
    """
    page = max(1, int(page))
    return _format_page(_fetch_news(), page)


def comments(url: str, page: int = 1) -> str:
    """Fetches all comments from a Hacker News discussion, including nested replies,
    preserving the site's own nested reply structure, 50 comments per page.
    Use when the user wants to see what people are saying, discussing, or debating about
    a Hacker News story, or wants a specific comment sub-thread.
    Does not fetch the linked article's content — use a general-purpose web page fetching
    tool for that; accepts a story's or comment's HN discussion URL
    (https://news.ycombinator.com/item?id=...) or numeric id, not the front page itself.
    """
    item_id = _extract_item_id(url)
    page = max(1, int(page))
    all_comments, truncated = _fetch_comments(item_id)
    return _format_comment_page(all_comments, page, truncated)
