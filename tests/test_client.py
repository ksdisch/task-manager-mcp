from unittest.mock import MagicMock, patch

import httpx
import pytest

from todoist_mcp.client import TodoistClient


def _fake_project(id_: str, name: str, parent_id: str | None) -> MagicMock:
    m = MagicMock()
    m.id = id_
    m.name = name
    m.parent_id = parent_id
    return m


def _fake_task(**overrides) -> MagicMock:
    defaults = {
        "id": "t1",
        "content": "Test task",
        "description": "",
        "project_id": "p1",
        "section_id": None,
        "parent_id": None,
        "labels": [],
        "priority": 1,
        "due": None,
    }
    defaults.update(overrides)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _http_error(
    status: int, body: str = "boom", headers: dict | None = None
) -> httpx.HTTPStatusError:
    req = httpx.Request("GET", "https://api.todoist.com/fake")
    resp = httpx.Response(status, request=req, text=body, headers=headers or {})
    return httpx.HTTPStatusError("err", request=req, response=resp)


# ---------- list_projects ----------


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


# ---------- create_task ----------


@patch("todoist_mcp.client.TodoistAPI")
def test_create_task_passes_all_fields_and_shapes_response(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.add_task.return_value = _fake_task(id="new-id", content="Do laundry")

    client = TodoistClient(token="t")
    result = client.create_task(
        content="Do laundry",
        project_id="p1",
        section_id="s1",
        parent_id="tp",
        labels=["home"],
        priority=3,
        due_string="tomorrow",
        description="with detergent",
    )

    mock_api.add_task.assert_called_once_with(
        content="Do laundry",
        project_id="p1",
        section_id="s1",
        parent_id="tp",
        labels=["home"],
        priority=3,
        due_string="tomorrow",
        description="with detergent",
    )
    assert result["id"] == "new-id"
    assert result["content"] == "Do laundry"


# ---------- update_task ----------


@patch("todoist_mcp.client.TodoistAPI")
def test_update_task_regular_fields_calls_update_only(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.update_task.return_value = _fake_task(id="t1", content="Renamed")

    client = TodoistClient(token="t")
    result = client.update_task("t1", content="Renamed", priority=4)

    mock_api.update_task.assert_called_once_with(task_id="t1", content="Renamed", priority=4)
    mock_api.move_task.assert_not_called()
    mock_api.get_task.assert_not_called()
    assert result["content"] == "Renamed"


@patch("todoist_mcp.client.TodoistAPI")
def test_update_task_move_only_calls_move_then_fetches(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.move_task.return_value = True
    mock_api.get_task.return_value = _fake_task(id="t1", section_id="s2")

    client = TodoistClient(token="t")
    result = client.update_task("t1", section_id="s2")

    mock_api.move_task.assert_called_once_with(
        "t1", project_id=None, section_id="s2", parent_id=None
    )
    mock_api.update_task.assert_not_called()
    mock_api.get_task.assert_called_once_with("t1")
    assert result["section_id"] == "s2"


@patch("todoist_mcp.client.TodoistAPI")
def test_update_task_move_and_update_combined(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.move_task.return_value = True
    mock_api.update_task.return_value = _fake_task(id="t1", content="New", section_id="s2")

    client = TodoistClient(token="t")
    result = client.update_task("t1", content="New", section_id="s2")

    mock_api.move_task.assert_called_once_with(
        "t1", project_id=None, section_id="s2", parent_id=None
    )
    mock_api.update_task.assert_called_once_with(task_id="t1", content="New")
    mock_api.get_task.assert_not_called()
    assert result["content"] == "New"
    assert result["section_id"] == "s2"


# ---------- complete_task ----------


@patch("todoist_mcp.client.TodoistAPI")
def test_complete_task_returns_success_dict(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.complete_task.return_value = True

    client = TodoistClient(token="t")
    result = client.complete_task("t1")

    mock_api.complete_task.assert_called_once_with(task_id="t1")
    assert result == {"completed": True, "task_id": "t1"}


# ---------- error handling ----------


@patch("todoist_mcp.client.TodoistAPI")
def test_create_task_http_error_returns_error_dict(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.add_task.side_effect = _http_error(400, "bad project id")

    client = TodoistClient(token="t")
    result = client.create_task(content="x", project_id="bogus")

    assert result["error"] == "todoist_api_error"
    assert result["code"] == 400
    assert "bad project id" in result["message"]
    assert "retryable" not in result


@patch("todoist_mcp.client.TodoistAPI")
def test_rate_limit_error_includes_retry_after(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.complete_task.side_effect = _http_error(
        429, "rate limited", headers={"Retry-After": "42"}
    )

    client = TodoistClient(token="t")
    result = client.complete_task("t1")

    assert result["code"] == 429
    assert result["retry_after"] == 42
    assert result["retryable"] is True


@patch("todoist_mcp.client.TodoistAPI")
def test_rate_limit_missing_retry_after_header(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.update_task.side_effect = _http_error(429, "slow down")

    client = TodoistClient(token="t")
    result = client.update_task("t1", content="x")

    assert result["code"] == 429
    assert result["retry_after"] is None
    assert result["retryable"] is True


# ---------- search_tasks ----------


@patch("todoist_mcp.client.TodoistAPI")
def test_search_tasks_basic_shape(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.filter_tasks.return_value = iter(
        [[_fake_task(id="t1", content="Buy milk", description="2%")]]
    )

    client = TodoistClient(token="t")
    result = client.search_tasks("today", limit=10)

    mock_api.filter_tasks.assert_called_once_with(query="today", limit=10)
    assert result["count"] == 1
    assert result["truncated"] is False
    task = result["tasks"][0]
    assert task["id"] == "t1"
    assert task["content"] == "Buy milk"
    assert task["description_preview"] == "2%"
    # Preview shape must NOT include full description or section/parent fields
    assert "description" not in task
    assert "section_id" not in task
    assert "parent_id" not in task


@patch("todoist_mcp.client.TodoistAPI")
def test_search_tasks_uses_default_limit_50(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.filter_tasks.return_value = iter([[]])

    client = TodoistClient(token="t")
    client.search_tasks("@waiting-on")

    mock_api.filter_tasks.assert_called_once_with(query="@waiting-on", limit=50)


@patch("todoist_mcp.client.TodoistAPI")
def test_search_tasks_caps_limit_at_200(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.filter_tasks.return_value = iter([[]])

    client = TodoistClient(token="t")
    client.search_tasks("overdue", limit=5000)

    mock_api.filter_tasks.assert_called_once_with(query="overdue", limit=200)


@patch("todoist_mcp.client.TodoistAPI")
def test_search_tasks_truncates_long_description(mock_api_cls: MagicMock) -> None:
    long_desc = "x" * 250
    mock_api = mock_api_cls.return_value
    mock_api.filter_tasks.return_value = iter([[_fake_task(description=long_desc)]])

    client = TodoistClient(token="t")
    result = client.search_tasks("today")

    preview = result["tasks"][0]["description_preview"]
    assert preview == "x" * 200 + "...[truncated]"
    assert len(preview) == 214  # 200 base chars + len("...[truncated]")


@patch("todoist_mcp.client.TodoistAPI")
def test_search_tasks_short_description_not_truncated(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.filter_tasks.return_value = iter([[_fake_task(description="short note")]])

    client = TodoistClient(token="t")
    result = client.search_tasks("today")

    assert result["tasks"][0]["description_preview"] == "short note"


@patch("todoist_mcp.client.TodoistAPI")
def test_search_tasks_truncated_true_when_second_page_exists(mock_api_cls: MagicMock) -> None:
    # limit=2, first page has 2 tasks, second page has more → truncated=True
    mock_api = mock_api_cls.return_value
    page1 = [_fake_task(id="t1"), _fake_task(id="t2")]
    page2 = [_fake_task(id="t3")]
    mock_api.filter_tasks.return_value = iter([page1, page2])

    client = TodoistClient(token="t")
    result = client.search_tasks("today", limit=2)

    assert result["count"] == 2
    assert result["truncated"] is True


@patch("todoist_mcp.client.TodoistAPI")
def test_search_tasks_truncated_false_when_first_page_short(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    # limit=10, first page has 3 → no need to peek, not truncated
    mock_api.filter_tasks.return_value = iter([[_fake_task(), _fake_task(), _fake_task()]])

    client = TodoistClient(token="t")
    result = client.search_tasks("today", limit=10)

    assert result["count"] == 3
    assert result["truncated"] is False


@patch("todoist_mcp.client.TodoistAPI")
def test_search_tasks_bad_filter_returns_invalid_filter_dict(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.filter_tasks.side_effect = _http_error(400, "unparseable filter")

    client = TodoistClient(token="t")
    result = client.search_tasks("### garbage ###")

    assert result == {
        "error": "invalid filter",
        "filter": "### garbage ###",
        "hint": "unparseable filter",
    }


@patch("todoist_mcp.client.TodoistAPI")
def test_search_tasks_rate_limit_uses_generic_error_shape(mock_api_cls: MagicMock) -> None:
    mock_api = mock_api_cls.return_value
    mock_api.filter_tasks.side_effect = _http_error(
        429, "too many", headers={"Retry-After": "30"}
    )

    client = TodoistClient(token="t")
    result = client.search_tasks("today")

    # 429 should NOT be remapped to the filter-parse shape
    assert result["code"] == 429
    assert result["retry_after"] == 30
    assert result["retryable"] is True
