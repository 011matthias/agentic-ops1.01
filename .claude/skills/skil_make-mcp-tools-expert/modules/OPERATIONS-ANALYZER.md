# Operations Analyzer (Make.com)

> When to use: (A) At build time — estimate ops before deploying, sanity-check against client's plan. (B) Post-hoc — diagnose ops overages, identify optimization targets, recommend plan changes.

---

## Section A: Pre-Build Estimation

Run this BEFORE deploying any Make.com scenario. The goal is to catch infeasible designs before they consume real operations.

### 1. Estimation Formulas

For each scenario in the spec, estimate monthly operations:

| Trigger Type | Monthly Executions | Monthly Ops |
|-------------|-------------------|-------------|
| Scheduled (interval) | `2,592,000 / interval_seconds` | `executions × modules_in_main_flow` |
| Webhook (on-demand) | `expected_events_per_month` | `events × modules_in_main_flow` |
| Watch (polling) | Same as scheduled | Same as scheduled |

**Rules of thumb:**
- Each module in the executed path = 1 operation
- Iterator modules multiply: `items_per_batch × modules_inside_iterator`
- Router routes: only the matched route's modules count (but count the router module itself)
- Error handler modules count when errors occur
- `filter` modules that reject = 1 op (the filter itself), then flow stops

### 2. Idle Poll Cost (Critical)

Scheduled scenarios that poll for new data (A0-style pollers, A3-style step processors) still consume operations when there's nothing to process:

```
idle_ops_per_execution = modules_before_early_exit_filter + 1 (the filter itself)
idle_monthly = (2,592,000 / interval_seconds) × idle_ops_per_execution
```

If no early-exit filter exists, idle cost = full execution cost. This is the #1 source of unexpected ops burn.

### 3. Plan Tier Reference

| Plan | Ops/Month | Monthly Cost | Notes |
|------|-----------|-------------|-------|
| Free | 1,000 | $0 | 2 active scenarios max |
| Core | 10,000 | ~$10/mo | Most small clients start here |
| Pro | 10,000 | ~$18/mo | Higher transfer limits, priority execution |
| Teams | 10,000 | ~$29/mo | Team features, unlimited users |
| Enterprise | Custom | Custom | Volume pricing |

All paid plans can purchase additional ops packs. Base ops are the same (10k) across Core/Pro/Teams — the difference is features, not ops.

### 4. Feasibility Check

After estimating total monthly ops across all scenarios:

| Projected vs Plan | Action |
|-------------------|--------|
| < 60% of limit | Green — proceed with build |
| 60-80% of limit | Yellow — note in spec, monitor after deployment |
| 80-100% of limit | Orange — optimize design before building (reduce intervals, add filters) |
| > 100% of limit | Red — STOP. Either redesign or recommend plan upgrade before building |

Present the estimate to the user before proceeding:
```
OPS ESTIMATE — {Client} — {Date}
Plan: {tier} ({limit} ops/month)
Projected: {total} ops/month ({percentage}% of limit)
Breakdown:
  {scenario1}: {ops}/month ({interval}, {modules} modules)
  {scenario2}: {ops}/month ({interval}, {modules} modules)
  ...
Status: {GREEN|YELLOW|ORANGE|RED}
```

### 5. Common Estimation Mistakes

- **Forgetting idle polls:** A scheduler running every 5 min = 8,640 executions/month even with zero data
- **Ignoring iterator multiplication:** 10 rows × 5 modules inside iterator = 50 ops, not 5
- **Not counting error handlers:** Resume error handlers add 1+ ops per error occurrence
- **Assuming webhooks are free:** Each webhook execution still costs ops (just demand-driven, not scheduled)
- **Overlooking test/dev scenarios:** UTIL scenarios left active consume ops too

---

## Section B: Post-Hoc Analysis

Run this when a client reports ops issues, hits plan limits, or at periodic review.

### Step 1: Inventory Active Scenarios

From `infrastructure.yaml`, list every scenario with `status: active` or recently active:

| Scenario | ID | Trigger | Frequency | Status |
|----------|----|---------|-----------|--------|
| A0 | {id} | scheduled ({N}s) | {monthly_execs}/month | active |
| A1 | {id} | webhook | demand-driven | active |
| ... | ... | ... | ... | ... |

Include UTIL scenarios — they may be consuming ops if left active.

### Step 2: Fetch Execution History

For each scenario:
```
executions_list(scenarioId={id}, limit=100)
```

From the response, extract per execution:
- `operations` — total ops consumed
- `status` — 1=success, 2=warning, 3=error
- `started` — timestamp (for calculating execution frequency)

### Step 3: Calculate Per-Scenario Cost

| Scenario | Avg Ops/Exec | Exec/Day | Projected Monthly Ops | % of Total |
|----------|-------------|----------|-----------------------|------------|
| A0 | {n} | {n} | {n} | {n}% |
| A1 | {n} | {n} | {n} | {n}% |
| ... | ... | ... | ... | ... |
| **TOTAL** | | | **{sum}** | 100% |

Sort by projected monthly ops descending. The top consumer is the primary optimization target.

### Step 4: Identify Optimization Opportunities

For the top consumers, check these patterns:

| Optimization | Expected Reduction | Applies When |
|-------------|-------------------|-------------|
| Increase polling interval (e.g., 5m → 15m) | Linear (3x for this example) | Data freshness allows longer gaps |
| Add early-exit filter after trigger | Skips all downstream modules on empty/non-due polls | Scheduled scenarios that often have nothing to process |
| Replace polling with webhook | Eliminates idle executions entirely | Source system supports outbound webhooks |
| Batch API calls instead of per-item | Reduces by `(items - 1) × batch_modules` | Iterator processing individual items |
| Merge sequential HTTP modules | -1 op per merge | Adjacent HTTP calls to same service |
| Deactivate unused UTIL scenarios | Eliminates their entire ops cost | Test fixtures left running |

### Step 5: Optimization Impact Estimate

For each proposed optimization, calculate the new projected ops:

```
BEFORE: {scenario} = {old_ops}/month
AFTER:  {scenario} = {new_ops}/month
SAVING: {delta}/month ({percentage}% reduction)
```

### Step 6: Plan Tier Recommendation

Compare optimized total against plan tiers:

| If optimized total... | Recommendation |
|----------------------|----------------|
| Fits within current plan (< 80%) | Apply optimizations, no plan change needed |
| Fits within current plan but tight (80-100%) | Apply optimizations, monitor monthly |
| Exceeds current plan even after optimization | Recommend plan upgrade or ops pack purchase |

### Step 7: Output Report

```
OPERATIONS ANALYSIS — {Client} — {Date}
Current plan: {tier} ({limit} ops/month)
Current usage: {total} ops/month ({percentage}% of limit)

Top consumers:
  1. {scenario}: {ops}/month ({percentage}% of total) — {trigger_detail}
  2. {scenario}: {ops}/month ({percentage}% of total) — {trigger_detail}

Optimization plan:
  1. {optimization}: {old} → {new} ops/month (saves {delta})
  2. {optimization}: {old} → {new} ops/month (saves {delta})

Post-optimization projected: {new_total} ops/month ({new_percentage}% of limit)
Recommendation: {STAY_ON_PLAN | UPGRADE_TO_{tier} | PURCHASE_OPS_PACK}
```

---

## Integration

- **Pre-build:** Referenced from `.claude/skills/skil_make-pack/SKILL.md` Build Procedure step 2.5
- **Post-hoc:** Load when client reports ops issues or at periodic `/status-check`
- **AUTONOMOUS-DIAGNOSTICS:** Cross-reference from Level 1 when symptom is "account paused" or "ops limit reached"
