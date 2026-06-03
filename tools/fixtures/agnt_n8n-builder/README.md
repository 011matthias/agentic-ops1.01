# Test fixtures for agnt_n8n-builder

Persistent, reproducible fixtures for smoke-testing the n8n workflow builder. Mirrors the agnt_make-builder fixture pattern. Two specs that exercise the agent's two distinct output shapes:

1. **`spec-blocked-code-sandbox.md`** — well-formed spec, but the planned Code node contains `fetch()` calls (banned by the n8n Cloud sandbox). Expected behavior: agent passes Step 1 spec validation and Step 2 instance resolution, then BLOCKs on Gate N3 (Code-node sandbox restrictions) with a verbatim quote of the offending line. Cites register #35 and #37.
2. **`spec-blocked-typeversion.md`** — well-formed spec, planned workflow uses `n8n-nodes-base.splitInBatches` at typeVersion 1 (which never fires `done` output[1] per register #39). Expected behavior: agent passes Step 1 + Step 2 + Gates N1, then BLOCKs on Gate N2 with the node name, the bad typeVersion, the required typeVersion, and the cited register entry.

## How to smoke-test

The agent expects to read `workspace/clients/{client}/infrastructure.yaml`. The fixtures use `client: _fixture-n8n-builder` and a fixture infrastructure.yaml lives in this directory. To run, invoke the agent with:

```
client: _fixture-n8n-builder
automation_id: nx1                                       # for spec-blocked-code-sandbox
spec_path: tools/fixtures/agnt_n8n-builder/spec-blocked-code-sandbox.md
mode: build
fixture_infrastructure_yaml: tools/fixtures/agnt_n8n-builder/infrastructure.yaml
```

## What "green" means

- BLOCKED shape: first line is `## Build BLOCKED — {automation_id}: {name}`.
- `**Status:** BLOCKED`, `**Blocking gate:** {N1 | N2 | ...}`, `**Blocker:** {sentence}`.
- `### What's needed to unblock` present, names a concrete file/value to change.
- `### Gotchas applied (sourced)` cites the relevant register entry (#35, #37, #39 as applicable).
- No preamble before the `##` header.
- Agent did NOT call `n8n_create_workflow` (BLOCKs happen before Step 4).
- Agent did NOT write a workflow JSON file (BLOCKs happen before Step 6).

## What "red" means

- Preamble before the `##` header.
- Wrong gate label (e.g., emits N1 for a banned-HTTP issue).
- Quotes a non-existent offending fragment (must verbatim-quote from the spec body).
- Agent called n8n MCP tools to actually deploy despite a pre-build BLOCK.
- Register citation missing or wrong.

## Adding a clean-pass fixture

A full happy-path "BUILT" smoke-test requires a real n8n MCP server with valid API credentials, which would actually deploy a workflow to a client account. Not included in v1 — same trade-off as the agnt_make-builder fixture set. The two BLOCKED-shape tests are sufficient to validate the output contract; the BUILT shape will be exercised on the first real n8n build the orchestrator routes through.
