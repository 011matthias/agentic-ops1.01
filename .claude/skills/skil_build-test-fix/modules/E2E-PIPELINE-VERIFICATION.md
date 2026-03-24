# E2E Pipeline Verification

> When to use: Any time a client has 2+ scenarios/workflows that form a pipeline (output of one triggers or feeds the next).

Component tests prove each scenario works in isolation. E2E tests prove the **integration assumptions** are correct. These are different concerns.

---

## Step 0: Verify the External Entry Point

Before mapping the internal pipeline, identify and verify the ACTUAL user-facing trigger. This step catches entry point mismatches that component tests cannot detect.

### 1. Identify the Real Entry Point

| Source Type | How to Discover | Verification Method |
|-------------|----------------|---------------------|
| Website form | `WebFetch` the page, inspect form `action` URL or JS POST target | Compare URL against pipeline's first webhook |
| CRM / SaaS webhook | Check the provider's outbound webhook settings | Compare configured URL against pipeline |
| Database polling | Confirm which table/query the poller reads | Verify the poller scenario exists and is active |
| Manual trigger | N/A — user triggers directly | Verify the correct scenario is triggered |

### 2. Compare Against Pipeline Expectation

The entry point MUST feed into the first scenario in the pipeline:

```
Expected: Source → A0 (gateway/poller) → A1 → A2 → ...
Actual:   Source → ???
```

If the source posts directly to a mid-pipeline scenario (e.g., website → A1 instead of website → DB → A0 → A1), the pipeline has an **entry point bypass**. This is a design bug — the gateway scenario is being skipped entirely.

### 3. Entry Point Bypass Resolution

| Situation | Fix |
|-----------|-----|
| Source posts to mid-pipeline scenario, gateway exists | Reconfigure source to use the gateway, or remove the gateway if unnecessary |
| Source posts to BOTH gateway and mid-pipeline | Remove the duplicate POST (Parallel Trigger — see below) |
| No gateway exists, source goes direct to first worker | Verify this is intentional per spec; document the decision |

### 4. When to Run This Step

- **Always** at the start of any E2E test plan, before component testing
- **Always** when a new external integration is added (new form, new CRM, new webhook source)
- **After deployment** when the entry point involves external systems you don't control

---

## Pre-Test: Map the Pipeline

Before running ANY E2E test:

### 1. List All Scenarios in the Pipeline

From the spec folder or `infrastructure.yaml`, enumerate every scenario that participates in the data flow.

### 2. Document Trigger Mechanism Between Each Pair

For each pair of adjacent scenarios (N → N+1):

| Question | Answer |
|----------|--------|
| How does N trigger N+1? | webhook / data store cursor / scheduler / direct call |
| What is the handoff data? | Which fields pass from N to N+1? |
| Is the trigger **exclusive**? | Can N+1 be triggered by anything OTHER than N? |

### 3. Verify Trigger Exclusivity

This is the critical step most often skipped. Check whether the downstream scenario can be triggered from **multiple sources**:

- For webhooks: compare the webhook URL in N+1 against ALL URLs registered in external systems (website forms, CRMs, other scenarios)
- For data store cursors: check if multiple scenarios read the same cursor
- For schedulers: check if timing overlaps create race conditions

---

## Anti-Pattern: Parallel Trigger (Double-Send Risk)

If an external system (website, CRM, form) sends webhooks to MULTIPLE scenarios in the pipeline:

```
Source → A (correct path via pipeline)
Source → B (bypasses A, creates double-processing)
```

**Detection:** Compare webhook URLs registered in the external system against webhook URLs in each scenario's gateway module. If the same source posts to multiple pipeline stages, the pipeline has a parallel trigger bug.

**Resolution options:**
1. Remove the direct webhook from the downstream scenario (route everything through the pipeline)
2. Add deduplication logic (check if lead already processed before acting)
3. Redesign: make the direct webhook the canonical path and remove the polling/upstream scenario

---

## E2E Test Procedure

### 1. Start from the SOURCE

Trigger from the actual user-facing entry point — not mid-pipeline:

| If the pipeline starts with... | Trigger by... |
|-------------------------------|---------------|
| Website form → MySQL → Poller | Submit the form (or insert a test row in MySQL) |
| Webhook from external system | POST to the webhook URL the external system uses |
| Scheduled poll | Wait for the schedule (or trigger manually with `scenarios_run`) |

**Never** trigger a downstream scenario directly (e.g., curl to A1) when testing the full pipeline — that bypasses integration seams.

### 2. Wait for Full Pipeline Completion

Monitor all scenarios in the pipeline. Use `executions_list` on each scenario to confirm execution occurred.

### 3. Verify at the DESTINATION

Check the final output (sheet row, email sent, notification delivered, record created) — not intermediate state.

### 4. Verify Intermediate States

Walk backward through the pipeline checking each handoff point:
- Data store records at each stage
- Cursor values advanced correctly
- Sheet columns populated at each step
- No duplicate records (parallel trigger check)

---

## Integration

- **Step 0** should run at the START of any E2E test plan — before component testing begins
- **OUTCOME-VERIFICATION.md** handles single-scenario verification — use it at each pipeline stage
- **This module** handles multi-scenario pipeline verification — the integration seams between stages
- Load this module whenever the spec folder contains 2+ scenarios with data dependencies
- If `WebFetch` is available, use it to verify website form targets autonomously (see `behaviors.md` autonomous-first diagnostics)
