# Gather Requirements

## Step 0: Detect Orchestrator

Before asking questions, determine which orchestrator this client uses:

1. **Check client folder:**
   - Has `trigger.config.ts` in automations → **Trigger.dev**
   - Has `railway.toml` in automations → **FastAPI** (legacy)
   - Check `.mcp.json` for `n8n-{client}` entry → **n8n**
   - Check `infrastructure.yaml` for `type: make` entry → **Make.com**

2. **If unclear, ask:**
   > "Which orchestrator does this client use?
   > - **n8n** (visual workflow builder)
   > - **Make.com** (visual scenario builder)
   > - **Trigger.dev** (code-first, TypeScript + Python)
   > - **FastAPI** (legacy Python service on Railway)"

---

## Core Questions (All Orchestrators)

Ask the user these questions to understand the automation:

> "Tell me about the automation you need:
>
> 1. **Problem:** What manual task or pain point are you solving?
> 2. **Systems:** Which systems are involved? (Fortnox, Upsales, Slack, Google Sheets, etc.)
> 3. **Trigger:** When should this run?
>    - **CRON:** At a specific time (e.g., "daily at 8am", "every hour")
>    - **Webhook:** When an event occurs (e.g., "when deal closes in Upsales")
>    - **Manual:** Only when explicitly triggered
> 4. **Flow:** Walk me through the steps - what happens from start to finish?
> 5. **Outcome:** What should happen when it completes successfully?
> 6. **Success criteria:** How do we know it worked correctly?"

---

## n8n-Specific Questions

If the orchestrator is n8n, also ask:

> "A few more questions for the n8n workflow:
>
> 1. **Existing workflow?** Is this a **new workflow** or an **update to an existing one**?
>    - If updating: What's the workflow name or ID? What needs to change?
> 2. **Visual verification:** After this runs, what should we check visually in {target system} to confirm it worked?
> 3. **Phased approach?** Should we build this incrementally (e.g., manual trigger first, then automate)?"

---

## Make.com-Specific Questions

If the orchestrator is Make.com, also ask:

> "A few more questions for the Make.com scenario:
>
> 1. **Existing scenario?** Is this a **new scenario** or an **update to an existing one**?
>    - If updating: What's the scenario name? What needs to change?
> 2. **Make.com organization:** Which Make.com organization/team should this scenario live in?
> 3. **Visual verification:** After this runs, what should we check visually in {target system} to confirm it worked?
> 4. **Native apps:** Do you know if the systems involved have native Make.com app modules, or should we check?"

---

## Parsing Responses

From the user's answers, extract:

| Field | Source | Example |
|-------|--------|---------|
| `name` | Problem description | "Recurring Order Generator" |
| `orchestrator` | Detection or user answer | "n8n" or "make" |
| `trigger.type` | Trigger answer | "cron" |
| `trigger.schedule` | CRON timing | "0 8 * * *" |
| `systems` | Systems mentioned | ["fortnox", "upsales"] |
| `acceptance_criteria` | Success criteria | ["Orders created correctly"] |

**Additional fields for n8n:**

| Field | Source | Example |
|-------|--------|---------|
| `existing_workflow` | n8n Q1 | "wf-abc123" or null |
| `visual_checks` | n8n Q2 | ["Check order in Fortnox UI"] |
| `phased` | n8n Q3 | true/false |

**Additional fields for Make.com:**

| Field | Source | Example |
|-------|--------|---------|
| `existing_scenario` | Make.com Q1 | "A3 - Daily Order Sync" or null |
| `make_org` | Make.com Q2 | "Client Organization" |
| `visual_checks` | Make.com Q3 | ["Check order in Fortnox UI"] |

---

## Follow-up Questions

If answers are unclear, ask:

**For unclear systems:**
> "Which specific API endpoints will we need from {system}?"

**For complex flows:**
> "Are there any conditional branches? For example, 'if X then Y, else Z'?"

**For edge cases:**
> "What should happen if:
> - No data is found?
> - A duplicate exists?
> - The API returns an error?"

**For business value:**
> "How much time does this manual task take? How often is it done?"

**For n8n updates (existing workflow):**
> "What does the existing workflow do now? What specifically needs to change?"

**For Make.com updates (existing scenario):**
> "What does the existing scenario do now? What specifically needs to change?"
