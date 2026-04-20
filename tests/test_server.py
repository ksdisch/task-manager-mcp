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


def test_tool_is_registered_with_fastmcp() -> None:
    tool_names = {t.name for t in server.mcp._tool_manager.list_tools()}
    assert "todoist_list_projects" in tool_names
