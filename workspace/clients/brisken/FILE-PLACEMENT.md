# Brisken File Placement (client-specific)

**Binding for this client.** Every file generated for Brisken lands in the
home that matches its **project** first, then its **kind**. This rule is the
source of truth for *where a Brisken file goes*. It sits under the repo-wide
file-placement system (`.claude/rules/rule_no_file_bloat.md` = W1
whether-to-create; `.claude/rules/rule_file_placement.md` = W2 where-it-lands;
`skil_file-placement`; `file-placement-gate.py`) and adds the Brisken
project-sort the generic gate can't know. Read `PROJECT-BOUNDARIES.md` first
(which project is live, isolation rules); this rule says where the file goes.

Run W1 (do I even create this?) → then this rule (which project? which folder?).

## Step 1 — classify by PROJECT

Brisken has three projects plus client-level material. Decide which one the
file serves before anything else (the swap-history ledger in
`PROJECT-BOUNDARIES.md` is the authority on what is live).

| Project | It's this project if the file is about… |
|---|---|
| **p1 — expense-reconciliation** (active) | bank/card statement reconciliation, Chase data, receipts/tickets, the recon tool / hosted workbench, Chris's workflow, Zoho Books / Zoho Expense, GL classification, the recon spec or call materials |
| **p2 — lead-generation** (active) | outbound lead gen, the Rome / TA Cook event, OnePilot product marketing, the OnePilot website / TreasuryCentral, AEO / Q&A clusters, targeting lists, outreach assets, the Dirk product-strategy decks, BANT qualification |
| **lead-nurturing** (PAUSED) | a0–a6 / app1, the universal-communicator inbound app. **Frozen — generate no new files here** until an explicit resumption is recorded in the swap history. |
| **client-level** (no single project) | the comms thread, brand logos, Brisken product decks, the binding docs themselves |

If a file genuinely serves both active projects, it is almost always
client-level (put it at the `context/` root), not duplicated into each.
Cross-project files inside one session are a `boundary-violation` (see
`PROJECT-BOUNDARIES.md`).

## Step 2 — route by KIND within the project

### context/ — internal working state (gitignored)

| Project | Home | Existing sub-homes |
|---|---|---|
| p1 | `context/expense-reconciliation/` | `expense-reports/` (statements, Chase, csv), `receipts/` (receipt images + tickets); call briefs sit at the folder root |
| p2 | `context/lead-generation/` | `Rome-Event/`, `accounts/`, `evidence/`, `outreach-assets/`, `targeting/`, `05-lists/` (raw lead archive — leave as-is) |
| client-level | `context/` root | `comms-log.md`, brand logos, `Products/` (company/product decks) |

### deliverables/ — client-facing output (tracked, committed)

| Project | Home |
|---|---|
| p2 | `deliverables/lead-generation/<theme>/` — pick the theme (below) |
| p1 | `deliverables/expense-reconciliation/` — create on the first static p1 deliverable (today p1 ships via the hosted Fly workbench, so it has none) |

**p2 deliverable themes** (sort every client-facing p2 file into one):

- `onepilot/` — OnePilot / TreasuryCentral website, blueprints, prototype, review/sign-off, vision-fit
- `rome-2026/` — anything for the Rome event (landing, one-pager, invite companies, OG/icon art)
- `aeo-outreach/` — AEO / Q&A cluster pages, forwardable one-pagers, the shadow-integration report
- `strategy/` — strategy decks, profile art, pitch artifacts

Add a new theme folder only when an artifact genuinely fits none of the four;
record the new theme in this table the same change.

### Other homes (unchanged by project-sort)

| Kind | Home |
|---|---|
| spec | `specs/{1-spec…4-live}/` named `p1-*` or `p2-*` (paused project = `a*`/`app*`, frozen) |
| automation code | `automations/{expense-reconciliation,lead-generation}/` |
| primary source (call transcript, Dirk's original functional doc) | `reference/` — never edit; revisions go into a spec |
| **ephemeral** (debug render, one-off analysis, API dump, scratch script) | **`.scratch/`** at the repo root — never under `context/` or `deliverables/`. Defer to global W2. |
| secrets / raw PII export | a gitignored path or the local vault — never committed |

## Step 3 — announce non-obvious placement

When the home isn't obvious from the request, state it in one line before
writing, e.g. `→ deliverables/lead-generation/aeo-outreach/X.html (p2,
client-facing AEO cluster)`, so a misroute is catchable in the same turn.

## Enforcement

Agent discipline at write time (this is a Layer-3 rule — it fires on recall,
not via a hook, because client-specific routing can't live in the shared
`file-placement-gate.py` without breaking client isolation). The generic gate
still catches repo-root drift, never-commit patterns, and scratch-in-tracked.

A Brisken file landing in the wrong project folder, a deliverable left flat at
`deliverables/` root, or a new file under the paused project is a friction
event (`file-placement-drift`) — log at `/comd_checkpoint`. The recurrence-kill
is to tighten this table, not to remember harder.

## Why

Established 2026-06-20 after the context/ + deliverables/ sort-by-project
reorg. Before it, `context/` mixed p1 (expense-reports, receipts) with p2
(lead-generation) at one level and `deliverables/` was a flat 21-file pile.
This rule keeps the next generated file from re-creating that mix.

Related: `PROJECT-BOUNDARIES.md` (project isolation + swap history),
`.claude/rules/rule_file_placement.md` (W2), `.claude/rules/rule_no_file_bloat.md` (W1).
