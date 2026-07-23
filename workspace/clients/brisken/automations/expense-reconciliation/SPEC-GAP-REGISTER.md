# Expense Reconciliation: Spec-vs-Build Gap Register

**Date:** 2026-07-23
**Analyst pass:** own-session reconciliation flagged in
`docs/2026-07-23 - Expense-Recon Follow-Through/Checkpoint.md` (next-step #3).
**Anchor spec:** `specs/1-spec/p1-expense-reconciliation-functional-spec.md`
(v2.1.0, updated 2026-05-24; sections §0–§39).
**Shipped-reality authority:** `BLUEPRINT.md` + `ANNEALING.md` +
`../../status/p1-expense-reconciliation.md` + the live backend
`brisken-expense-recon.fly.dev` (read-only) + the module tree under `src/`.

Every classification below cites a PR, a file, a BLUEPRINT/ANNEALING
entry, or a live read. "MISSING" rows were checked absent in `src/`, not
assumed.

---

## The descope frame (read this first)

The spec is a **v2 multi-tenant SaaS** design. Dirk narrowed it to a
**single-tenant "working tool"** on 2026-05-27 ("We just need a working
tool. Anneal quality through real-data use, not architecture up front",
ANNEALING posture) and confirmed the standalone shape on 2026-06-12
(BLUEPRINT "Standalone realignment / Path A"). The BLUEPRINT scope block
(lines 6–16) names what that directive puts **out of scope**:

> Multi-tenant database, RBAC, audit log per v2 §25.7, Firebase/Cloud SQL
> platform, mobile receipt-capture page, "Brisken Books" replacement, web
> app deployment, customer onboarding flows. All of those are real but
> they belong to a different product.

So a large fraction of the spec is **DEFERRED by decision, not missing by
oversight.** Those rows are marked `DEFERRED` and are explicitly *not*
counted as gaps. The genuine gaps are the `MISSING` and `PARTIAL` rows
that sit **inside** the working-tool scope.

**Legend.**
`IMPLEMENTED` shipped and evidenced ·
`PARTIAL` some of the requirement shipped, a named remainder open ·
`MISSING` in working-tool scope, verified absent ·
`DEFERRED` descoped to the SaaS product (not a gap) ·
`DIVERGENT` a documented decision changed the spec's answer ·
`N/A` narrative section, no build requirement.

---

## Section-by-section register

§0 (revision history) and §39 (references) carry no build requirement and
are omitted. §1–§38 are walked below (38 requirement-bearing sections; the
"28" in the task brief was an approximation).

| § | Requirement | Status | Evidence | Note |
|---|---|---|---|---|
| 1 | North-star: multi-day grind → ~15 min/month, 99% automated | PARTIAL | BLUEPRINT done-state checklist (all unchecked); status "Criss has not used the tool since 2026-07-20" | Engine that enables it is built; the outcome is unproven. No Criss-completed full month on the tuned matcher; run `b67133b8df98` is the pre-accuracy-program 0/94 baseline. |
| 2 | AI-native reconciliation assistant (MVP) | IMPLEMENTED | matcher + categorizer + review workbench + Zoho export, all shipped | The MVP half of the vision is the built product. |
| 2 | Long-term "book of record" direction | DEFERRED | BLUEPRINT not-in-scope | Brisken Books; §36. |
| 3 | Core business problem statement | N/A | narrative | No build requirement. |
| 4 | Multi-tenant + multi-entity + RBAC hierarchy (owner/admin/legal-entity-admin/process-user/viewer) | DEFERRED | `web/auth.py`: `ROLES = (ROLE_OPERATOR,)`, one shared `EXPENSE_RECON_OPERATOR_CODE`; PR #350 stripped role plumbing | Verified absent. Single operator is the whole model. Descoped, not a gap. |
| 5.1 | Statement upload (CSV/Excel) | IMPLEMENTED | `ingest/statement_csv.py`, `statement_xlsx.py`, `statement_pdf.py` | Exceeds spec: PDF statement path added (carries per-charge FX). |
| 5.1 | Receipt/invoice browser upload | IMPLEMENTED | web intake (`web/app.py` `/api/intakes`); `ingest/receipts_folder.py` | |
| 5.1 | Mobile receipt-capture page | DEFERRED | BLUEPRINT not-in-scope; slice 7 optional; no mobile module in `src/` | §5.1 item 4, §27.5. Descoped. |
| 5.1 | OCR / receipt extraction | IMPLEMENTED | `receipts_folder.py` (vision) + `expense_report_pdf.py` + `expense_report_images.py` (PR #315) | |
| 5.1 | Hybrid matching (deterministic + LLM judgment) | IMPLEMENTED | `matching/deterministic.py` + `matching/judgment.py` | The most mature subsystem; see §15. |
| 5.1 | AI classification vs chart of accounts | IMPLEMENTED | `categorize.py` (LD-2 per-line) + `ingest/chart_of_accounts.py` + `coa_gate.py` | |
| 5.1 | Spreadsheet-like review table, mass-edit | IMPLEMENTED | web review-workbench (Slice 9) + xlsx report; `/api` mutation parity PR #318 incl. bulk decide | Review surface evolved to a web workbench + xlsx export; the "grid" concept is served by both. |
| 5.1 | Approval workflow (review-everything default) | IMPLEMENTED | §16 export-approved gate PR #297; §17 disposition PR #296 | Configurable automation (§14) is planned, default-OFF. |
| 5.1 | Posting/replication to Zoho (file export MVP) | PARTIAL | `output/zoho_export.py` journal CSV (8.5) shipped | Live Zoho API POST (4b) gated on Zoho access; see §21. |
| 5.1 | Receipt linkage end-to-end (single store) | IMPLEMENTED | `hosting/store.py` content-addressed; receipt URL carried into export (8.4/8.5) | Storage architecture diverges from the literal single-DB spec; see §9. |
| 5.1 | Reconciliation guarantee | IMPLEMENTED | `test_reconciliation_guarantee_invariant_holds`; invariant OK on all real months | See §25.5. |
| 5.2 | Release 2 (live Zoho API, direct receipt-to-Zoho, auto-approval thresholds, email ingest) | DEFERRED | post-MVP by spec | Not working-tool scope yet. |
| 5.3 | Release 3 (bank aggregators, more formats, cloud-folder watch) | DEFERRED | BLUEPRINT not-in-scope | |
| 6 | Zoho Books, Expenses object, 1:1 journal replication mapped to Zoho GL | PARTIAL | `zoho_export.py` + `coa_gate.py` (1,252-account chart) + `card_accounts` map | File-export replication built + GL-mapped; live API replication gated. Internal model decoupled from Zoho template: IMPLEMENTED. |
| 7 | MVP single-format CSV/Excel, read as structured columns | IMPLEMENTED | `statement_csv.py`/`_xlsx.py` config-driven `column_map`; PDF added | Exceeds spec (three statement sources). |
| 8 | Receipt sources: browser upload + mobile camera; JPEG/PNG/PDF | PARTIAL | browser + vision + PDF built; mobile camera DEFERRED | Also added: Zoho ER-PDF ingest (`expense_report_pdf.py`, PR #263) as a lighter Zoho-Expense path. |
| 9 | Single store (structured + receipt files in same DB) | DIVERGENT | SQLite `web/store.py` for run data + content-addressed file store on the Fly `/data` volume | The strict single-DB rule was itself flagged as a §26.3 tension and belongs to the deferred SaaS platform; the working tool keeps both on the same private `/data` volume (`fra`). |
| 9.1 | Per-jurisdiction retention config | MISSING | 0 matches for `retention` in `src/`; status open gate ("legal retention to confirm") | Real gap; low urgency for an internal tool, real for commercialization. |
| 10 | Required accounting fields (date/vendor/amount/account/currency/expense-account) | IMPLEMENTED | `matching/types.py` + `zoho_export.py` columns; extra fields retained on `Receipt` | VAT correctly omitted for MVP. |
| 11 | VAT/tax as metadata only, not required MVP | N/A | matches spec (deferred by design) | Correctly not built. |
| 12 | Recognize DE/EN/PT; translate to English | PARTIAL | BLUEPRINT slice-2 calibration: PT vendor names round-trip; 3 currencies detected | Multilingual OCR works; an explicit translate-to-English field layer is not built (not needed for management reporting). |
| 13 | AI classification: not static-table, deterministic-first, signals, output (account/confidence/reasoning/alt/warning), learning from corrections | IMPLEMENTED | `categorize.py` LD-2; `learning/` merchant_category (Slice 9); REVIEW tier + provenance | §13.4 learning path live. |
| 14 | Configurable automation: review-all → trust-graduated → thresholds | PARTIAL | default review-everything is current behavior; status marks §14 configurable automation "planned" | Trust-graduated / threshold config is planned (Phase 6, default-OFF), not built. |
| 15 | Matching engine (deterministic layer, LLM FX judgment, date logic, outcomes, confidence) | IMPLEMENTED | `deterministic.py` + LD-5 params + FX bands + `judgment.py`; card signal PR #317; accuracy program PRs #404/#405/#406 | Most annealed subsystem; deterministic-correct 3/95 → 55/95, 0 wrong (ANNEALING 2026-07-23). |
| 15.5 | Confidence thresholds (TBD in spec) | IMPLEMENTED | pinned scorer `recon-match-accuracy` + tuned defaults (PR #406) | Spec's "TBD" resolved by the measured accuracy program. |
| 16 | Review table: preview, inline edit, approval actions incl. mass-approve, statuses | IMPLEMENTED | web workbench: confirm/reclassify/manual-match/commit-memory; PR #318 bulk decide; statuses via outcome buckets | |
| 17 | Personal vs business flags + reimbursement | PARTIAL | §17 disposition backend PR #296 (`/api/runs/{id}/disposition`) | Exact Zoho reimbursement posting mapping is a Zoho-access discovery task (spec §17/§31), gated. |
| 18 | Duplicate detection (flag, side-by-side, merge/ignore) | IMPLEMENTED | `duplicates.py`; §18 resolve PR #298; run detail carries `duplicate_groups` | |
| 19 | Multi-receipt / split cases (MVP simplified) | PARTIAL | per-line split across categories (one receipt → N journal entries, LD-2) built | Multi-receipt-per-transaction and split business/personal are not first-class; spec itself left this "to confirm with Chris". |
| 20 | Three-layer currency (transaction / account-card / book) | PARTIAL | 3-layer docstrings on `types.py` (E7); FX path live | LD-5 collapsed the account-card layer to USD (Brisken has no EU/UK card); per-entity configurable book currency is tied to multi-entity (deferred). FX (transaction ccy ≠ USD) is the live, heavily-built path. |
| 21 | Zoho integration: API journal replication; file-export MVP fast-path; receipt attachment | PARTIAL | file export IMPLEMENTED (`zoho_export.py`); `zoho/client.py` exists (`list_expenses`); POST /journals (4b) gated | Receipt URL + report reference carried in the export; push-onto-the-Zoho-record gated on API access. |
| 22 | Chart of accounts: hierarchical; manual/upload/edit/map to Zoho GL | PARTIAL | COA ingest + validation gate (`coa_gate.py`, PR #202/#203/#205) live | Category-management UI is the emerging master-data settings work (settings API live; SPA settings screen published/live). Maps to Dirk note #2. |
| 23 | Data model (Tenant/User/Role/Scope) | DEFERRED | single-tenant, single operator | |
| 23 | Data model: LegalEntity, FinancialAccount | PARTIAL | `card_entities` {2838→Corporate Services} + `card_accounts` maps; `store/statements.py` per account | Card→entity/account maps, not managed entity/account objects with responsible-user or RBAC scope. |
| 23 | Data model: Statement, Transaction, Receipt/Document | IMPLEMENTED | `store/statements.py`; `matching/types.py`; `hosting/` | |
| 23 | Data model: ExpenseRecord/JournalEntry, ChartOfAccountsNode, ZohoMapping | PARTIAL | journal rows in `zoho_export.py`; COA JSON ingested; `card_accounts` map | Not persisted double-entry journal / full mapping objects. |
| 23.13 | AuditLog | PARTIAL | `runlog.py` (run + per-tx decision log, who/when/source, PR #109) | Covers approval/decision audit; role-change + retention-deletion audit (§25.7) deferred with RBAC/retention. |
| 24 | Four-component pipeline (OCR / deterministic match / LLM judgment / web framework), kept separate | IMPLEMENTED | `ingest`+`llm/client` / `matching/deterministic` / `matching/judgment` / `web/` | Clean match to the spec's component separation. |
| 25.1 | Accuracy/transparency (mark uncertain, never invent) | IMPLEMENTED | REVIEW tier; "unknown → visible placeholder, never a guess" (status); B4 discipline throughout | |
| 25.2 | Performance (monthly statement without one-by-one) | IMPLEMENTED | batch pipeline; BLUEPRINT <5 min target | Not formally load-tested; real months (84–203 charges) run clean. |
| 25.3 | Security (auth, encrypted transport/storage, key mgmt, tenant/scope isolation) | PARTIAL | login + bearer + throttle (`ratelimit.py`, PRs #367/#369); HTTPS (Fly); OpenAI key via env | "One shared operator code is still the whole boundary" (status). Tenant/entity/account scope isolation deferred with RBAC. |
| 25.4 | GDPR/privacy (deletion rights, data export, minimization, retention, documented processors) | MISSING | 0 matches for `gdpr`/`consent`/`anonymi`/`retention` in `src/` | Real gap; F9 delete-run is operational cleanup, not a GDPR deletion workflow. Low urgency internal, real for commercialization. |
| 25.5 | Reconciliation guarantee (zero transactions lost) | IMPLEMENTED | invariant test + Summary assertion; OK on all real months | The crown-jewel NFR; held through every anneal. |
| 25.6 | AI per-use consent prompt + no-training guarantee | PARTIAL/DIVERGENT | 0 matches for `consent` in `src/`; provider pivoted to OpenAI (BLUEPRINT Provider Pivot) | Per-use consent prompt (spec calls it non-negotiable) NOT built. No-training posture shifted from Anthropic-Pro to the OpenAI API tier and has not been re-documented against the spec's guarantee. |
| 25.7 | Auditability from day 1 (approvals, overrides, posting attempts, role changes, retention deletions) | PARTIAL | `runlog.py` + decision/override tables cover approvals/overrides/posting | Role-change + retention-deletion audit deferred with RBAC/retention. |
| 26 | Re-opened stack (multi-tenant, single store, Anthropic via Brisken Pro, GCP/Firebase candidate) | DIVERGENT/DEFERRED | working tool is Python/FastAPI on Fly.io; provider = OpenAI; GCP candidate not adopted | The whole re-opened stack question was rendered moot by the working-tool descope ("§38.1 stack decision... IRRELEVANT for MVP-for-Brisken", BLUEPRINT). Effectively resolved to §26.5's "conventional Python web framework" fallback. |
| 26.4 | Anthropic Claude via Brisken Pro | DIVERGENT | Provider Pivot 2026-06-01 → OpenAI `gpt-4o-mini` | Provider-agnostic `LLMClient`; swap is one file. Documented decision, not a gap. |
| 27.1 | Sign-in screen (tenant-scoped) | PARTIAL | single-code login | Not tenant-scoped (single tenant). |
| 27.2 | Dashboard (counts per status, scoped) | IMPLEMENTED | `/api/operator/state` + SPA dashboard; F3 processing PR #410 | |
| 27.3–27.4 | Statement upload + receipt upload screens | IMPLEMENTED | web intake | |
| 27.5 | Mobile capture page | DEFERRED | descoped | |
| 27.6 | Reconciliation review table (main screen) | IMPLEMENTED | web review-workbench | |
| 27.7 | Posting/export screen | PARTIAL | export CSV download built; Zoho post gated | |
| 27.8–27.12 | Settings screens (chart of accounts / accounts+entities / users+access / automation policy / Zoho mapping) | PARTIAL | settings API live (`fx_reference_rates`+`card_entities`+`card_accounts`); SPA settings screen published/live (chunk `settings-CsopqaDN.js`) | Users+access screen DEFERRED (no RBAC); automation-policy screen PLANNED (§14). This cluster is exactly Dirk note #2. |
| 28 | Automation-policy configuration fields | PLANNED | §14; not built (default-OFF) | |
| 29 | Error handling + warnings (flags) | IMPLEMENTED | Errors sheet (B1); `ParseIssue`; COA-gate diversions; FX/missing-receipt/duplicate flags | |
| 30 | MVP success criteria (9) | PARTIAL | criteria 2–8 enablers built; criterion 1 (multi-tenant/RBAC) DEFERRED; criterion 9 (time-on-task, zero lost) UNPROVEN | The business test ("Chris runs a real month") has not happened on the tuned tool. |
| 31 | Open questions (split, VAT display, Zoho reimbursement map, thresholds, auto-approve) | PARTIAL | thresholds → accuracy program; auto-approve → §14 planned; split → per-line built; VAT/reimbursement → deferred/gated | |
| 32 | Implementation order (Phase 0–8) | DIVERGENT (acknowledged) | §32 build-state note (2026-06-07, E4): slice-based, value-core front-loaded | Phases 2–7 logic built slice-wise; Phase 0 (multi-tenant/RBAC) deferred; Phase 8 full-month replay approximated by the labeled-fixture accuracy program, not a Chris-run month. |
| 33 | Developer deliverables (architecture/schema/wireframes/API/roadmap/risks/cost) | PARTIAL | BLUEPRINT + ANNEALING + spec + cost figures; the SPA is the working UI | No separate wireframe/clickable-prototype artifact; folded into the working tool. |
| 34 | Key product principles (12) | IMPLEMENTED | deterministic-first, guarantee, receipt-linked, never-invent, Zoho-target all hold | Naming ("expense" is wrong) is cosmetic, retained. |
| 35 | One-sentence developer brief | PARTIAL | reconciliation core built; multi-tenant/RBAC/mobile parts deferred | The brief describes the SaaS; the tool is its single-tenant core. |
| 36 | Long-term vision (Brisken Books, double-entry, invoice issuing, aggregators) | DEFERRED | BLUEPRINT not-in-scope | |
| 37 | People & process (Chris key user; Dirk brief → joint call → cadence; Dirk visibility) | N/A (mostly) | joint call with Chris not yet scheduled (status open gate); feedback widget gives Dirk visibility | Process, not build. Criss (Cristiane Cavalcanti) is live and has left feedback. |
| 38 | Open research items (stack-gating) | SUPERSEDED | working-tool descope moot-ed §38.1–38.4; provider pivot moot-ed 38.2–38.4 | §38.5 mobile scanning deferred; §38.6 legal retention still open (real). |

---

## Where Dirk's 4 live-feedback notes map

Pulled read-only from `GET /feedback.jsonl` on `brisken-expense-recon.fly.dev`
(operator, 2026-07-20, verbatim below). These four are the reason this
register exists; note #4 is answered by the register as a whole.

**Note 1: "the flow is backwards" (17:16).**
> "the process starts with collecting receipts and creating expenses.
> then, after month end, a statement is loaded to now reconcile the
> statement against the receipts and related expenses in the system.
> Starting this way is a little bit backwards - and leaves the user in
> the dry, it appears to be a cryptic technical job to now find a
> statement and upload it...."

Maps to the pipeline **entry model**, not the matcher. The app's entry
point ("Reconcile a month" → upload a statement) makes the statement the
first artifact. Dirk's real-world model (and the spec's §2/§5/§8 vision)
is expenses/receipts accumulating continuously, with the statement load
as the month-end reconcile step. **Verdict: real workflow gap**, partly
overlapping the deferred continuous-capture surfaces (mobile capture §5.1,
Zoho Expense pull §21). It is a front-of-pipeline product decision, and
nothing in the matching engine has to change to fix it.

**Note 2: settings / master data (17:20).**
> "we need a setting and master data section where rules and master data
> are cerated and maintained - legal entities, banks, bank accounts,
> expense categories, available currencies, fx rates (pull them from a
> source), etc. -"

Maps to spec §22 (COA), §23 (LegalEntity/FinancialAccount), §20
(currencies), §27.8–27.12 (settings screens). **Mostly addressed since
the note:**
- The settings backend is live and manages `fx_reference_rates`,
  `card_entities`, `card_accounts` (`web/store.py` `SETTINGS_DEFAULTS`;
  `GET/PUT /api/settings`, set live 2026-07-23).
- The SPA settings screen is **published and live** on
  `brisken-reconcile-dash.lovable.app` (verified 2026-07-23: the deployed
  chunk `settings-CsopqaDN.js` carries the master-data editor with
  `fx_reference_rates` / `card_entities` / `card_accounts` / legal-entity /
  reference-rate fields). An earlier "merged-not-published" read was
  corrected the same day.
- Two real remainders: **fx rates "pull them from a source" is not built**
  (rates are a manual map + per-run self-derivation; code comments say the
  authoritative rate source is "§38-TBD"; no external rate API in `src/`);
  and the **entity / bank / account model is card-scoped maps** (card→entity,
  card→account) rather than full first-class managed objects for banks,
  accounts, and currencies.

**Note 3: Zoho Expense auto-pull (17:21).**
> "connect it to Zoho expense and pull this in automatically - any receipt
> scanned and expense created shows up here..... - then manual additions -
> need UI, upload receipt, enter value, parse info and fill in details,
> etc."

Maps to spec §5.1 item 4 fallback, §8.1, §21, §38.5. **Partly built:** the
lighter path shipped (read the Zoho ER-NNNNN report PDF Chris already has,
`expense_report_pdf.py` PR #263, no API needed). The **live Zoho Expense
API auto-pull is not built** and is gated on Zoho token expense-scope
re-consent (status open gate #2). The **manual-add UI** (upload one
receipt, enter value, parse, fill) is partial: intake upload exists, a
single-receipt guided add-and-parse flow is not the primary path.

**Note 4: "I do not see the long requirements and functional design
document reflected in this" (17:22).**

This is the meta-note, and this register is its answer. The honest reading:
- **The spec's engine is deeply reflected, arguably over-delivered:**
  matching, FX judgment, categorization, the reconciliation guarantee,
  duplicate detection, review, Zoho journal export (§13–§18, §21, §24,
  §25.5, §29). Those are the built product.
- **What Dirk was looking at when he wrote this is the spec's front-end
  structure, which is thin or invisible:** the settings/master-data
  surfaces (note #2), the continuous expenses-first workflow (note #1),
  and the Zoho Expense ingestion (note #3). Notes #1–#3 *are* the concrete
  content of note #4.
- **And the spec itself was never reconciled to the build.** ANNEALING E4
  ("Spec divorced from build state") has been open since 2026-06-07: the
  spec still reads as a multi-tenant SaaS with Phase 0 (multi-tenant + RBAC)
  first, so a reader expecting that platform genuinely "does not see it
  reflected", because it was deliberately descoped, and the spec was never
  updated to say so. Half of note #4 is a **documentation gap**, not a
  build deficiency.

(Two earlier notes from Criss, the user, on 2026-07-16, are adjacent and
worth carrying: "there needs to be an option to remove a file placed wrong
and replace it", addressed by F9 delete/intake-reset, PR #410; and "the
receipt photo needs to be downloadable to be used", the receipt-image
read, PR #315, plus the hosted receipt URL. Both PT-language, translated
here.)

---

## Close-the-gap shortlist (real gaps vs descoped)

### Real gaps, prioritized (inside working-tool scope)

1. **Reconcile the spec to the build** (small, documentation). Add a
   working-tool section to the spec (or a v3) stating the single-tenant
   descope and the slice-based order, closing ANNEALING E4. This is the
   most direct answer to note #4's "I don't see the doc reflected", and
   half of that note is the doc being stale. **Do this first** (nothing
   else needs building for it, and it is what note #4 literally asks).
2. **Reframe the entry workflow to expenses-first** (note #1, medium,
   product). Make expenses/receipts the accumulating primary surface and
   the statement load the month-end reconcile step, so the operator is not
   dropped into "find and upload a statement" as step one.
3. **FX rate auto-pull from a source** (note #2, medium, build). Add an
   external reference-rate fetch to replace the manual `fx_reference_rates`
   map; the self-derived per-run rate stays as fallback. The rest of note
   #2 (the master-data settings surface) is already shipped and published.
4. **Live Zoho Expense auto-pull** (note #3, medium/large, gated). Build
   the Zoho Expense API ingest; gated on the token expense-scope re-consent
   (owner gate #2). The ER-PDF path is the interim.
5. **Per-use AI consent prompt (§25.6)** (small/medium, build). The spec
   marks it non-negotiable; it is not built. Pair with a short written
   no-training posture note for the OpenAI provider.
6. **Manual expense-add UI** (note #3 second half, medium). Guided single
   receipt: upload → parse → fill → add.
7. **Chris-validated full month (§30.9, §8, done-state)** (validation, not
   build). Send Criss the SPA URL + operator code (owner) and have her run
   a real month on the tuned matcher; this is the only thing that turns the
   north-star from "enabled" to "proven".
8. **Live Zoho API journal posting (4b) + line-item idempotency (4.8)**
   (medium, gated on Zoho access). File export is the interim.
9. **Retention config + GDPR deletion (§9.1, §25.4)** (low urgency
   internal, prerequisite for any commercialization).

Items 1, 2, 3, 5, 6 need no external gate and are the fastest path to
making Dirk's four notes visibly answered. Items 4, 7, 8 wait on an owner
action (Zoho re-consent, send-Criss-the-link).

### Descoped, not gaps (do not build unless commercializing)

Per Dirk's "working tool" directive (BLUEPRINT scope block); listing them
so they are not mistaken for gaps against the v2 spec:

- Multi-tenant database + tenant/user/role/scope data model (§4, §23, §26)
- RBAC hierarchy and per-entity/account scope enforcement (§4, §25.3)
- Mobile receipt-capture page (§5.1, §8.1, §27.5, slice 7)
- Firebase / Cloud SQL / GCP platform and the whole re-opened stack
  research (§26, §38.1–§38.4); superseded by the Fly/FastAPI working tool
- Brisken Books: double-entry book of record, GL-hierarchy posting, light
  invoice issuing (§2, §36)
- Live bank/card aggregator connectivity (§5.3, §36)
- SaaS web-app deployment + customer onboarding flows (§26)
- Full audit log for role changes / retention deletions (§25.7, the parts
  tied to RBAC and retention)

### Divergences (documented decisions, not gaps)

- **LLM provider: Anthropic Claude → OpenAI `gpt-4o-mini`** (Provider Pivot
  2026-06-01). Provider-agnostic `LLMClient`; supersedes §26.4 and moots
  §38.2–§38.4.
- **Storage: single-DB → SQLite + content-addressed volume store** (§9);
  the strict single-store rule was a flagged §26.3 tension belonging to the
  deferred platform.
- **Account-card currency layer collapsed to USD** (§20, LD-5): Brisken has
  no EU/UK card; every card settles USD.

---

## One-line answer to note #4, for Dirk

The engine the spec describes is built and, on matching/FX/categorization,
past what the spec asked for. What the spec leads with, the multi-tenant
SaaS platform, was deliberately set aside to ship a working tool, and the
spec was never updated to say so. The settings/master-data surface Dirk
asked for is now built and published; what is genuinely still thin inside
the working tool is the expenses-first workflow, the fx-rate auto-pull, the
live Zoho Expense pull, and the AI consent prompt. Those, plus updating the
spec itself, are the list above.
