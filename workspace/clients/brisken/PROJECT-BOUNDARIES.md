# Brisken Project Boundaries

**As of:** 2026-05-17 (active/paused swapped back: expense reconciliation is the project, lead nurturing paused. See swap history at the bottom; this scope has reversed multiple times, the history ledger is the authority on what is current.)
**Status:** Two separate projects. One active. One paused. No shared infrastructure between them.

This document is binding. Any future session working in this client folder must read it before touching any spec, code, or infrastructure. Because the active/paused assignment has changed several times, the **Swap history** section at the bottom is the single source of truth for which project is live right now. Do not infer it from file presence; read the ledger.

---

## Active project

**AI-assisted Expense Reconciliation platform with Zoho Books export**

- Status: active. Confirmed by the user 2026-05-17 as the project Brisken is doing. The earlier read that the Upwork offer meant lead nurturing was corrected: the offer was a separate matter; the expense reconciliation product is the engagement.
- Source functional document: provided by the user 2026-05-14
- Live artifacts (verified present 2026-05-17):
  - `reference/expense-reconciliation-open-decisions.md` (18-decision sheet with recommendation column) -- current, ready for Dirk
- Open comms item with no draft yet: the headline-goal question for Dirk (which of the four goal directions is primary). The earlier draft for this was removed during the lead-nurturing detour and needs rewriting before it goes out, alongside the open-decisions sheet.
- Specs (when written): `specs/1-spec/p1-*.md`
- Code (when written): `automations/expense-reconciliation/`
- Context (when written): `context/expense-reconciliation/`
- ID namespace owned: `p1`, `p1.app1`, `p1.be1`, `p1.a1`, ...
- Proposed stack (from the functional document, not yet confirmed by Dirk): standalone FastAPI backend, React frontend, PostgreSQL, Azure Blob storage, Azure Document Intelligence, Anthropic Claude.
- Open with client: the 18 decisions and the headline-goal question. These are the immediate next deliverable for this project.

This is the only active project in this client folder. Sessions that name Brisken default to this project unless they explicitly state otherwise.

---

## Paused project

**Lead Nurturing platform with Universal Communicator extension**

- Status: paused. A real, separate project with substantial prior work, not dead. Not being worked on per the user's 2026-05-17 instruction. Resumes only if explicitly picked up.
- Specs: `specs/1-spec/a0-linkedin-lead-ingest.md`, `a1-website-form-ingest.md`, `a2-sap-email-ingest.md`, `a3-lead-follow-up-pipeline.md`, `a4-reply-monitoring.md`. Each carries `paused: true` in frontmatter.
- Planned, not written: `app1` (unified dashboard), `a5` (invoice and accounts-payable routing), `a6` (compliance email routing).
- Preserved artifacts (verified present 2026-05-17; do NOT delete; primary sources and prior work that carry forward if this project resumes):
  - `reference/2026-04-10-call-transcript.md` (43-minute primary client call; irreplaceable)
  - `context/drafts/getting-started-and-effort-to-dirk.md` (lead-nurturing build plan and effort estimate; not applicable while paused)
- ID namespace owned: `a0` through `a6`, `app1`.

While paused, this project receives no new specs, no implementation work, no decision making, and no infrastructure changes.

---

## Why nothing is deleted

The active/paused assignment for this client has reversed several times (see Swap history). Deleting the paused project's files to reduce confusion was considered and rejected on 2026-05-17: the 2026-04-10 call transcript is an irreplaceable primary source, the lead-nurturing specs are substantial work that a repeated reversal could make live again, and the boundary mechanism in this document already provides the isolation that deletion would provide, without the irreversibility. Context isolation is achieved by this ledger plus the `paused: true` flags plus the session scope rule, not by deleting files.

---

## Isolation guarantees

Nothing in the list below is shared between the two projects. Any future session tempted to introduce sharing must edit this document first and justify the change.

1. **Codebase.** Separate folders under `automations/`. No shared libraries. No common module imported by both.
2. **Orchestrators.** Different stacks entirely. Expense reconciliation uses its own FastAPI service. Lead nurturing, if resumed, uses a headless backend behind a React/Next.js dashboard.
3. **Databases.** Separate database instances. No shared schemas. No shared tables.
4. **File storage.** Separate storage buckets or containers. No shared paths.
5. **Secrets and environment variables.** Separate `.env` files. Separate secret stores.
6. **MCP servers.** Separate MCP server entries in `.mcp.json` if either uses any.
7. **Deployment targets.** Separate Railway, Vercel, or cloud-host projects. Separate GitHub repositories via separate git subtrees.
8. **CI/CD pipelines.** Separate workflows. A failing deploy on one never blocks the other.
9. **Test fixtures.** Separate fixtures, documented in each project's own `context/test-fixtures.md`.
10. **Logging and monitoring.** Separate dashboards. An incident on one does not page the other.

---

## ID namespace rules

- Expense reconciliation owns `p1` and all `p1.*` sub-identifiers. This is the active project; new specs here use the `p1` prefix.
- Lead nurturing owns `a0` through `a6`, plus `app1`. No new IDs in this range while paused.
- A future third project picks a fresh container ID (`p2`, `p3`, ...).

If a session writes a spec whose ID falls in another project's namespace, it has crossed the boundary; rewrite with the correct prefix.

---

## File path rules

| Path | Belongs to | Notes |
|---|---|---|
| `specs/1-spec/p1-*.md` | Expense reconciliation (active) | New specs for the active project go here |
| `specs/1-spec/a*.md`, `app*.md` | Lead nurturing (paused) | Frozen; no edits while paused |
| `automations/expense-reconciliation/` | Expense reconciliation | Created when implementation starts |
| `automations/lead-nurturing/` | Lead nurturing | Only if that project resumes |
| `context/drafts/` | Either project | Filename must indicate the project |
| `reference/2026-04-10-call-transcript.md` | Lead nurturing (paused) | Primary source; never delete |
| `reference/expense-reconciliation-open-decisions.md` | Expense reconciliation (active) | Current |
| `PROJECT-BOUNDARIES.md` | This document | Binding |

---

## Operational rule for sessions

One session works on one project at a time. The session header `Scope:` line must name the project explicitly (`brisken/expense-reconciliation` or `brisken/lead-nurturing`). Cross-project edits inside a single session are not allowed. If a session needs to touch the other project, it stops, checkpoints, and starts a fresh session scoped to the other.

---

## When the paused project resumes

If lead nurturing resumes, it gets its own session, checkpoint, infrastructure, deploy targets, and repository. It shares no code or services with expense reconciliation. The resumption is recorded with a new entry in the Swap history.

---

## What changes if this document is violated

A boundary violation (cross-project edit, shared infrastructure, ID-namespace collision, session scope tag missing or wrong) is a friction event of category `boundary-violation`. Logged at the next checkpoint; the violation is reversed before further work. No exceptions.

---

## Swap history

The authority on which project is live. Read top entry for current state.

- 2026-05-17: **Expense reconciliation set ACTIVE, lead nurturing set PAUSED.** User corrected the earlier read: the Upwork offer was a separate matter, not the engagement. a0-a4 `paused: true` re-applied. Deletion of lead-nurturing context considered and rejected (primary-source transcript, repeated reversals, boundary already provides isolation). This is the current state.
- 2026-05-15: Lead nurturing set active, expense reconciliation paused, after Dirk's Upwork offer was read as describing lead nurturing. a0-a4 unpaused.
- 2026-05-15: Initial boundary created with expense reconciliation active, lead nurturing paused (user instruction to drop the old scope).
