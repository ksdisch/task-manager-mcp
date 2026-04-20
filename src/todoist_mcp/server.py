"""FastMCP server exposing Todoist operations over stdio."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .client import TodoistClient

mcp = FastMCP("todoist-mcp")

_client: TodoistClient | None = None


def _get_client() -> TodoistClient:
    global _client
    if _client is None:
        _client = TodoistClient()
    return _client


@mcp.tool()
def todoist_list_projects() -> list[dict]:
    """List all Todoist projects. Returns id, name, and parent_id for each."""
    return _get_client().list_projects()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
