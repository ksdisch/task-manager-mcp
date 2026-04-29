"""Shape Todoist SDK objects into LLM-friendly dicts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

DESCRIPTION_PREVIEW_LEN = 200
TRUNCATED_SUFFIX = "...[truncated]"


def format_project(project: Any) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "parent_id": project.parent_id,
    }


def format_label(label: Any) -> dict:
    return {
        "id": label.id,
        "name": label.name,
        "color": label.color,
        "is_favorite": label.is_favorite,
    }


def format_section(section: Any) -> dict:
    return {
        "id": section.id,
        "name": section.name,
        "project_id": section.project_id,
        "order": section.order,
    }


def format_task(task: Any) -> dict:
    """Full-view task for create/update/get — no description truncation."""
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


def format_task_preview(task: Any) -> dict:
    """Search-result task — description truncated to 200 chars."""
    return {
        "id": task.id,
        "content": task.content,
        "project_id": task.project_id,
        "labels": list(task.labels) if task.labels else [],
        "priority": task.priority,
        "due": _format_due(task.due),
        "description_preview": _truncate_description(task.description),
    }


def _truncate_description(desc: str | None) -> str:
    if not desc:
        return ""
    if len(desc) > DESCRIPTION_PREVIEW_LEN:
        return desc[:DESCRIPTION_PREVIEW_LEN] + TRUNCATED_SUFFIX
    return desc


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
