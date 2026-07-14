"""Newsfeed MCP server.

Provides tools for fetching current headlines and discussions from:
- Hacker News
- Lobste.rs
- TechCrunch
"""

from fastmcp import FastMCP

from newsfeed_mcp import hackernews
from newsfeed_mcp import lobsters
from newsfeed_mcp import techcrunch

mcp = FastMCP("newsfeed")

# Hacker News
mcp.tool(
    name="hackernews",
    description=(
        "Fetches the current Hacker News front page via the official API, returning title, "
        "URL, points, comment count, and HN discussion link for each story, 10 per page, in "
        "the site's actual live rank order (matching news.ycombinator.com). "
        "Use when the user wants to see what's currently popular or trending on Hacker News. "
        "Does not support past dates (HN exposes no historical rankings) or return article "
        "text/comments — use a general-purpose web page fetching tool for a linked article's "
        "body, or `hackernews_comments` for the discussion."
    ),
)(hackernews.feed)

mcp.tool(
    name="hackernews_comments",
    description=(
        "Fetches all comments from a Hacker News discussion, including nested replies, "
        "preserving the site's own nested reply structure, 50 comments per page. "
        "Use when the user wants to see what people are saying, discussing, or debating about "
        "a Hacker News story, or wants a specific comment sub-thread. "
        "Does not fetch the linked article's content — use a general-purpose web page fetching "
        "tool for that; accepts a story's or comment's HN discussion URL "
        "(https://news.ycombinator.com/item?id=...) or numeric id, not the front page itself."
    ),
)(hackernews.comments)

# Lobste.rs
mcp.tool(
    name="lobsters",
    description=(
        "Fetches the current Lobste.rs front page (hottest stories) via the official API, "
        "returning title, URL, points, comment count, and discussion link for each story, 10 "
        "per page, in the site's actual live rank order. "
        "Use when the user wants to see what's currently popular or trending on Lobste.rs, a "
        "programming and tech-focused link aggregator. "
        "Does not support past dates (the API exposes no historical rankings) or return article "
        "text/comments — use a general-purpose web page fetching tool for a linked story's "
        "body, or `lobsters_comments` for the discussion."
    ),
)(lobsters.feed)

mcp.tool(
    name="lobsters_comments",
    description=(
        "Fetches all comments from a Lobste.rs story discussion, including nested replies, "
        "preserving the site's own nested reply structure, 50 comments per page. "
        "Use when the user wants to see what people are saying, discussing, or debating about "
        "a Lobste.rs story, or wants a specific comment sub-thread. "
        "Does not fetch the linked story's content — use a general-purpose web page fetching "
        "tool for that; accepts a story's Lobste.rs URL (https://lobste.rs/s/<short_id>/...) or "
        "its short id, not the front page itself."
    ),
)(lobsters.comments)

# TechCrunch
mcp.tool(
    name="techcrunch",
    description=(
        "Fetches TechCrunch articles published on a given date via the site's RSS feed, "
        "returning title, URL, and a short description for each, 10 per page. "
        "Use when the user wants TechCrunch headlines or news for today, yesterday, or a "
        "specific date, or wants to browse what TechCrunch covered. "
        "Does not fetch full article bodies — use a general-purpose web page fetching tool with "
        "a result's URL for that; the date must be 'today', 'yesterday', or YYYY-MM-DD (convert "
        "other phrasing like 'last Monday' yourself first)."
    ),
)(techcrunch.feed)



