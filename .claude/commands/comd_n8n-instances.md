---
description: Manage per-client n8n MCP server instances
argument-hint: [list | add <client> | remove <client>]
---

Per-client MCP servers are rendered into the gitignored `.mcp.json` by `tools/mcp_config.py`; nothing edits that file by hand. The sources are the client's tracked `infrastructure.yaml` (instance `mcp_server`, `api_url_env`, `api_key_env`) and its gitignored `workspace/clients/{client}/context/.env` (the values). Machine-only servers (a Make MCP URL, the CDP port, vercel) live in `.mcp.local.json` at the primary clone root, each optionally tagged `"_scope": ["{client}" | "platform"]`.

## What to do for `$ARGUMENTS`

**list**: `uv run tools/mcp_config.py --check`. It names servers added, removed and changed for this checkout; values never print.

**add {client}**:
1. In `workspace/clients/{client}/infrastructure.yaml`, give the n8n instance `mcp_server: n8n-{client}`, `api_url_env: N8N_API_URL_{CLIENT}` and `api_key_env: N8N_API_KEY_{CLIENT}` (names only, never values; this file is tracked).
2. Put the two values in `workspace/clients/{client}/context/.env` under those names. Ask the user for the API URL and key only if they are not already in that `.env` or the vault.
3. Add the two names to the client's `automations/.env.example`.
4. `uv run tools/mcp_config.py --ensure`. A missing variable skips the server and names it.

**remove {client}**: delete the `mcp_server`/`api_*_env` lines from the instance (or the instance), then `--ensure`.

`--ensure` writes only when the render changed, keeps the previous file in `.scratch/`, and prints "restart Claude Code to load" when it did. Restart is the only manual step.

## Scope

- **Primary clone**: the union of every client's servers plus every local entry, so no running session loses one.
- **Worktree**: only the session's client (branch `client/{client}/...`, or `--client {client}`), and `vercel` only for `platform/` and `proposal/` branches. A Brisken worktree carries no Make server.
- SessionStart runs `--ensure --hook`, and a `git worktree add` renders the new worktree; `/comd_resume` Step 0 runs `--check`.
- First time on a machine with a hand-written `.mcp.json`: `uv run tools/mcp_config.py --adopt` seeds `.mcp.local.json` from it. `--ensure` refuses until then, because rendering first would drop those servers.

The base `n8n-mcp` docs-only server is a local entry, not a client instance; keep it there.
