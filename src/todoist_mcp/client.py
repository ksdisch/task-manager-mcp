"""Thin wrapper around the Todoist SDK. Loads token from the repo's .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from todoist_api_python.api import TodoistAPI

from .formatters import format_project

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


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
        return [
            format_project(p)
            for page in self._api.get_projects()
            for p in page
        ]
