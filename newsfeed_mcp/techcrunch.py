"""TechCrunch RSS client."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import requests

FEED_URL = "https://techcrunch.com/feed/"
PT_TZ = ZoneInfo("America/Los_Angeles")

_MAX_ITEMS = 50
_MAX_PAGES = 5
_DESC_MAX_LEN = 200
_PAGE_SIZE = 10


@dataclass
class Article:
    title: str
    url: str
    description: str
    published_at: datetime


def _fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    resp.raise_for_status()
    return resp.text


def _strip_cdata(text: str) -> str:
    m = re.match(r"<!\[CDATA\[(.*?)]]>", text, re.DOTALL)
    return m.group(1) if m else text


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _truncate(text: str, max_len: int) -> str:
    return text[:max_len].rstrip() + "…" if len(text) > max_len else text


def _parse_date(arg: str, today: date) -> date:
    arg = arg.lower().strip()
    if arg == "today":
        return today
    if arg == "yesterday":
        return today - timedelta(days=1)
    try:
        return date.fromisoformat(arg)
    except ValueError:
        raise ValueError(f"Unrecognized date: {arg!r}. Use 'today', 'yesterday', or YYYY-MM-DD.")


def _parse_feed(xml_text: str) -> list[Article]:
    root = ET.fromstring(xml_text)
    articles = []
    for item in root.findall("./channel/item")[:_MAX_ITEMS]:
        title = _strip_cdata(item.findtext("title", "")).strip()
        url = item.findtext("link", "").strip()
        desc = _strip_html(_strip_cdata(item.findtext("description", "")))
        pub_date_str = item.findtext("pubDate", "")
        try:
            published_at = parsedate_to_datetime(pub_date_str).astimezone(PT_TZ)
        except Exception:
            continue
        articles.append(Article(
            title=title,
            url=url,
            description=_truncate(desc, _DESC_MAX_LEN),
            published_at=published_at,
        ))
    return articles


def _filter(articles: list[Article], filter_date: date) -> list[Article]:
    return [a for a in articles if a.published_at.date() == filter_date]


def _fetch_news(when: str | date) -> list[Article]:
    today = datetime.now(PT_TZ).date()
    filter_date = _parse_date(when, today) if isinstance(when, str) else when
    result = []
    for page in range(1, _MAX_PAGES + 1):
        articles = _parse_feed(_fetch(f"{FEED_URL}?paged={page}"))
        if not articles:
            break
        result.extend(_filter(articles, filter_date))
        if min(a.published_at.date() for a in articles) < filter_date:
            break
    return result


def _format_page(articles: list[Article], page: int, date_arg: str) -> str:
    if not articles:
        return f"No articles found for {date_arg}."
    total = len(articles)
    start = (page - 1) * _PAGE_SIZE
    page_articles = articles[start:start + _PAGE_SIZE]
    if not page_articles:
        return f"No more articles on page {page} for {date_arg}."
    lines = []
    for idx, a in enumerate(page_articles, start + 1):
        lines.append(f"{idx}. {a.title} ({a.url})")
        lines.append(f"   {a.description}")
        lines.append("")
    end = start + len(page_articles)
    if end < total:
        lines.append(f"Showing {start + 1}–{end} of {total}. Ask for page {page + 1} to see more.")
    return "\n".join(lines).rstrip()


def feed(date: str, page: int = 1) -> str:
    """Fetches TechCrunch articles published on a given date via the site's RSS feed,
    returning title, URL, and a short description for each, 10 per page.
    Use when the user wants TechCrunch headlines or news for today, yesterday, or a
    specific date, or wants to browse what TechCrunch covered.
    Does not fetch full article bodies — use a general-purpose web page fetching tool with
    a result's URL for that; the date must be 'today', 'yesterday', or YYYY-MM-DD (convert
    other phrasing like 'last Monday' yourself first).
    """
    date_arg = str(date)
    page = max(1, int(page))
    return _format_page(_fetch_news(date_arg), page, date_arg)
