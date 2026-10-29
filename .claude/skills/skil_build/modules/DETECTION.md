# Orchestrator Detection

Detect before building. Default for new clients: n8n.

```bash
uv run tools/infra_yaml.py --client {client}   # prints orchestrator=... (and deploy=... when set)
```

The loader resolves in this order, first hit wins:

| Order | Check | Orchestrator |
|-------|-------|-------------|
| 1 | top-level `orchestrator:` in infrastructure.yaml | as written |
| 2 | an instance with `type: n8n` / `make` / `trigger-dev` / `fastapi` | that type |
| 3 | `trigger.config.ts` in automations/ | Trigger.dev |
| 4 | `railway.toml` in automations/ | FastAPI (legacy) |

`.mcp.json` is not a detection source: it is gitignored, so a worktree has none, and it only says which credentials are wired on this machine. A top-level `deploy:` names the one sanctioned deploy entry point and outranks the orchestrator's default lane (Brisken: FastAPI on Fly through `deploy.py`, never `railway up`).

**n8n:** Visual workflows via n8n MCP tools. No code deployment. **Make.com:** Visual scenarios via Make.com MCP tools or UI. **Trigger.dev:** Code-first TypeScript + Python. Deploy via `npx trigger.dev deploy`. **FastAPI:** Legacy only — do not use for new clients.
