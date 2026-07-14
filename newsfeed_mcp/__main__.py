"""Run the newsfeed MCP server as a module.

Usage:
    python -m newsfeed_mcp
    uv run python -m newsfeed_mcp
"""

from newsfeed_mcp import mcp

if __name__ == "__main__":
    mcp.run()
