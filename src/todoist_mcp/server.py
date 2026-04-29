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


@mcp.tool()
def todoist_create_task(
    content: str,
    project_id: str | None = None,
    section_id: str | None = None,
    labels: list[str] | None = None,
    priority: int | None = None,
    due_string: str | None = None,
    description: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """Create a new Todoist task.

    priority: 1=normal (lowest) through 4=urgent (highest).
    due_string: natural language like "tomorrow at 3pm", "every monday".
    Returns the created task.
    """
    return _get_client().create_task(
        content=content,
        project_id=project_id,
        section_id=section_id,
        parent_id=parent_id,
        labels=labels,
        priority=priority,
        due_string=due_string,
        description=description,
    )


@mcp.tool()
def todoist_update_task(
    task_id: str,
    content: str | None = None,
    description: str | None = None,
    labels: list[str] | None = None,
    priority: int | None = None,
    due_string: str | None = None,
    project_id: str | None = None,
    section_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """Update a Todoist task. Only fields you pass are changed.

    Moves (project_id / section_id / parent_id) are handled automatically via
    the move endpoint — you can change section + content in one call.
    Returns the updated task.
    """
    fields = {
        "content": content,
        "description": description,
        "labels": labels,
        "priority": priority,
        "due_string": due_string,
        "project_id": project_id,
        "section_id": section_id,
        "parent_id": parent_id,
    }
    return _get_client().update_task(
        task_id,
        **{k: v for k, v in fields.items() if v is not None},
    )


@mcp.tool()
def todoist_complete_task(task_id: str) -> dict:
    """Mark a Todoist task as complete. Returns {completed, task_id}."""
    return _get_client().complete_task(task_id)


@mcp.tool()
def todoist_search_tasks(filter: str, limit: int = 50) -> dict:  # noqa: A002
    """Search Todoist tasks using the native filter syntax.

    Filter examples:
      "@waiting-on"              — tasks with the waiting-on label
      "p1 & today"                     — priority-1 tasks due today
      "#Inbox & no date"               — Inbox tasks with no due date
      "overdue"                        — anything past its due date
      "7 days & !@waiting-on"    — due in next 7 days, excluding waiting-on

    limit caps at 200 (default 50). Descriptions are truncated to 200 chars.
    Response: {tasks: [...], count: int, truncated: bool}. truncated=true means
    there are more matches than `limit` — refine the filter or raise the limit.
    """
    return _get_client().search_tasks(filter_query=filter, limit=limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
