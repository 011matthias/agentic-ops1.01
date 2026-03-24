# Platform Feasibility Assessment

> When to use: At client onboarding (`/new-client`, `/convert-proposal`) — before creating the folder structure. Also at first spec creation and whenever the client's platform subscription changes. The goal is to catch subscription mismatches, capability blockers, and cost risks before any building begins.

---

## Section A: Full Platform Capability Audit

Run this checklist during onboarding. Ask the client or investigate autonomously (check their account via MCP if available).

### Make.com

| Item | How to Check | Record In |
|------|-------------|-----------|
| **Plan tier** (free/core/pro/teams/enterprise) | Ask client, or check Make.com UI → Organization → Subscription | `platform.tier` |
| **Ops limit** (monthly operations cap) | Plan tier table below; ask if they've purchased additional ops packs | `platform.ops_limit` |
| **API/MCP access** | Pro+ plans only. Check: can they generate an MCP token at Profile → API/MCP? | `platform.api_access` |
| **Concurrent active scenarios** | Free=2, Core=unlimited, but check if custom limit applies | `platform.concurrent_limit` |
| **Available modules** | Some modules (Custom Apps, premium integrations) require Pro+. Check if the design needs any gated modules | `platform.module_blockers` |
| **Data store limits** | Free=1 store (1MB), Core=unlimited stores but 5MB each. Check if design needs multiple stores or large records | `platform.data_store_notes` |
| **File storage** | Free=1GB, paid=varies. Relevant if automation handles file attachments | `platform.file_storage` |
| **Zone** (us1/eu1/eu2) | Affects latency and data residency. Check org URL | Already in `infrastructure.yaml` |

**Make.com plan tier reference:**

| Plan | Ops/Month | Scenarios | API/MCP | Data Stores | Cost |
|------|-----------|-----------|---------|-------------|------|
| Free | 1,000 | 2 active | No | 1 (1MB) | $0 |
| Core | 10,000 | Unlimited | No | Unlimited (5MB each) | ~$10/mo |
| Pro | 10,000 | Unlimited | Yes | Unlimited (5MB each) | ~$18/mo |
| Teams | 10,000 | Unlimited | Yes | Unlimited (5MB each) | ~$29/mo |
| Enterprise | Custom | Unlimited | Yes | Custom | Custom |

Note: All paid plans have the same base ops (10k). Extra ops packs available. The difference between Core/Pro/Teams is features (API access, team management, priority execution), not ops volume.

### n8n

| Item | How to Check | Record In |
|------|-------------|-----------|
| **Hosting type** (cloud/self-hosted) | Ask client | `platform.hosting` |
| **Execution limit** | Cloud: plan-dependent. Self-hosted: unlimited but resource-constrained | `platform.execution_limit` |
| **Workflow count limit** | Cloud Starter=5 active, Pro=unlimited | `platform.workflow_limit` |
| **Database/storage limits** | Cloud: plan-dependent. Self-hosted: check DB server capacity | `platform.storage_notes` |
| **Available nodes** | Community vs Enterprise nodes. Check if design requires enterprise-only nodes | `platform.node_blockers` |
| **Credential sharing** | Teams/Enterprise feature. Relevant for multi-user setups | `platform.team_features` |

### Trigger.dev

| Item | How to Check | Record In |
|------|-------------|-----------|
| **Plan tier** (hobby/pro/enterprise) | Ask client or check dashboard | `platform.tier` |
| **Execution minutes/month** | Hobby=500min, Pro=varies by plan | `platform.execution_minutes` |
| **Concurrency limit** | Hobby=5 concurrent, Pro=varies | `platform.concurrency` |
| **Event volume limits** | Check trigger rate limits | `platform.event_limit` |
| **Available integrations** | All integrations available on all plans (code-based) | N/A |

### Common (All Orchestrators)

These questions apply regardless of platform:

| Item | Why It Matters |
|------|---------------|
| **Number of planned automations** | More automations = more ops/executions consumed |
| **Estimated event volume** (daily/monthly) | Webhook-triggered automations scale with event count |
| **Growth expectations** | Will volume 2x in 6 months? Size the plan for where the client is going |
| **Third-party API rate limits** | External APIs may constrain design (e.g., Gmail 250 sends/day, Google Sheets 60 reads/min) |
| **Data sensitivity / compliance** | May constrain zone selection or require self-hosted |

---

## Section B: Feasibility Verdict Framework

After completing the audit, produce a verdict using this framework.

### Capacity Verdict (ops/executions)

Estimate the workload using OPERATIONS-ANALYZER Section A formulas (for Make.com) or equivalent estimation for n8n/Trigger.dev. Then:

| Projected vs Limit | Verdict | Action |
|--------------------|---------|--------|
| < 50% of limit | **GREEN** | Proceed — headroom for growth |
| 50-80% of limit | **YELLOW** | Proceed — document monitoring plan, flag in spec |
| 80-100% of limit | **ORANGE** | Recommend upgrade BEFORE building. If client declines, optimize design to fit |
| > 100% of limit | **RED** | STOP. Client must upgrade plan, purchase ops packs, or accept reduced scope |

### Capability Blockers

Check these independently from capacity:

| Blocker Type | Example | Verdict |
|-------------|---------|---------|
| **Feature gate** | API/MCP access requires Pro+ (Make.com) | BLOCKER — upgrade or use workaround |
| **Module gate** | Custom Apps module not on plan | BLOCKER — upgrade or use HTTP module |
| **Node gate** | Enterprise-only n8n node required | BLOCKER — upgrade or use community alternative |
| **Rate limit** | Gmail 250/day but client expects 500 sends/day | BLOCKER — design change needed (batch, queue, alternate provider) |
| **Storage gate** | Data store size insufficient for expected volume | BLOCKER — upgrade or implement data rotation |

A single BLOCKER overrides a GREEN capacity verdict — the design cannot proceed until the blocker is resolved.

### Combined Verdict

```
PLATFORM FEASIBILITY — {Client} — {Date}
Orchestrator: {name} ({tier} plan)

Capacity: {GREEN|YELLOW|ORANGE|RED} — {projected} of {limit} ({%})
Blockers: {NONE | list of blockers with resolution options}

Verdict: {PROCEED | PROCEED WITH MONITORING | UPGRADE REQUIRED | REDESIGN REQUIRED}

{If not GREEN/no blockers:}
Recommendations:
  1. {recommendation with specific action}
  2. {alternative if client declines #1}
```

---

## Section C: Recording the Assessment

After completing the audit, record findings in `infrastructure.yaml` under a `platform` section:

```yaml
platform:
  tier: "core"                    # Plan name (lowercase)
  ops_limit: 10000                # Monthly cap (ops, executions, or minutes)
  api_access: true                # Can we use MCP/API tools?
  concurrent_limit: null          # null = unlimited on this plan
  feasibility: "yellow"           # green|yellow|orange|red
  blockers: []                    # List of capability blockers, empty if none
  assessed: "2026-03-14"          # Date of this assessment
  notes: "Client on Core plan. Projected 8k ops/month fits within limit
    but leaves little headroom. Recommend monitoring monthly. If adding
    more automations, upgrade to Pro (same ops but enables API access)."
```

Update the `assessed` date and re-run the audit whenever:
- A new automation is added to the client
- The client changes their subscription
- `/ops-audit` shows the verdict has shifted

---

## Integration

- **`/new-client` Step 2.5:** Run Section A + B after orchestrator selection. Record in infrastructure.yaml during folder creation.
- **`/convert-proposal` Step 5.5:** Same as above.
- **`spec-creator`:** When creating a new spec, check `infrastructure.yaml` platform section. If adding this automation would shift the verdict (e.g., YELLOW → ORANGE), flag in spec implementation notes.
- **`/ops-audit`:** Uses the recorded `platform.ops_limit` and `platform.tier` as the baseline for live comparison.
- **OPERATIONS-ANALYZER:** This module provides the investigation framework; OPERATIONS-ANALYZER provides the ops estimation formulas. Do not duplicate formulas — reference OPERATIONS-ANALYZER Section A.
