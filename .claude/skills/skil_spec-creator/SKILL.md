---
name: spec-creator
description: Creates automation specifications from requirements. Use when defining new automations, documenting workflows, converting discussions to specs, or planning client automations. Generates Mermaid flow diagrams, API references, edge cases, and test definitions.
---

# Spec Creator

Creates comprehensive specifications following the Agentic Ops standard format. Supports all work item types (automation, app, backend, project) and all orchestrators (n8n, Make.com, Trigger.dev, FastAPI).

## Quick Start

1. Determine work item type (Step 0)
2. Detect orchestrator and gather requirements
3. Generate Mermaid diagram following `modules/MERMAID-PATTERNS.md`
4. Add edge cases from `modules/EDGE-CASES.md`
5. Define tests using `modules/TESTING-SECTION.md`
6. Use type-specific module for extra sections (n8n, Make.com, app, backend, or project)
7. Save to `workspace/clients/{client}/specs/1-spec/{id}.md`

## Process

### Step 0: Determine Work Item Type

Ask the user what they are building:

| Type | ID Pattern | When to Use |
|------|-----------|-------------|
| `automation` | `a{N}` | Background job, cron task, webhook handler, n8n workflow |
| `sub-automation` | `a{N}.{M}` | Child of an existing automation (e.g., `a6.1`, `a6.2`) |
| `app` | `app{N}` | Frontend, dashboard, web UI |
| `backend` | `be{N}` | Backend API, DB migration, infrastructure service |
| `project` | `p{N}` | Multi-phase project container (2+ independently-trackable phases) |
| `phase` | `p{N}.{M}` | A single phase within an existing project |
| `bug-fix` | `fix{N}` | A tracked fix for a specific existing automation or work item |

The type determines the ID prefix, which sections to include, and which module to use.

**If type is `bug-fix`:** follow the abbreviated process in **Step 0B** instead of Steps 1–7.

### Step 0B: Bug-Fix Abbreviated Process

Use this instead of Steps 1–7 when type is `bug-fix`.

**Gather from user:**
- Which automation is broken? (get the ID, e.g., `a2`)
- What is the symptom / what's failing?
- Is the root cause known yet?

**Determine ID and filename:**
1. Scan all stage folders (`1-spec/`, `2-build/`, `3-test/`, `4-live/`) for existing `fix{N}` files
2. Assign next available `fix{N}` (e.g., `fix1`, `fix2`)
3. **Filename convention:** `fix{N}-{parentId}-{short-description}.md`
   - Example: `fix1-a2-order-sync-crash.md`
   - This makes the link visible from the folder listing without opening the file

**Create the spec:**
- Use `workspace/templates/specs/bug-fix-spec.md` (not `automation-spec.md`)
- Set `parent: a{N}` to the automation being fixed
- Set `orchestrator` to match the parent automation's orchestrator
- Save to `workspace/clients/{client}/specs/1-spec/fix{N}-{parentId}-{description}.md`

**Update the parent spec:**
- Open the parent automation spec (e.g., `a2-crm-erp-sync.md`)
- Set `needs_fixes: true` in its frontmatter
- Add to `last_changes`: `"Opened fix1: {short description}"`

**Update the README:**
- Add the fix to the "Open Bug Fixes" section in `workspace/clients/{client}/specs/README.md`

**Report to user:**
- Fix spec location and ID
- Parent spec updated (`needs_fixes: true`)
- Next steps: investigate root cause, update "Root Cause" section, then implement

---

### Step 1: Detect Orchestrator & Gather Requirements

1. **For automation/sub-automation: detect orchestrator** (before asking questions):
   - Check for `trigger.config.ts` in automations → Trigger.dev
   - Check for `railway.toml` in automations → FastAPI
   - Check `.mcp.json` for `n8n-{client}` entry → n8n
   - Check `infrastructure.yaml` for `type: make` entry → Make.com
2. **For app/backend/project/phase**: orchestrator = `none` (skip detection)
3. Load `prompts/gather-requirements.md`
4. Ask core questions (all types)
5. If n8n: ask n8n-specific questions (new vs update, visual verification, phased approach)
6. If Make.com: ask Make.com-specific questions (new vs existing scenario, org/team, visual verification)

### Step 2: Identify Client and ID

Determine:
- Client name: Check `workspace/clients/` folder or ask user
- ID: Next available ID based on type — scan all stage folders (`1-spec/`, `2-build/`, `3-test/`, `4-live/`) across the client to find the highest existing number:
  - Automation: `a{N}`
  - Sub-automation: `a{N}.{M}` (determined by parent automation)
  - App: `app{N}`
  - Backend: `be{N}`
  - Project: `p{N}`
  - Phase: `p{N}.{M}` (determined by parent project)
  - Bug-fix: `fix{N}` (scan for existing `fix*.md` files across all stage folders)
- Name: Descriptive name from problem statement

### Step 3: Fetch API Docs (Mandatory for HTTP-based integrations)

**This step must be completed BEFORE writing endpoints into the spec.**
Wrong endpoints in specs lead directly to broken n8n HTTP nodes, Make.com HTTP modules, and incorrect API clients.

**For automation/sub-automation (n8n or Make.com):**
1. Check if native nodes/app modules exist for each system (n8n: use `search_nodes`; Make.com: check the Make.com app directory)
2. If native nodes/modules exist: Note which ones to use (e.g., Slack, Google Sheets) — no HTTP docs needed
3. If HTTP Request/HTTP modules are needed for a system:
   - Check if `workspace/api-docs/{system}/` already exists with a `full-documentation.md`
   - **If missing: invoke the api-docs-fetcher immediately** (do not proceed with spec until done):
     ```bash
     uv run .claude/skills/api-docs-fetcher/scripts/fetch_docs.py \
       --url "{api_docs_base_url}" \
       --service {system_name}
     ```
   - Ask the user for the API docs URL if unknown
   - After fetching: scan `workspace/api-docs/{system}/full-documentation.md` for the exact endpoints needed
   - Use **only verified endpoint paths** from the docs in the API References table

**For automation/sub-automation (code-based — Trigger.dev / FastAPI):**
1. Check if `workspace/api-docs/{system}/` exists
2. If exists: Review `full-documentation.md` for relevant endpoints
3. **If missing: invoke the api-docs-fetcher** before writing any endpoint paths in the spec:
   ```bash
   uv run .claude/skills/api-docs-fetcher/scripts/fetch_docs.py \
     --url "{api_docs_base_url}" \
     --service {system_name}
   ```
4. Use verified endpoint paths from fetched docs (or ask user if no docs URL available)

**For app/backend:**
1. Check if existing API clients exist in `automations/python/clients/` or `automations/app/clients/`
2. Note tech stack and existing patterns

> **Rule**: Never invent or guess API endpoint paths. If docs don't exist and can't be fetched, explicitly mark endpoints in the spec as `⚠️ VERIFY` and note they must be confirmed before implementation.

### Step 4: Design Flow

**For code-based automation (Trigger.dev / FastAPI):**
Using the 5-step pattern (Initialize → Fetch → Transform → Execute → Finalize):
1. Map user's workflow to the 5 steps
2. Generate Mermaid diagram per `modules/MERMAID-PATTERNS.md` (code-based section)
3. Identify decision points and branches
4. Note any loops or conditional flows

**For n8n automation:**
Using node-based patterns:
1. Map user's workflow to n8n nodes (Trigger → HTTP Request / Native Node → Code → Action)
2. Generate Mermaid diagram per `modules/MERMAID-PATTERNS.md` (n8n section)
3. Show node types and operations in diagram (e.g., "GET /orders", "Code: Transform")
4. Note IF/Switch branching, pagination, and error handling

**For Make.com automation:**
Using module-based patterns:
1. Map user's workflow to Make.com modules (Trigger module → App/HTTP modules → Router → Action)
2. Generate Mermaid diagram per `modules/MERMAID-PATTERNS.md` (Make.com section)
3. Show module types and apps in diagram (e.g., "Fortnox: List orders", "Router", "Slack: Post message")
4. Note Router branching, Iterator/Aggregator patterns, and error handler routes

**For app:**
Using `modules/APP-SECTIONS.md`:
1. Map user flows (pages, interactions)
2. Define tech stack and component structure
3. Generate user flow diagram

**For backend:**
Using `modules/BACKEND-SECTIONS.md`:
1. Map API endpoints and database schema
2. Define auth and deployment model

**For project/phase:**
Using `modules/PROJECT-SECTIONS.md`:
1. List phases and dependencies
2. Define success criteria per phase

### Step 5: Define Edge Cases

Based on systems involved, add edge cases from `modules/EDGE-CASES.md`:

**All types:**
- API-specific errors (rate limits, auth, timeouts)
- Data validation scenarios
- Duplicate handling

**Additional for n8n:**
- n8n-specific edge cases (Continue On Fail, node retry, credential refresh)

**Additional for Make.com:**
- Make.com-specific edge cases (error handlers, connection refresh, incomplete executions)

**Skip for project/phase:** (no code = no edge cases)

### Step 6: Create Testing Section

**For code-based automation (Trigger.dev / FastAPI):**
Using `modules/TESTING-SECTION.md`:
- Define unit tests for transform logic
- Define integration tests (dry-run, sandbox)
- Extract acceptance criteria from user's requirements

**For n8n:**
Using `modules/TESTING-SECTION.md` (n8n section) and `modules/N8N-SECTIONS.md`:
- Define manual testing steps in n8n UI (Limit nodes, disable write nodes)
- Define visual verification steps in target systems
- Define idempotency test (re-run creates no duplicates)
- Extract acceptance criteria (verifiable through UI inspection)

**For Make.com:**
Using `modules/TESTING-SECTION.md` (Make.com section) and `modules/MAKE-SECTIONS.md`:
- Define manual testing steps (Run once, inspect module bubbles)
- Define visual verification steps in target systems
- Define idempotency test (re-run creates no duplicates)
- Extract acceptance criteria (verifiable through execution inspector and target system UIs)

**For app/backend:**
Using `modules/APP-SECTIONS.md` or `modules/BACKEND-SECTIONS.md`:
- Define manual QA steps
- Define integration test scenarios

**For project/phase:** (keep it high-level; individual phases have their own specs)

### Step 7: Generate Spec File

Use template at `workspace/templates/specs/automation-spec.md`:

**For automation (code-based):**
1. Fill in frontmatter: `type: automation`, `id: a{N}`, `orchestrator`, `trigger`, `systems`
2. Complete each section using code-based patterns
3. Save to `workspace/clients/{client}/specs/1-spec/{id}.md`

**For automation (n8n):**
1. Fill in frontmatter with `orchestrator: n8n`
2. Use n8n section templates from `modules/N8N-SECTIONS.md`:
   - Add **N8N Workflow** section (workflow info, credentials, node types)
   - Use **Manual Testing** section instead of pytest
   - Add **Visual Verification** section
   - Use **n8n Implementation Notes** format
3. Save to `workspace/clients/{client}/specs/1-spec/{id}.md`

**For automation (Make.com):**
1. Fill in frontmatter with `orchestrator: make`
2. Use Make.com section templates from `modules/MAKE-SECTIONS.md`:
   - Add **Make.com Scenario** section (scenario info, connections, module types)
   - Use **Manual Testing in Make.com** section instead of pytest
   - Add **Visual Verification** section
   - Use **Make.com Implementation Notes** format
3. Save to `workspace/clients/{client}/specs/1-spec/{id}.md`

**For app:**
1. Fill in frontmatter: `type: app`, `id: app{N}`, `orchestrator: none`
2. Use `modules/APP-SECTIONS.md` sections
3. Save to `workspace/clients/{client}/specs/1-spec/{id}.md`

**For backend:**
1. Fill in frontmatter: `type: backend`, `id: be{N}`, `orchestrator: none`
2. Use `modules/BACKEND-SECTIONS.md` sections
3. Save to `workspace/clients/{client}/specs/1-spec/{id}.md`

**For project:**
1. Fill in frontmatter: `type: project`, `id: p{N}`, `orchestrator: none`
2. Use `modules/PROJECT-SECTIONS.md` (phases list, goals, milestones)
3. Save to `workspace/clients/{client}/specs/1-spec/{id}.md`

Ensure `workspace/clients/{client}/specs/1-spec/` folder exists (create if needed).

## Output

```
workspace/clients/{client}/specs/1-spec/{id}.md
```

## After Creating Spec

Report to user:
- Spec location and ID assigned
- Type and orchestrator used
- Next steps: Build the workflow (n8n) or scenario (Make.com) or implement (code-based) or start development (app/backend)
- Testing: Manual testing in n8n UI or Make.com / testing-agent for code-based / QA for app/backend

## Modules

| Module | Purpose |
|--------|---------|
| [MERMAID-PATTERNS.md](modules/MERMAID-PATTERNS.md) | Flow diagram templates (code-based + n8n + Make.com) |
| [EDGE-CASES.md](modules/EDGE-CASES.md) | Common error scenarios by system + n8n/Make.com-specific |
| [TESTING-SECTION.md](modules/TESTING-SECTION.md) | Test structure templates (pytest + n8n/Make.com manual) |
| [N8N-SECTIONS.md](modules/N8N-SECTIONS.md) | n8n-specific spec section templates |
| [MAKE-SECTIONS.md](modules/MAKE-SECTIONS.md) | Make.com-specific spec section templates |
| [APP-SECTIONS.md](modules/APP-SECTIONS.md) | App/frontend spec section templates |
| [BACKEND-SECTIONS.md](modules/BACKEND-SECTIONS.md) | Backend service spec section templates |
| [PROJECT-SECTIONS.md](modules/PROJECT-SECTIONS.md) | Project container spec template |
