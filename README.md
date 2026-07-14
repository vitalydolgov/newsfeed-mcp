# Newsfeed MCP

A simple MCP server that provides current tech news and discussions from:

- **Hacker News**
- **Lobste.rs**
- **TechCrunch**

## Tools

| Tool                  | Description |
|-----------------------|-------------|
| `hackernews`          | Fetches the current Hacker News front page. |
| `hackernews_comments` | Fetches comments from an HN story or comment thread. |
| `lobsters`            | Fetches the Lobste.rs hottest stories. |
| `lobsters_comments`   | Fetches comments from a Lobste.rs story. |
| `techcrunch`          | Fetches TechCrunch articles for a given date. |

## Running

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run python -m newsfeed_mcp
```

Configure an MCP client to run `python -m newsfeed_mcp` from the project directory, using its absolute path:

```json
{"command": "uv", "args": ["run", "--directory", "/path/to/newsfeed-mcp", "python", "-m", "newsfeed_mcp"]}
```

The exact configuration format depends on the client.

## Development

Project layout:

```text
newsfeed-mcp/
├── pyproject.toml
├── README.md
└── newsfeed_mcp/
    ├── __init__.py      # FastMCP server definition
    ├── __main__.py      # entry point for `python -m newsfeed_mcp`
    ├── hackernews.py
    ├── lobsters.py
    └── techcrunch.py
```

After changes, run:

```sh
uv run python -m compileall -q newsfeed_mcp
```
