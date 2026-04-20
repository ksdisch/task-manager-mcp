from unittest.mock import MagicMock, patch

from todoist_mcp import server


def test_todoist_list_projects_tool_returns_client_output() -> None:
    expected = [{"id": "1", "name": "Inbox", "parent_id": None}]
    fake_client = MagicMock()
    fake_client.list_projects.return_value = expected

    with patch.object(server, "_client", fake_client):
        result = server.todoist_list_projects()

    assert result == expected
    fake_client.list_projects.assert_called_once_with()


def test_create_task_tool_forwards_all_kwargs_as_keywords() -> None:
    fake_client = MagicMock()
    fake_client.create_task.return_value = {"id": "new"}

    with patch.object(server, "_client", fake_client):
        result = server.todoist_create_task(
            content="Task",
            project_id="p",
            section_id="s",
            labels=["home"],
            priority=2,
            due_string="today",
            description="desc",
            parent_id="tp",
        )

    assert result == {"id": "new"}
    fake_client.create_task.assert_called_once_with(
        content="Task",
        project_id="p",
        section_id="s",
        parent_id="tp",
        labels=["home"],
        priority=2,
        due_string="today",
        description="desc",
    )


def test_update_task_tool_filters_none_fields() -> None:
    fake_client = MagicMock()
    fake_client.update_task.return_value = {"id": "t1"}

    with patch.object(server, "_client", fake_client):
        result = server.todoist_update_task(task_id="t1", content="New", priority=3)

    assert result == {"id": "t1"}
    # None fields must be filtered out — not passed to the client
    fake_client.update_task.assert_called_once_with("t1", content="New", priority=3)


def test_complete_task_tool_forwards_task_id() -> None:
    fake_client = MagicMock()
    fake_client.complete_task.return_value = {"completed": True, "task_id": "t1"}

    with patch.object(server, "_client", fake_client):
        result = server.todoist_complete_task("t1")

    assert result == {"completed": True, "task_id": "t1"}
    fake_client.complete_task.assert_called_once_with("t1")


def test_all_phase2_tools_registered_with_fastmcp() -> None:
    tool_names = {t.name for t in server.mcp._tool_manager.list_tools()}
    assert {
        "todoist_list_projects",
        "todoist_create_task",
        "todoist_update_task",
        "todoist_complete_task",
    }.issubset(tool_names)
