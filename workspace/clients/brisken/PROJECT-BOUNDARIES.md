# Brisken Project Boundaries

**As of:** 2026-06-11 (third project registered: `p2` BANT lead generation, per owner directive; Dirk's offer of $300 per accepted BANT lead + commission on closed deals. Expense reconciliation remains active and untouched. Lead nurturing remains paused. See swap history at the bottom; this scope has reversed multiple times, the history ledger is the authority on what is current.)
**Status:** Three separate projects. Two active (`p1` expense reconciliation, `p2` lead generation). One paused (lead nurturing). No shared infrastructure between any of them.

This document is binding. Any future session working in this client folder must read it before touching any spec, code, or infrastructure. Because the active/paused assignment has changed several times, the **Swap history** section at the bottom is the single source of truth for which project is live right now. Do not infer it from file presence; read the ledger.

---

## Active project

**AI-assisted Expense Reconciliation platform with Zoho Books export**

- Status: active. Confirmed by the user 2026-05-17 as the project Brisken is doing. The earlier read that the Upwork offer meant lead nurturing was corrected: the offer was a separate matter; the expense reconciliation product is the engagement.
- Source functional document v1: provided by the user 2026-05-14; landed in repo 2026-05-24 at `reference/2026-05-14-functional-spec-original.md` (verbatim, preserved as primary source).
- Live artifacts (verified present 2026-05-25):
  - `reference/2026-05-14-functional-spec-original.md`; Dirk's v1 functional document, primary source, do not edit
  - `reference/2026-05-20-call-transcript.md`; full verbatim transcript, Part 1 + Part 2 (primary source)
  - `context/2026-05-20-call-outcomes.md`; structured decision extraction with transcript timestamps
  - `specs/1-spec/p1-expense-reconciliation-functional-spec.md`; v2 functional specification (binding for build decisions; supersedes v1)
  - `reference/expense-reconciliation-open-decisions.md`; 18-decision sheet, partially superseded by the call outcomes, cross-reference only
  - `automations/expense-reconciliation/`; Phase 4 deterministic matching engine + tests (v2 spec §15.1). Pure Python, stack-independent. 9 tests green (2026-05-25). See `automations/expense-reconciliation/README.md`.
- Specs (extended as work progresses): `specs/1-spec/p1-*.md`
- Code (when implementation starts): `automations/expense-reconciliation/`
- Context (when written): `context/expense-reconciliation/`
- ID namespace owned: `p1`, `p1.app1`, `p1.be1`, `p1.a1`, ...
- Stack: v1's proposed stack (FastAPI + React + PostgreSQL + Azure Blob + Azure Document Intelligence + Anthropic Claude) was reversed in part on the 2026-05-20 call: Azure Document Intelligence and Azure Blob rejected, AWS Bedrock declined as provider; Firebase / GCP is candidate for the whole platform pending the research items in v2 spec §38; Anthropic Claude confirmed via Brisken's existing Pro subscription with built-in consent + no-training conditions. The stack is genuinely re-opened.
- Open with client (current): the v2 functional spec for Dirk's review; the joint call with Chris (Brisken finance manager) once Dirk briefs her; API access to Brisken's existing Claude Pro subscription.

Sessions that name Brisken default to this project unless they explicitly state otherwise.

---

## Active project #2 (registered 2026-06-11; redirected to products 2026-06-12)

**BANT Lead Generation for Brisken's OnePilot products (`p2`)**

- Status: active, pre-terms. Registered per owner directive 2026-06-11: Dirk offered $300 per BANT-qualified lead + a commission on closed deals (offer relayed by owner; verbatim terms not yet captured; see spec Phase 0). No spend and no outbound contact until terms are settled with Dirk.
- DIRECTION (owner, 2026-06-12): Brisken does NOT want new clients for the treasury CONSULTING business (SAP Treasury Consulting / RAPSODY / Treasury Assessment). p2 sells the OnePilot PRODUCT suite (subscriptions) + AI Digital Workforce. The offer and CTA shift from a consulting engagement to a product demo. Architecture: one shared engine runs a SEPARATE CAMPAIGN PER PRODUCT (own ICP, signal, angle, product-demo CTA); 8 core campaigns (7 apps + Digital Workforce) + OnePilot for FSI as a parallel banking track. No single wedge.
- What Brisken sells (full catalog from 6 client decks, 2026-06-12, distilled to `context/lead-generation/brisken-product-catalog.md`): the OnePilot platform (Framework + 7 apps) + AI Digital Workforce + the now-out-of-scope consulting; HQ Houston, TX, USA. OnePilot for FSI (banking orchestration) is a separate, larger expansion ICP.
- Spec: `specs/1-spec/p2-bant-lead-generation.md` (plan + ICP; binding for this project).
- Code (when implementation starts): `automations/lead-generation/`
- Context: `context/lead-generation/` (terms, ICP data, evidence pack, product catalog)
- ID namespace owned: `p2`, `p2.*`.
- Relationship to the PAUSED lead-nurturing project: distinct. Lead nurturing (a0-a6) processes INBOUND leads from Brisken's existing SAP channels; p2 GENERATES outbound leads. p2 does not unpause a0-a6 and shares nothing with them. If reply-handling later wants the a3/a4 designs, that is a separate, explicit resumption decision recorded in the swap history.
- Hard constraint: no sourcing or sending infrastructure shared with any other client. Meji's Apollo seat / Sales Navigator / Instantly workspace are off-limits for this project (verified 2026-06-11: all current Apollo access is Gurmej's login-shared seat).

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

- Expense reconciliation owns `p1` and all `p1.*` sub-identifiers; new specs there use the `p1` prefix.
- BANT lead generation owns `p2` and all `p2.*` sub-identifiers (registered 2026-06-11).
- Lead nurturing owns `a0` through `a6`, plus `app1`. No new IDs in this range while paused.
- A future fourth project picks a fresh container ID (`p3`, `p4`, ...).

If a session writes a spec whose ID falls in another project's namespace, it has crossed the boundary; rewrite with the correct prefix.

---

## File path rules

| Path | Belongs to | Notes |
|---|---|---|
| `specs/1-spec/p1-*.md` | Expense reconciliation (active) | New specs for the active project go here. v2 functional spec lives at `specs/1-spec/p1-expense-reconciliation-functional-spec.md`. |
| `specs/1-spec/p2-*.md` | BANT lead generation (active) | Registered 2026-06-11; plan + ICP spec |
| `context/lead-generation/` | BANT lead generation | Terms, ICP data, evidence pack |
| `specs/1-spec/a*.md`, `app*.md` | Lead nurturing (paused) | Frozen; no edits while paused |
| `automations/expense-reconciliation/` | Expense reconciliation | Created when implementation starts |
| `automations/lead-nurturing/` | Lead nurturing | Only if that project resumes |
| `context/drafts/` | Either project | Filename must indicate the project |
| `reference/2026-04-10-call-transcript.md` | Lead nurturing (paused) | Primary source; never delete |
| `reference/2026-05-14-functional-spec-original.md` | Expense reconciliation (active) | Dirk's v1 functional document, primary source; never edit (revisions go into v2 in `specs/1-spec/`) |
| `reference/2026-05-20-call-transcript.md` | Expense reconciliation (active) | Primary source; full call transcript with Part 1 and Part 2; never delete |
| `reference/expense-reconciliation-open-decisions.md` | Expense reconciliation (active) | Pre-call 18-decision sheet; partially superseded by `context/2026-05-20-call-outcomes.md`, cross-reference only |
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

- 2026-06-12: **p2 redirected from treasury consulting to OnePilot products, per-product campaign model.** Owner directive (two steps): (1) Brisken does not want new clients for the treasury consulting business (SAP Treasury Consulting / RAPSODY / Treasury Assessment); p2 now sells the OnePilot product suite (SaaS subscriptions) + AI Digital Workforce, offer/CTA shifts from a consulting engagement to a product demo. (2) Architecture is one shared engine running a separate campaign per product (8 core campaigns + OnePilot for FSI parallel track), not a single wedge. Deep scan of 6 client product decks distilled to `context/lead-generation/brisken-product-catalog.md` (incl. the per-product campaign library); the p2 spec and the Dirk-facing strategy deck (HTML + PDF) were reframed the same day. Expense reconciliation unchanged; lead nurturing stays paused.
- 2026-06-11: **Third project registered: `p2` BANT lead generation (active, pre-terms).** Owner directive: Dirk offered $300 per BANT-qualified lead + commission on closed deals for Brisken's B2-enterprise SAP Treasury business. Plan approved by owner (evidence pack before terms call; book-meetings-only qualification; LinkedIn-first channel mix while email warms). Expense reconciliation unchanged; lead nurturing stays paused; p2 is outbound generation, not a resumption of a0-a6.
- 2026-05-25: **Build began.** Per Dirk's directive (north star: Chris's reconciliation grind days -> minutes; begin building now), Phase 4 deterministic matching engine shipped at `automations/expense-reconciliation/`. 9 tests green. Phase 4 was promoted ahead of Phase 0 because it is the value-prop core, is stack-independent, and de-risks the LLM judgment layer sizing before §38 lands. Active project unchanged.
- 2026-05-24: **Functional spec revision landed.** Dirk's 2026-05-14 v1 functional document preserved verbatim at `reference/2026-05-14-functional-spec-original.md`. Revised v2 spec written to `specs/1-spec/p1-expense-reconciliation-functional-spec.md` against the 2026-05-20 call outcomes. v2 is binding for build decisions; v1 stays read-only as primary source. Active project unchanged.
- 2026-05-17: **Expense reconciliation set ACTIVE, lead nurturing set PAUSED.** User corrected the earlier read: the Upwork offer was a separate matter, not the engagement. a0-a4 `paused: true` re-applied. Deletion of lead-nurturing context considered and rejected (primary-source transcript, repeated reversals, boundary already provides isolation). This is the current state.
- 2026-05-15: Lead nurturing set active, expense reconciliation paused, after Dirk's Upwork offer was read as describing lead nurturing. a0-a4 unpaused.
- 2026-05-15: Initial boundary created with expense reconciliation active, lead nurturing paused (user instruction to drop the old scope).
