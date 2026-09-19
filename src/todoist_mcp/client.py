"""Thin wrapper around the Todoist SDK. Loads token from the repo's .env.

API errors are caught and returned as structured dicts so they never propagate
as raw exceptions into the MCP layer.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from todoist_api_python.api import TodoistAPI

from .formatters import (
    format_label,
    format_project,
    format_section,
    format_task,
    format_task_preview,
)

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

DEFAULT_SEARCH_LIMIT = 50
MAX_SEARCH_LIMIT = 200


def _api_error(exc: httpx.HTTPStatusError) -> dict:
    resp = exc.response
    code = resp.status_code
    out: dict[str, Any] = {
        "error": "todoist_api_error",
        "code": code,
        "message": (resp.text or str(exc))[:500],
    }
    if code == 429:
        retry_after = resp.headers.get("Retry-After")
        out["retry_after"] = int(retry_after) if retry_after and retry_after.isdigit() else None
        out["retryable"] = True
    return out


class TodoistClient:
    def __init__(self, token: str | None = None) -> None:
        if token is None:
            load_dotenv(ENV_PATH)
            token = os.environ.get("TODOIST_API_TOKEN")
            if not token:
                raise RuntimeError(
                    f"TODOIST_API_TOKEN not set. Add it to {ENV_PATH}."
                )
        self._api = TodoistAPI(token)

    def list_projects(self) -> list[dict]:
        try:
            return [
                format_project(p)
                for page in self._api.get_projects()
                for p in page
            ]
        except httpx.HTTPStatusError as e:
            return [_api_error(e)]

    def create_task(
        self,
        *,
        content: str,
        project_id: str | None = None,
        section_id: str | None = None,
        parent_id: str | None = None,
        labels: list[str] | None = None,
        priority: int | None = None,
        due_string: str | None = None,
        description: str | None = None,
    ) -> dict:
        try:
            task = self._api.add_task(
                content=content,
                project_id=project_id,
                section_id=section_id,
                parent_id=parent_id,
                labels=labels,
                priority=priority,
                due_string=due_string,
                description=description,
            )
        except httpx.HTTPStatusError as e:
            return _api_error(e)
        return format_task(task)

    def update_task(self, task_id: str, **fields: Any) -> dict:
        move_fields = {
            "project_id": fields.pop("project_id", None),
            "section_id": fields.pop("section_id", None),
            "parent_id": fields.pop("parent_id", None),
        }
        update_fields = {k: v for k, v in fields.items() if v is not None}

        try:
            if any(v is not None for v in move_fields.values()):
                self._api.move_task(task_id, **move_fields)

            if update_fields:
                task = self._api.update_task(task_id=task_id, **update_fields)
            else:
                task = self._api.get_task(task_id)
        except httpx.HTTPStatusError as e:
            return _api_error(e)
        return format_task(task)

    def get_task(self, task_id: str) -> dict:
        """One task by id, full view: the description is never truncated."""
        try:
            task = self._api.get_task(task_id)
        except httpx.HTTPStatusError as e:
            return _api_error(e)
        return format_task(task)

    def complete_task(self, task_id: str) -> dict:
        try:
            success = self._api.complete_task(task_id=task_id)
        except httpx.HTTPStatusError as e:
            return _api_error(e)
        return {"completed": bool(success), "task_id": task_id}

    def list_labels(self) -> list[dict]:
        try:
            return [
                format_label(label)
                for page in self._api.get_labels()
                for label in page
            ]
        except httpx.HTTPStatusError as e:
            return [_api_error(e)]

    def list_sections(self, project_id: str) -> list[dict]:
        try:
            return [
                format_section(s)
                for page in self._api.get_sections(project_id=project_id)
                for s in page
            ]
        except httpx.HTTPStatusError as e:
            return [_api_error(e)]

    def create_project(
        self,
        *,
        name: str,
        parent_id: str | None = None,
        color: str | None = None,
    ) -> dict:
        try:
            project = self._api.add_project(
                name=name,
                parent_id=parent_id,
                color=color,
            )
        except httpx.HTTPStatusError as e:
            return _api_error(e)
        return format_project(project)

    def search_tasks(self, filter_query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> dict:
        """Native-filter task search. Caps at MAX_SEARCH_LIMIT, truncates descriptions."""
        capped = max(1, min(limit, MAX_SEARCH_LIMIT))

        try:
            pages = self._api.filter_tasks(query=filter_query, limit=capped)
            first_page = next(pages, [])

            # Detect result-list truncation: if the first page filled the cap,
            # peek at the next iteration. Any content there means there's more
            # than the caller's limit.
            truncated = False
            if len(first_page) >= capped:
                next_page = next(pages, None)
                truncated = bool(next_page)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                return {
                    "error": "invalid filter",
                    "filter": filter_query,
                    "hint": (e.response.text or str(e))[:300],
                }
            return _api_error(e)

        tasks = [format_task_preview(t) for t in first_page[:capped]]
        return {"tasks": tasks, "count": len(tasks), "truncated": truncated}
