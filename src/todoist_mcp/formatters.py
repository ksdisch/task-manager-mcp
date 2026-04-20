"""Shape Todoist SDK objects into LLM-friendly dicts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def format_project(project: Any) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "parent_id": project.parent_id,
    }


def format_task(task: Any) -> dict:
    """Full-view task (no description truncation — Phase 3 adds that for search)."""
    return {
        "id": task.id,
        "content": task.content,
        "description": task.description,
        "project_id": task.project_id,
        "section_id": task.section_id,
        "parent_id": task.parent_id,
        "labels": list(task.labels) if task.labels else [],
        "priority": task.priority,
        "due": _format_due(task.due),
    }


def _format_due(due: Any) -> dict | None:
    if due is None:
        return None
    return {
        "date": _iso(getattr(due, "date", None)),
        "string": getattr(due, "string", None),
        "is_recurring": getattr(due, "is_recurring", False),
        "timezone": getattr(due, "timezone", None),
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)
