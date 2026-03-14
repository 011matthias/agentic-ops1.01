# Orchestrator Detection

Detect before building. Default for new clients: Trigger.dev.

| Check | Orchestrator |
|-------|-------------|
| `trigger.config.ts` in automations/ | Trigger.dev |
| `.mcp.json` entry `n8n-{client}` | n8n |
| `infrastructure.yaml` with `type: make` | Make.com |
| `railway.toml` in automations/ | FastAPI (legacy) |

```bash
if [ -f workspace/clients/{client}/automations/trigger.config.ts ]; then echo "trigger-dev"
elif grep -q "n8n-{client}" .mcp.json 2>/dev/null; then echo "n8n"
elif grep -q "type: make" workspace/clients/{client}/infrastructure.yaml 2>/dev/null; then echo "make"
elif [ -f workspace/clients/{client}/automations/railway.toml ]; then echo "fastapi"
fi
```

**n8n:** Visual workflows via n8n MCP tools. No code deployment. **Make.com:** Visual scenarios via Make.com MCP tools or UI. **Trigger.dev:** Code-first TypeScript + Python. Deploy via `npx trigger.dev deploy`. **FastAPI:** Legacy only — do not use for new clients.
