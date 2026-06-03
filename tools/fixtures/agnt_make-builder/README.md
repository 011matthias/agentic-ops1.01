# Test fixtures for agnt_make-builder

Persistent, reproducible fixtures for smoke-testing the Make.com builder agent. Two specs that exercise the agent's two distinct output shapes:

1. **`spec-blocked-no-trigger.md`** — spec frontmatter missing `trigger` field. Expected behavior: agent emits `## Build BLOCKED — fx1: ...` shape after Step 1 fail-fast, citing the missing trigger. Validates the BLOCKED shape on spec validation failure.
2. **`spec-blocked-ops.md`** — spec is structurally well-formed but the projected ops would catastrophically exceed the fixture plan's limit (cron every 5 seconds × 6 modules × 31 days = ~3.2M ops/month vs 10k plan). Expected behavior: agent passes Step 1 spec validation, resolves the fixture instance, then BLOCKs on Gate G1 (ops estimation) with the math shown. Validates the BLOCKED shape on a pre-build gate failure.

## How to smoke-test

The agent expects to read `workspace/clients/{client}/infrastructure.yaml`. The fixtures use `client: _fixture-make-builder` and the fixture infrastructure.yaml lives in this directory (`infrastructure.yaml`). To run the smoke test, invoke the agent with one of:

```
client: _fixture-make-builder
automation_id: fx1                                    # for spec-blocked-no-trigger
spec_path: tools/fixtures/agnt_make-builder/spec-blocked-no-trigger.md
mode: build
fixture_infrastructure_yaml: tools/fixtures/agnt_make-builder/infrastructure.yaml
```

The agent's Step 2 reads infrastructure.yaml from `workspace/clients/{client}/`; for smoke-tests, the invoker either (a) points the agent at the fixture's `infrastructure.yaml` explicitly, or (b) treats the BLOCK on "infrastructure.yaml not found" as part of the test surface (validates the missing-instance BLOCK shape).

## What "green" means

- BLOCKED shape: first line is `## Build BLOCKED — {automation_id}: {name}`, `**Status:** BLOCKED`, `**Blocking gate:** {gate}`, `**Blocker:** {sentence}`, `### What's needed to unblock` section present, `### Gotchas applied (sourced)` includes the relevant register entry.
- No preamble before the `##` header.
- Agent did NOT write a blueprint file (no `workspace/clients/_fixture-make-builder/automations/blueprints/*.json` created — BLOCKs happen before Step 4).
- Agent did NOT call `make-api.py` or any scenarios MCP tool (BLOCKs happen before Step 6).

## What "red" means

- Preamble before the `##` header ("Let me check this spec first...").
- Wrong section names or missing sections.
- Agent wrote a blueprint file despite BLOCKing — means gates were skipped.
- Agent called scenarios_update or make-api.py — means it tried to deploy despite a pre-build BLOCK.
- Gate citation missing or wrong register entry referenced.

## Adding a clean-pass fixture

A "BUILT" smoke-test fixture (one that exercises the full report shape) requires a real Make MCP server connection or a willingness to actually deploy a no-op scenario. Not included in v1 because the value-per-cost is low (real deploys cost ops; mocked MCP would let the test drift from reality). Add later if the BLOCKED-shape tests prove insufficient.
