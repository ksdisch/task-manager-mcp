# todoist-mcp — Personal Todoist MCP Server

**Status:** Plan / pre-build
**Repo:** `~/Cowork/mcp-servers/todoist-mcp/` (currently empty)
**Owner:** Kyle
**Target:** v0.1.0 — 8 tools, portfolio-grade repo, full Cowork skill cutover

> This file is the canonical spec. On approval, a copy will be placed in the repo (likely as `PROJECT_SPEC.md` or folded into `README.md` + CLAUDE.md) so future Claude Code sessions can reference it without leaving the project.

---

## 1. Context — Why build this

**Problem.** Zapier MCP is capped at 100 plan tasks/month. Current usage sits at **102 (over cap)**. Of those, **87 were raw `API Request (Beta)` calls** — meaning Zapier's wrapped tools are too narrow for the real workflows (filtered searches, multi-field updates). A local MCP server with a usage-driven tool surface replaces Zapier entirely, unblocks Cowork Desktop + Claude Code, and lands a portfolio-ready artifact in a currently hot category (MCP servers).

**Done looks like:**
- Local MCP server runs via `uv run todoist-mcp` with zero errors on cold start.
- All 8 P0/P1 tools callable from both Claude Code and Cowork Desktop.
- Existing Cowork skills work after swapping tool names (list in §7).
- API token lives in one file; rotation is a single edit.
- README + clean commit history so the repo is portfolio-presentable.
- Zapier's Todoist tools can be disabled without breaking any workflow.

---

## 2. Tool Surface (Final)

| # | Tool | Priority | Signature |
|---|------|----------|-----------|
| 1 | `todoist_search_tasks` | P0 | `(filter: str, limit: int = 50)` — native filter syntax |
| 2 | `todoist_create_task` | P0 | `(content, project_id?, section_id?, labels?, priority?, due_string?, description?, parent_id?)` |
| 3 | `todoist_update_task` | P0 | `(task_id, **any_field)` — handles section moves too |
| 4 | `todoist_complete_task` | P0 | `(task_id)` |
| 5 | `todoist_list_projects` | P0 | `()` → `id, name, parent_id` |
| 6 | `todoist_list_labels` | P1 | `()` |
| 7 | `todoist_list_sections` | P1 | `(project_id)` |
| 8 | `todoist_create_project` | P1 | `(name, parent_id?, color?)` |

**P2 (ship later if needed):** `todoist_add_comment` — skipped from MVP because 0 invocations in Zapier history.

**Safety defaults:**
- `search_tasks` caps at `limit=200`, default `50`. Truncates descriptions to 200 chars in list responses.
- All write tools return the updated object so Claude can verify success without a second read.
- Rate-limit aware: catch Todoist 429s and surface a clean error (Todoist REST cap is 450 req / 15 min — plenty of headroom).

---

## 3. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Matches data stack; consistent mental model |
| MCP SDK | `mcp[cli]` (FastMCP style) | Decorator API = minimal boilerplate |
| Todoist SDK | `todoist-api-python` (official) | No hand-rolled HTTP |
| Dep mgmt | `uv` | Fast, modern, matches preference |
| Env | `python-dotenv` | Token loaded from server's own `.env` |
| Testing | `pytest` | Standard |
| Lint/format | `ruff` | Fast, single tool for both |

---

## 4. File Structure

```
~/Cowork/mcp-servers/todoist-mcp/
├── .env                      # TODOIST_API_TOKEN (gitignored)
├── .env.example              # Template committed to git
├── .gitignore
├── .python-version           # 3.11
├── README.md                 # Install + tool reference + filter syntax guide
├── pyproject.toml            # uv-managed
├── uv.lock
├── src/
│   └── todoist_mcp/
│       ├── __init__.py
│       ├── server.py         # FastMCP app + @tool decorators
│       ├── client.py         # Todoist SDK wrapper (error handling, truncation)
│       └── formatters.py     # Response shaping for LLM consumption
└── tests/
    ├── test_client.py        # Mocked
    └── test_server.py        # Mocked tool calls
```

---

## 5. Configuration & Token Rotation

**Insight:** don't store the token in Claude Desktop / Claude Code configs. Store it in the server's own `.env`, loaded via `python-dotenv` at startup. Client configs just invoke the server — no token duplication.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "todoist": {
      "command": "uv",
      "args": ["--directory", "/Users/kyledisch/Cowork/mcp-servers/todoist-mcp", "run", "todoist-mcp"]
    }
  }
}
```

> ⚠️ Path note: original spec had `/Users/kyle/...` — corrected to `/Users/kyledisch/...` to match actual `$HOME`.

**Claude Code** (one-time):
```bash
claude mcp add todoist -- uv --directory ~/Cowork/mcp-servers/todoist-mcp run todoist-mcp
```

**Rotating the token:** edit one line in `~/Cowork/mcp-servers/todoist-mcp/.env`. Done. Both clients pick it up on server restart.

---

## 6. Risks & Mitigations

| # | Risk | Mitigation |
|---|------|-----------|
| R1 | Claude crafts a bad filter, dumps 10k tasks into context | Hard cap `limit=200`, default `50`; truncate descriptions |
| R2 | Todoist REST API doesn't support some operations (e.g. attaching parent) | SDK wraps Sync API where needed; fall back to raw HTTP in `client.py` if blocked |
| R3 | `ruff` / Python version mismatch across machines | `.python-version` file + `uv sync` handles it |
| R4 | Open-sourcing later means hardcoded ACE conventions leak | Keep `server.py` generic; workflow examples live in README, not code |
| R5 | Breaking existing Cowork skills during swap | Build + test server fully before swapping skill configs; keep Zapier fallback available during transition |

---

## 7. Build Phases

Four phases. Each is a clean commit. Run sequentially — don't skip ahead.

### Phase 1 — Scaffold + first read-only tool
**Goal:** working `todoist_list_projects` callable from Claude Code. Proves end-to-end plumbing.

1. `uv init` at `~/Cowork/mcp-servers/todoist-mcp/`
2. Set up file structure (`src/todoist_mcp/`, `tests/`, etc.)
3. Deps: `mcp[cli]`, `todoist-api-python`, `python-dotenv`, `pytest`, `ruff`
4. `.env.example` (`TODOIST_API_TOKEN=`) and `.env` (Kyle pastes real token)
5. Implement ONLY `todoist_list_projects` end-to-end:
   - `client.py`: `TodoistClient` wrapper loading token from `.env`
   - `server.py`: FastMCP app with the single `@tool`
   - Returns JSON array of `{id, name, parent_id}`
6. Pytest test mocking the Todoist SDK, verifying tool output shape
7. `git init`, `.gitignore` excludes `.env`, `uv.lock` committed
8. Commit: `feat: scaffold + list_projects tool`

**Verify:** `uv run todoist-mcp` starts clean → `uv run pytest` green → `ruff check` clean → register with Claude Code and test live before Phase 2.

### Phase 2 — P0 write tools
1. `todoist_create_task` — all fields from §2
2. `todoist_update_task` — `task_id` + any subset of updatable fields as kwargs. Must handle section moves (Sync API if REST won't cut it)
3. `todoist_complete_task`
4. Each tool returns the updated/created object
5. Error handling in `client.py`: catch API errors, return `{"error": ..., "code": ...}` — never raise raw exceptions into MCP layer
6. Rate-limit handling: on 429, return retry-able error with `Retry-After`
7. Pytest covers all three tools with mocked SDK responses
8. Commit: `feat: P0 write tools (create, update, complete)`

**Verify:** existing tests pass → manual create/update/complete from Claude Code → `ruff check` clean.

### Phase 3 — Search with native filter syntax (the unlock)
Replaces the 87 raw Zapier API calls.

1. `todoist_search_tasks(filter: str, limit: int = 50)`:
   - Native Todoist filter syntax
   - Must-work examples: `@waiting-on`, `p1 & today`, `#Inbox & no date`, `overdue`, `7 days & !@waiting-on`
   - Hard cap `limit ≤ 200`, default `50`
   - Descriptions truncated to 200 chars with `...[truncated]` suffix if cut
   - Response shape: `{tasks: [{id, content, project_id, labels, priority, due, description_preview}], count, truncated: bool}`
2. Filter parse errors → `{"error": "invalid filter", "filter": <input>, "hint": "..."}` instead of crashing
3. Tests: basic filter, limit enforcement, truncation, bad filter
4. README "Filter Syntax Cookbook" — 5-6 filters Kyle actually uses (gather in chat during this phase)
5. Commit: `feat: search_tasks with native filter syntax`

**Verify:** reproduce all existing `waiting-check` / `daily-plan` queries from Claude Code → truncation works → `ruff check` clean, pytest green.

### Phase 4 — P1 tools + polish + cutover
1. Remaining P1: `todoist_list_labels`, `todoist_list_sections`, `todoist_create_project`
2. README polish:
   - Badges (Python version, license)
   - Install section (uv-based, 3 steps max)
   - Tool reference table with signatures + examples
   - Filter Syntax Cookbook (from Phase 3)
   - "Why this exists" section — the Zapier-replacement story
   - MIT license
3. `make` or `just` target for common dev loop (install, test, lint, run)
4. Verify Claude Desktop integration — provide exact JSON block for `claude_desktop_config.json`
5. Commit: `feat: P1 tools + portfolio polish`
6. Tag `v0.1.0`

**Verify:** fresh clone works with `git clone` → `cp .env.example .env` → add token → `uv sync` → `uv run todoist-mcp` → all 8 tools callable from both clients → every affected skill (§7.1) swaps cleanly.

### 7.1 Skills to update at cutover
- `todoist-sync`
- `triage-inbox`
- `waiting-check`
- `daily-plan`
- `add-task`
- `app-sync`
- `gmail-triage` (Todoist task creation)
- `evening-reflection`

Don't disable Zapier until Phase 4 verification passes. Dual-run for a week is acceptable belt-and-suspenders.

---

## 8. Out of Scope (v0.1)

- `todoist_add_comment` — 0 invocations in usage data; reconsider in v0.2 if a workflow needs it
- Webhook / push support — this is a pull-based read/write server, not reactive
- Multi-user features (Find User, Invite User, Get Collaborators) — personal account only
- Hosted / remote deployment — can add later without touching tool logic

---

## 9. Reasoning & Best Practices Baked In

- **Usage-driven tool surface** — designed from actual 102 Zapier invocations, not a theoretical wishlist. The 87 raw API calls directly informed the `search_tasks` filter-syntax decision.
- **Single source of token truth** — `.env` in server directory, not client configs. Rotation is one edit.
- **Phase-gated builds** — each phase stops and verifies before the next. Matches "fast iteration over polished first drafts" while keeping quality high.
- **Portfolio-grade from day one** — MIT license, clean README, commit hygiene. Resume artifact; MCP servers are hot with hiring managers right now.
- **Cutover safety** — don't disable Zapier until Phase 4 verification passes.

---

## 10. Skill Bumps This Project Delivers (Tier 2 DE pivot)

- **MCP protocol mechanics** — stdio transport, tool schemas, JSON-RPC flow. Increasingly relevant as MCP becomes the standard LLM integration layer.
- **`uv` in production** — currently casual usage; this project cements the workflow (lock files, Python pinning, `uv run` scripts).
- **Clean Python SDK design** — thin MCP layer over a reusable `client.py` is the same architectural pattern for wrapping Snowflake / dbt / Prefect APIs in future portfolio work.

---

## 11. Execution Notes for Future Sessions

- **This plan lives in two places** once approved: `~/.claude/plans/i-have-new-project-bright-acorn.md` (session plan) AND will be copied into the repo as `PROJECT_SPEC.md` during Phase 1 scaffolding so any Code session working in the repo can read it without leaving the project.
- **Phase prompts** (§7) are pre-written. Feed them to Claude Code one at a time — don't batch.
- **Before each phase:** `git status` clean, previous phase verified.
- **After each phase:** run verify checklist, make the commit listed, stop.
- **Token lives only in `.env`** inside the repo directory. Never paste it into a client config or commit it.
