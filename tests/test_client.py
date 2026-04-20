from unittest.mock import MagicMock, patch

import pytest

from todoist_mcp.client import TodoistClient


def _fake_project(id_: str, name: str, parent_id: str | None) -> MagicMock:
    m = MagicMock()
    m.id = id_
    m.name = name
    m.parent_id = parent_id
    return m


@patch("todoist_mcp.client.TodoistAPI")
def test_list_projects_flattens_pages_and_shapes_response(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.get_projects.return_value = iter(
        [
            [_fake_project("1", "Inbox", None), _fake_project("2", "Work", None)],
            [_fake_project("3", "Subproject", "2")],
        ]
    )

    client = TodoistClient(token="fake-token")
    projects = client.list_projects()

    assert projects == [
        {"id": "1", "name": "Inbox", "parent_id": None},
        {"id": "2", "name": "Work", "parent_id": None},
        {"id": "3", "name": "Subproject", "parent_id": "2"},
    ]
    mock_api_cls.assert_called_once_with("fake-token")


def test_missing_token_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TODOIST_API_TOKEN", raising=False)
    monkeypatch.setattr("todoist_mcp.client.load_dotenv", lambda *a, **kw: None)

    with pytest.raises(RuntimeError, match="TODOIST_API_TOKEN"):
        TodoistClient()
