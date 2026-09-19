# task-manager-mcp

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Local stdio MCP server exposing Todoist operations to Claude (Code, Desktop, or
any MCP client). 8 tools covering the read/write surface a real workflow needs,
including the native filter syntax that powers Todoist's own filter views.

> **Naming note:** the repo is `task-manager-mcp` even though it wraps Todoist —
> see the deployment note in *Why this exists* below. Internally the Python
> package is still `todoist-mcp`; only the public-artifact name was changed.

## Why this exists

Zapier's MCP integration caps at 100 tasks/month and wraps Todoist with tools
too narrow for real workflows — its `filter` parameter accepts only a handful
of presets, so anything ad-hoc has to fall through to raw `API Request (Beta)`
calls. In one month of usage, **87 of 102 invocations were raw API calls** for
queries Zapier couldn't express natively.

This server replaces that with eight purpose-built tools, exposes Todoist's
full filter language to the LLM, and runs locally — no cap, no Zapier
quota, no token in the client config.

### A real-world deployment note

The repo is named `task-manager-mcp` rather than `todoist-mcp` for a non-obvious
reason. When this server is installed as a Claude Desktop / Cowork extension,
Cowork's plugin runtime puts the spawned MCP process inside an Operon network
sandbox with a managed HTTPS MITM proxy. The proxy pattern-matches on plugin
identity: any plugin whose manifest advertises "Todoist" gets hijacked into
Cowork's built-in Todoist connector spec — which expects an OAuth flow our
static-token MCP doesn't speak. Tools list got replaced with phantom names
(`todoist_get_comments`, `todoist_move_task`) that don't exist in our code, and
every actual call returned 401.

The fix was to strip "Todoist" from the manifest's `name` and `display_name`
fields. The actual tool names (`todoist_search_tasks`, `todoist_list_labels`,
etc.) stay the same — only the plugin's outer identity changes. Worth
knowing if you're shipping any Todoist-adjacent MCP into Cowork, or any
similarly-sandboxed runtime with managed connector OAuth.

## Install

```bash
git clone https://github.com/ksdisch/task-manager-mcp.git
cd task-manager-mcp
cp .env.example .env       # then paste your TODOIST_API_TOKEN
uv sync
uv run todoist-mcp         # smoke test — Ctrl-C to exit
```

Get a Todoist API token at <https://app.todoist.com/app/settings/integrations/developer>.

### Register with Claude Code

```bash
claude mcp add todoist -- uv --directory "$(pwd)" run todoist-mcp
```

### Register with Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/todoist-mcp", "run", "todoist-mcp"]
    }
  }
}
```

The token lives in the server's own `.env` — never in client configs.
Rotating the token is a single-line edit; both clients pick it up on restart.

## Tools

| Tool | Signature | Purpose |
|---|---|---|
| `todoist_list_projects` | `()` | List every project. Returns `id, name, parent_id`. |
| `todoist_create_task` | `(content, project_id?, section_id?, labels?, priority?, due_string?, description?, parent_id?)` | Create a task. Natural-language `due_string`. |
| `todoist_update_task` | `(task_id, **any_field)` | Update any subset of fields. Auto-detects project/section/parent moves. |
| `todoist_get_task` | `(task_id)` | Fetch one task by id with its full, untruncated description (read-only). |
| `todoist_complete_task` | `(task_id)` | Mark complete. |
| `todoist_search_tasks` | `(filter, limit=50)` | Native filter-syntax search (see Cookbook). Cap 200, default 50. |
| `todoist_list_labels` | `()` | List every label. Returns `id, name, color, is_favorite`. |
| `todoist_list_sections` | `(project_id)` | List sections in a project. Returns `id, name, project_id, order`. |
| `todoist_create_project` | `(name, parent_id?, color?)` | Create a project. |

All write tools return the created/updated object so the LLM can verify
without a second read. HTTP errors are caught and returned as
`{"error": ..., "code": ..., "message": ...}` — never raised into the MCP
layer. Rate-limit (429) responses include `retry_after`.

## Filter Syntax Cookbook

`todoist_search_tasks(filter, limit=50)` accepts Todoist's native filter
language — the same one that powers filter views in the Todoist UI.

Full reference: <https://todoist.com/help/articles/introduction-to-filters-V98wIH>

### Recipes that cover 90% of real usage

| Goal | Filter |
|---|---|
| Everything I'm waiting on someone else for | `@waiting-on` |
| Priority-1 tasks due today | `p1 & today` |
| Inbox items that still need a date | `#Inbox & no date` |
| Everything past its due date | `overdue` |
| The next week's work, minus anything parked on someone else | `7 days & !@waiting-on` |

### Operators quick reference

- `&` — AND  ·  `|` — OR  ·  `!` — NOT
- `@label` — tasks with a label
- `#Project` — tasks in a project (name, not id)
- `p1` / `p2` / `p3` / `p4` — priority (p1 = urgent)
- `today` / `tomorrow` / `7 days` / `no date` / `overdue` — date helpers

### Response shape

```json
{
  "tasks": [
    {
      "id": "...",
      "content": "...",
      "project_id": "...",
      "labels": ["..."],
      "priority": 1,
      "due": {"date": "...", "string": "...", "is_recurring": false, "timezone": null},
      "description_preview": "first 200 chars...[truncated]"
    }
  ],
  "count": 1,
  "truncated": false
}
```

`truncated: true` means there are more matches than `limit` — raise the limit
(cap 200) or refine the filter. Descriptions are capped at 200 chars with a
`...[truncated]` suffix.

### Bad filters

Todoist returns 400 for unparseable filters. The wrapper surfaces that as:

```json
{"error": "invalid filter", "filter": "<your input>", "hint": "<api message>"}
```

— never raises into the MCP layer.

## Development

Common loops via `just`:

```bash
just install   # uv sync (incl. dev deps)
just test      # pytest
just lint      # ruff check
just check     # test + lint
just run       # uv run todoist-mcp (stdio server)
```

Or directly: `uv sync`, `uv run pytest`, `uv run ruff check .`, `uv run todoist-mcp`.

## License

MIT — see [LICENSE](LICENSE).
