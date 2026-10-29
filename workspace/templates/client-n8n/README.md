# {Client} automations (n8n)

Copy this folder to `workspace/clients/{client}/automations/` for a new n8n client. Layout (rule_file_placement §2):

| Path | What |
|---|---|
| `{id}-{slug}.n8n.json` | one scrubbed export per workflow, flat; the name is the workflow's `export:` in `../infrastructure.yaml` |
| `tools/` | this client's scripts; every script gets a row in `tools/README.md` |
| `tests/` | this client's tests (fixtures only in CI, never a tenant credential) |
| `.env.example` | the variable names this client needs, no values; the values live in the gitignored `../context/.env` |

Exports: `uv run tools/n8n_export.py --client {client}` writes them from live; `--check` exits 1 when repo and live differ.

MCP server: set `mcp_server`, `api_url_env`, `api_key_env` on the instance in `../infrastructure.yaml`, put the values in `../context/.env`, run `uv run tools/mcp_config.py --ensure`.

## Workflows

| Export | n8n id | Trigger | What it does |
|---|---|---|---|
