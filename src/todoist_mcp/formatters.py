"""Shape Todoist SDK objects into LLM-friendly dicts."""

from typing import Any


def format_project(project: Any) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "parent_id": project.parent_id,
    }
