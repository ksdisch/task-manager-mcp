# todoist-mcp

Local stdio MCP server exposing Todoist operations. A personal Zapier replacement
that drops the 100-task/mo cap and exposes Todoist's native filter syntax to Claude.

> Status: Phase 3 of 4 — read/write tools + search with native filter syntax.
> Full install guide, badges, and P1 tools land in Phase 4. See `PROJECT_SPEC.md`
> for the full plan.

## Filter Syntax Cookbook

`todoist_search_tasks(filter, limit=50)` accepts Todoist's native filter
language — the same one that powers filter views in the Todoist UI. This is
the tool that replaces the raw `API Request (Beta)` calls a Zapier integration
can't express.

Full reference:
<https://todoist.com/help/articles/introduction-to-filters-V98wIH>

### Recipes that cover 90% of real usage

| Goal | Filter |
|---|---|
| Everything I'm waiting on someone else for | `@waiting-response` |
| Priority-1 tasks due today | `p1 & today` |
| Inbox items that still need a date | `#Inbox & no date` |
| Everything past its due date | `overdue` |
| The next week's work, minus anything parked on someone else | `7 days & !@waiting-response` |

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
`...[truncated]` suffix; call `todoist_update_task` / fetch the full task if
you need the untruncated body.

### Bad filters

Todoist returns 400 for unparseable filters. The wrapper surfaces that as:

```json
{"error": "invalid filter", "filter": "<your input>", "hint": "<api message>"}
```

— never raises into the MCP layer.
