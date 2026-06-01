---
id: nx2
name: Fixture — splitInBatches pinned to typeVersion 1
type: workflow
stage: build
orchestrator: n8n
version: 0.1.0
created: 2026-05-26
updated: 2026-05-26
trigger:
  type: webhook
  events_per_month: 200
systems:
  - webhook
  - googleSheets
last_changes:
  - 2026-05-26: created as agnt_n8n-builder smoke-test fixture (intentionally pins splitInBatches to typeVersion 1)
next_steps:
  - none (fixture, will be re-used as-is)
---

# nx2 — Fixture: splitInBatches pinned to typeVersion 1

## Goal

Synthetic spec to validate Gate N2 (typeVersion compatibility) in the agnt_n8n-builder agent. The planned workflow uses `n8n-nodes-base.splitInBatches` at `typeVersion: 1`, which per register #39 never fires the `done` output[1] — workflows that depend on the done signal silently stall. The required version is `>= 3`.

## Flow

```mermaid
graph TD
  A[Webhook trigger] --> B[Read sheet rows]
  B --> C[Split In Batches typeVersion 1]
  C -->|loop output[0]| D[Process item]
  D --> C
  C -->|done output[1] — silently never fires| E[Send summary]
```

## Step details

1. Webhook fires (~200 events/month).
2. Read all rows from a Google Sheet.
3. Split the rows into batches via `n8n-nodes-base.splitInBatches`, **explicitly pinned to `typeVersion: 1`** (per the spec author's intent, intentionally banned).
4. For each batch (output[0]), process the item.
5. After all batches are done (output[1]), send a summary — **but output[1] never fires on typeVersion 1**, so this path is dead.

Planned workflow body excerpt:
```json
{
  "nodes": [
    {
      "name": "Split In Batches",
      "type": "n8n-nodes-base.splitInBatches",
      "typeVersion": 1,
      "parameters": { "batchSize": 10 }
    }
  ]
}
```

## Expected agent behavior

- Step 1: trigger present (`webhook`, `events_per_month: 200`), systems listed → PASS.
- Step 2: resolve `_fixture-n8n-builder` instance from fixture infrastructure.yaml.
- Step 3, Gate N1: nodeType format clean (`n8n-nodes-base.splitInBatches` in body) → PASS.
- Step 3, Gate N2: scan for known-incompatible typeVersions. Finds `splitInBatches` at typeVersion 1 → BLOCK.
- Should NOT proceed to N3–N7.
- Output: `## Build BLOCKED — nx2: Fixture — splitInBatches pinned to typeVersion 1` with `**Blocking gate:** N2`, naming the node, the bad version, the required version, and citing register #39.

## Why this fixture exists

Register #39 (kunde-inc, 2026-03-04): n8n Split-In-Batches typeVersion 1 never fires `done` output[1] — the workflow loops on the batch output but never reaches the "after all items" branch. Took diagnosis time on the original incident. Gate N2 is the structural fix.
