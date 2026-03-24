# TRIGGER-DEV-BUILD — Trigger.dev Implementation Workflow

Trigger.dev automations use TypeScript task wrappers that call Python scripts via `python.runScript()`. Code lives in the client's automations folder.

## Design Principles

- Use `schemaTask` with Zod validation for typed, validated payloads
- Break complex workflows into subtasks for independent retry/idempotency, but avoid over-splitting — use `Promise.allSettled` for parallel work within a single task to save costs (each subtask gets its own process, billed per-ms)
- Always configure `retry` (maxAttempts, delay, backoff) — don't over-retry
- Use `triggerAndWait`/`batchTriggerAndWait` only when parent needs child results; otherwise use `trigger`/`batchTrigger`
- Pass `idempotencyKey` when triggering from inside tasks to prevent duplicate work on retries
- Use `logger` at key execution points for visibility
- Group single-use subtasks in the same file as the parent; don't export them
- Never wrap `triggerAndWait`/`batchTriggerAndWait` in `Promise.all` — not supported

---

## Folder Structure

```
workspace/clients/{client}/automations/
├── src/trigger/
│   └── {task-id}.ts          ← TypeScript task wrapper
├── python/
│   ├── automations/
│   │   └── {name}.py         ← Python automation class
│   └── workspace/clients/
│       └── {service}/
│           └── client.py     ← API client
├── trigger.config.ts          ← Build config
├── package.json
└── requirements.txt
```

---

## Step 1: Determine Task Type

Reference: `.claude/rules/trigger-dev/basic-tasks.md`

| Trigger | Use |
|---------|-----|
| Cron/Schedule | `schedules.task()` with `cron` property |
| Webhook/Event | `task()` — called by external system |
| Manual/One-off | `task()` — called by user or another task |
| AI-powered | `task()` + AI SDK inside Python — invoke `trigger-agents` skill |

**For scheduled tasks**, reference `.claude/rules/trigger-dev/scheduled-tasks.md`.

---

## Step 2: Check Dependencies

For each system in the spec:

```bash
ls workspace/clients/{client}/automations/python/clients/{system}/
```

If the client doesn't exist → suggest `/api-boilerplate` for that service, then continue with a stub.

---

## Step 3: Write Python Automation Class

Create `workspace/clients/{client}/automations/python/automations/{name}.py`:

```python
"""
Automation {ID}: {Name}

Spec: specs/{stage}/{id}.md
Trigger: {trigger_type}

{Brief description from spec Goal section}
"""
import json
import sys
import logging
from typing import Any

# Configure logging to stderr (Trigger.dev captures this)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)


class {AutomationClass}:
    """
    {Description}

    Flow:
    {Key steps from spec Mermaid diagram}
    """

    automation_id = "{id}"

    def __init__(self, {params}):
        self.{param} = {param}
        self.{client} = None

    def initialize(self) -> None:
        """Initialize API clients and validate config."""
        logger.info(f"Initializing {self.automation_id}")
        # import and instantiate clients

    def fetch_data(self) -> Any:
        """Fetch data from source systems (Step 2 from spec)."""
        pass

    def transform(self, data: Any) -> Any:
        """Transform data for destination (Step 3 from spec)."""
        pass

    def execute(self, data: Any) -> Any:
        """Execute main logic (Step 4 from spec)."""
        pass

    def finalize(self, result: Any) -> None:
        """Cleanup and notifications (Step 5 from spec)."""
        pass

    def run(self, dry_run: bool = False) -> dict:
        self.initialize()
        data = self.fetch_data()
        transformed = self.transform(data)
        if dry_run:
            return {"dry_run": True, "would_process": len(transformed) if isinstance(transformed, list) else 1}
        result = self.execute(transformed)
        self.finalize(result)
        return {"success": True, "processed": len(result) if isinstance(result, list) else 1}


if __name__ == "__main__":
    payload = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    automation = {AutomationClass}(**payload)
    result = automation.run()
    print(json.dumps(result))  # stdout → Trigger.dev captures as task output
```

**Key patterns:**
- Log to `stderr` (Trigger.dev captures for UI display)
- Print final result to `stdout` as JSON (Trigger.dev captures as task output)
- Support `dry_run=True` for safe testing

---

## Step 4: Write TypeScript Task Wrapper

Create `workspace/clients/{client}/automations/src/trigger/{task-id}.ts`:

**For webhook/event tasks:**
```typescript
import { task } from "@trigger.dev/sdk";
import { python } from "@trigger.dev/python";

export const {taskName} = task({
  id: "{automation-id}",
  retry: { maxAttempts: 3 },
  run: async (payload: Record<string, unknown>) => {
    const result = await python.runScript(
      "./python/automations/{name}.py",
      [JSON.stringify(payload)]
    );
    return JSON.parse(result.stdout);
  },
});
```

**For scheduled tasks:**
```typescript
import { schedules } from "@trigger.dev/sdk";
import { python } from "@trigger.dev/python";

export const {taskName} = schedules.task({
  id: "{automation-id}",
  cron: "{cron_expression}",   // e.g. "0 8 * * *" = 8am UTC daily
  run: async (payload) => {
    const result = await python.runScript(
      "./python/automations/{name}.py",
      [JSON.stringify({ scheduled: true, timestamp: payload.timestamp.toISOString() })]
    );
    return JSON.parse(result.stdout);
  },
});
```

Reference: `.claude/rules/trigger-dev/scheduled-tasks.md` for cron syntax.

---

## Step 5: AI Agent Tasks (invoke `trigger-agents` skill)

If the automation uses LLMs or AI:
- Invoke the `trigger-agents` skill for orchestration, parallelization, routing, or human-in-the-loop patterns
- Common patterns: multi-step LLM chain, parallel AI workers, evaluator-optimizer

---

## Step 6: Advanced Patterns

Reference: `.claude/rules/trigger-dev/advanced-tasks.md`

| Need | Pattern |
|------|---------|
| Process many items | `batchTriggerAndWait` (up to 1,000) |
| Prevent duplicate runs | `idempotencyKeys.create()` |
| Consolidate rapid triggers | `debounce: { key, delay }` |
| Limit concurrency | `queue: { concurrencyLimit: N }` |
| Track progress | `metadata.set('progress', N)` |
| Heavy compute | `machine: { preset: 'large-2x' }` |

**Never** wrap `triggerAndWait` or `wait.*` in `Promise.all` — not supported.

---

## Step 7: Update trigger.config.ts (invoke `trigger-config` skill)

If the automation needs build extensions (Python, Prisma, Playwright, FFmpeg, etc.):

```typescript
import { pythonExtension } from "@trigger.dev/build/extensions/python";

extensions: [
  pythonExtension({
    scripts: ["./python/**/*.py"],
    requirementsFile: "./requirements.txt",
    devPythonBinaryPath: ".venv/bin/python",
  }),
]
```

Invoke `trigger-config` skill for full extension configuration guidance.

---

## Step 8: Write Tests

Create `workspace/clients/{client}/automations/tests/test_{name}.py`:

```python
"""Tests for {AutomationClass}"""
import pytest
from python.automations.{name} import {AutomationClass}

def test_transform_basic():
    """Basic transformation produces correct output."""
    automation = {AutomationClass}()
    result = automation.transform([{...}])
    assert result == [{...}]

def test_dry_run():
    """Dry-run completes without side effects."""
    automation = {AutomationClass}()
    result = automation.run(dry_run=True)
    assert result["dry_run"] is True
    assert result["would_process"] >= 0
```

Run: `uv run pytest tests/test_{name}.py -v`

---

## Step 9: Realtime Monitoring (invoke `trigger-realtime` skill)

If the client needs a frontend progress indicator or streaming output:
- Invoke `trigger-realtime` skill for React hooks, public tokens, and stream setup
- Key hooks: `useRealtimeRun`, `useRealtimeTaskTrigger`, `useRealtimeStream`

Reference: `.claude/rules/trigger-dev/realtime.md`
