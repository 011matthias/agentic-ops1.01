# Brisken Expense Reconciliation — Remaining Build Blueprint

Single coherent plan to take the current slice-1 working tool to
"on its feet, working for Brisken."

**Scope:** Brisken only. Single tenant, 1–3 legal entities, Chris is
the only user, runs the tool monthly (or weekly). The multi-tenant
SaaS vision in v2 spec §§4–6 is deferred indefinitely per Dirk's
"working tool" directive. This blueprint plans what's needed to make
Chris's reconciliation grind go from days to minutes; nothing more.

**Not in scope:** Multi-tenant database, RBAC, audit log per v2 §25.7,
Firebase/Cloud SQL platform, mobile receipt-capture page, "Brisken
Books" replacement, web app deployment, customer onboarding flows.
All of those are real but they belong to a different product. They
re-enter scope only if Brisken later commercialises the tool.

**Hard gates that determine ship calendar:**

1. **Anthropic API access** to Brisken's Pro subscription (Dirk
   task-list item, pending). Blocks slice 2.
2. **Chris's first real-data sample** (one statement file, one receipt
   folder, one Zoho chart-of-accounts export). Blocks calibration
   work in slice 3.
3. **Zoho Books API access** OR a confirmed file-export workflow.
   Blocks slice 4.

Slices 2 and 3 can be partially built against synthetic data while
gates 1 and 2 land. Slice 4 cannot start without gate 3.

---

## Provider Pivot (2026-06-01)

The §38.2 stack decision was reversed: Brisken's LLM provider is
**OpenAI** (model: `gpt-4o-mini` for categorization, vision model
TBD for receipt OCR in slice 2b), not Anthropic Claude. The
provider-agnostic `LLMClient` protocol means the swap is one file
(`llm/client.py`) if Brisken later moves back to Anthropic, Vertex
Claude, or any other provider.

**Slice 2 part 1 (categorizer LLM) — shipped 2026-06-01.** Real
gpt-4o-mini calls behind the LD-2 strict line-item rule. Verified
end-to-end against `examples/run.with-llm.example.json`: the LLM
correctly categorizes "Coffee beans 2kg" as Office Supplies (the
keyword stub returned Meals due to substring matching on "coffee").
Cost ≈ $0.0003 per reconciliation run on the 4-receipt example;
projects to ≈ $0.015–0.06/month for Brisken's expected receipt
volume. Vision OCR for receipt extraction (slice 2 part 2) deferred
to next session.

---

## Locked Design Decisions (2026-05-31)

The decisions below were locked after a design pass with the owner.
They are binding for slice 2 + slice 4 implementation. Re-open only
on explicit redirect, with the reason logged here.

### LD-1. Eight expense categories

These are the only categories the tool assigns. New categories are
added explicitly (config change), never inferred.

| # | Category | Line-item signals |
|---|---|---|
| 1 | Travel & Transport | flights, hotels, Uber/Lyft, train, fuel, parking, tolls, rentals, mileage |
| 2 | Meals & Entertainment | restaurant items, café drinks, catering, client dinners, alcohol at meals, room-service food |
| 3 | Software & Subscriptions | SaaS line items, monthly/annual plans, "subscription", "license", AI tools, cloud (AWS/GCP/Azure), domain renewals |
| 4 | Office Supplies & Consumables | paper, pens, printer ink, cleaning, coffee/tea for office, snacks, kitchen consumables, small stationery |
| 5 | Equipment & Hardware | laptops, monitors, chairs, desks, phones, cables, peripherals, anything > ~$100 and durable |
| 6 | Marketing & Advertising | ad-platform invoices (Meta/Google/LinkedIn), sponsorships, swag, event sponsorships, branded items, marketing print |
| 7 | Professional Services | legal, accounting, consulting, contractor invoices, recruiting fees, freelancer payments |
| 8 | Utilities & Premises | rent, internet, phone/SIM, electricity, water, coworking, insurance premiums |

### LD-2. Three-tier classification rule

The classifier never reads the vendor name as input when line items
exist. Vendor is a fallback only, and fallback rows are visually
marked so Chris can confirm them.

| Tier | Source | When | Visual mark |
|---|---|---|---|
| 1 | `LINE` | Receipt has clear line items → each line classified from its description | green row, no flag |
| 2 | `VENDOR ⚠` | Receipt has no line items OR all items are vague ("Item 1", "Misc.") → vendor-based fallback | yellow row + ⚠ in Source column |
| 3 | `REVIEW` | Vendor + line items both unknown / unhelpful OR LLM confidence below threshold | orange row + "REVIEW" in Source column |

Implications:

- **Per-line categorization.** Each line item gets its own category
  from its own description. Vendor name is metadata, never a
  classifier input for tier 1.
- **One receipt → N journal entries.** A $200 Amazon receipt with
  `Office chair $150, Coffee beans $30, HDMI cable $20` becomes
  three separate Zoho journal entries (Equipment, Office Supplies,
  Equipment), all tied to the same source transaction.
- **No silent vendor assumptions.** Tier 2 rows are marked; Chris
  reviews them. The tool guesses from vendor name when forced, and
  the guess is visible as a guess.

### LD-3. Output structure — 5 + N sheets

`N` = number of credit cards being reconciled in the run.

```
[ Summary ] [ {Card 1} ] [ {Card 2} ] ... [ {Card N} ] [ Needs Review ] [ Unmatched ] [ Errors ]
```

**Sheet 1 — Summary (Chris's landing page).** Single-page dashboard.

Contents (in fixed order):

1. Run header (period, run id, timestamp).
2. Totals block (transactions, receipts, matched, needs review,
   unmatched, invariant OK/BROKEN).
3. Categorization source breakdown (count + % of Tier 1 LINE vs
   Tier 2 VENDOR vs Tier 3 REVIEW).
4. By card subtotals (spend, matched, needs review).
5. By category × by card cross-tab matrix.
6. LLM cost this run.

**Sheets 2..N+1 — One tab per credit card.** Chronological within
each tab. Same column shape as Needs Review.

Columns, in order:

| Col | Field | Notes |
|---|---|---|
| A | Date | Transaction date |
| B | Vendor | From statement |
| C | Line item | Description from OCR; "(receipt total, no itemization)" when none |
| D | Qty | Optional |
| E | Amount | Line total (sums across rows = card total) |
| F | Category | One of the 8 in LD-1; blank for REVIEW rows |
| G | Source | LINE / VENDOR ⚠ / REVIEW — drives row fill color |
| H | Zoho A/C | Suggested Zoho account from categorization |
| I | Note | FX, no-receipt, parse-warning, etc. |

Bottom of each card tab: subtotals per category + card total.

**Sheet N+2 — Needs Review.** Same column shape as the per-card
tabs, but adds a "Card" column at the front. Filtered from all
cards to Tier 2 (⚠) + Tier 3 (REVIEW) only. Sorted: REVIEW first,
then VENDOR ⚠, then by card, then by date.

**Sheet N+3 — Unmatched.** Two sections in one sheet: unmatched
transactions (top), unmatched receipts (bottom). Lets Chris
Excel-eye obvious pairs the matcher missed.

**Sheet N+4 — Errors.** Parse errors with line number, file name,
error message. Empty in clean months.

### LD-4. Row coloring drives the Source column

Excel `PatternFill` on the whole row:

- Tier 1 LINE → green (`FFC6EFCE`) — trusted, eye blurs past
- Tier 2 VENDOR ⚠ → yellow (`FFFFEB9C`) — confirm
- Tier 3 REVIEW → orange (`FFFCD5B4`) — must touch
- Unmatched transactions → red-ish (`FFF8CBAD`)

Header rows → blue-grey (`FFD9E1F2`).

---

## Current state (2026-05-31)

**Slice 1 — Working tool skeleton.** Shipped (uncommitted, awaiting
explicit ship order).

| Component | Status | Notes |
|---|---|---|
| Statement parser (CSV + Excel) | Done | `parse_statement_csv` / `parse_statement_xlsx`, 23 tests |
| Deterministic matcher | Done | `match_month`, 9 tests, 5 outcome types, reconciliation invariant verified |
| Receipts CSV ingest | Done | Slice-1 bridge; replaced by vision in slice 2 |
| LLM judgment | FX + ambiguous done | `judge_fx_match` (D1b) and `judge_ambiguous` (tie-break) both call the LLM when a client is wired (OpenAI); no-client path returns the `[STUB]` reason / leaves the tie. Never auto-resolves; both always require review and never drop a receipt. |
| Excel review report | Done | 4 sheets: Summary / Matches / Needs Review / Unmatched |
| CLI entry point | Done | `expense-recon --config run.json [--out report.xlsx]` |
| Build system | Done | Hatchling + uv; `uv sync && uv run expense-recon` works |
| Test suite | Done | 40/40 passing in 0.8s |
| Annealing register | Done | 30 items in [ANNEALING.md](ANNEALING.md) |

**Today's working contract:** Chris drops her statement file + a
receipts.csv with already-extracted receipt fields + a JSON config →
gets a 4-sheet xlsx review report. No LLM, no Zoho, no run history.

---

## Slice map — what's left

```
Slice 2 — LLM layer:    receipt OCR (Claude vision) + real judgment
Slice 3 — Robustness:   matcher quality + error handling, real-data ready
Slice 4 — Zoho output:  categorization + post-to-Zoho (API or file)
Slice 5 — Production:   Brisken-specific config + run history + deploy

Optional after MVP:
Slice 6 — Review UI:    tiny Streamlit / FastAPI for in-tool editing
Slice 7 — Mobile capture: replaces "Chris uploads receipts" step
```

Slices 2 → 3 → 4 → 5 is the critical path to MVP-for-Brisken. Slices
6 and 7 are quality-of-life on top.

---

## Slice 2 — LLM Layer (Receipt OCR + Real Judgment)

**Goal.** Chris drops a folder of receipt images / PDFs instead of
hand-extracting them into a CSV. The matcher's FX and ambiguous cases
get real Claude judgment instead of `[STUB]`.

**Gates:** Anthropic API access (BLOCKS implementation, not design).

**Deliverables:**

| # | Item | Path |
|---|---|---|
| 2.1 | Anthropic client abstraction (`LLMClient` protocol) | `src/expense_recon/llm/client.py` |
| 2.2 | Receipt vision pipeline — **Done (2026-06-10, OpenAI):** `extract_receipt` on `LLMClient`; vision for images, text-layer path for digital PDFs (pypdf) with pypdfium2 render fallback for scans; extracts header fields AND line items per LD-2, never invents items | `src/expense_recon/ingest/receipts_folder.py` |
| 2.3 | Real `judge_fx_match` body (LLM judgment call) — **Done (D1b, OpenAI):** `LLMClient.judge_fx_match` + impls, FX-convert + same-purchase verdict, 8 tests, always review | `src/expense_recon/matching/judgment.py` |
| 2.4 | Real `judge_ambiguous` body — **Done (2026-06-07):** LLM tie-break, pick annotated + promoted, all candidates kept (guarantee), 5 tests | same |
| 2.5 | Cost / token tracking per run (covers OCR + judgment + categorization calls) | `src/expense_recon/llm/cost.py` |
| 2.6 | Config schema extension (`llm:` block) | `cli.py` + JSON schema |
| 2.7 | CLI receipt-source switch (CSV vs folder) — **Done (2026-06-10):** `receipts.source` "csv"/"folder", inferred from path when absent; folder mode requires `llm:` block; `vision_model` config knob added | `cli.py` |
| 2.8 | Vision-cell unit tests with mocked client — **Done (2026-06-10):** 14 tests, CI-safe | `tests/test_receipts_folder.py` |
| 2.9 | End-to-end test with the real API (gated behind env var) — **Done (2026-06-10):** `tests/test_llm_integration.py`, skipped unless `EXPENSE_RECON_LIVE_OPENAI=1` + key; covers vision image extraction + PDF text-layer path | `tests/test_llm_integration.py` |
| 2.10 | Update Summary sheet with LLM call count + estimated cost | `report_xlsx.py` |

**Config additions:**

```json
"receipts": {
  "source": "folder",                  // "csv" | "folder"
  "path": "./receipts-may/",            // folder of .jpg / .png / .pdf
  "default_currency": "USD"
},
"llm": {
  "provider": "anthropic",
  "model": "claude-sonnet-4-6",
  "api_key_env": "ANTHROPIC_API_KEY",
  "max_concurrent": 4,
  "fail_on_no_key": true
}
```

**Vision prompt shape (per receipt) — revised for LD-2:** "Extract
date, total, currency, vendor, optional reference number from this
receipt image. **Then extract every line item: description, quantity,
unit price, line total.** If the receipt shows only a final total
with no itemization, return `line_items: []`. If a line item is
illegible, include it with `description: '(illegible)'` so the
classifier can flag for review. Return JSON matching this schema."
Structured output mode. Retry on parse failure (max 2). Costs
~$0.007–$0.010 per receipt on Sonnet 4.6 (slightly higher than
header-only OCR due to line-item extraction).

**Judgment prompt shape (per FX/ambiguous case):** "Here is a credit-
card transaction (USD $112.30, HOTEL PARIS FR, 2026-04-12) and a
candidate receipt (€98.45, Hotel Paris, 2026-04-12). Is this plausibly
the same purchase after currency conversion? Return JSON
{`match`: bool, `confidence`: float, `reasoning`: str}." ~$0.003 per
case.

**Acceptance criteria:**

- [~] `uv run expense-recon --config run.json` against a folder of 30
      receipts produces structured `Receipt` objects with ≥95% of the
      header fields populated correctly AND ≥90% of line items
      extracted with description + line_total (measured against a
      hand-labeled subset). **Coverage met (2026-06-11): 100% header
      population on the 13 real-receipt set. Accuracy not yet provable;
      no hand-labeled ground truth until Chris shares a reconciled
      month (slice 3b gate).**
- [x] (2026-06-11) Receipts with no itemization return `line_items: []`
      cleanly; never hallucinate items. Verified live: the unitemized
      service invoice in the calibration set returned 0 items while
      itemized receipts (ride-share fare breakdowns, a restaurant slip)
      returned their lines.
- [ ] All FX cases in the test fixture get real Claude judgment, not
      `[STUB]`. Judgment includes plausibility reasoning in the report.
- [ ] Summary sheet shows: `LLM calls: N, est. cost: $X.YY`.
- [ ] `ANTHROPIC_API_KEY=invalid` produces a clean error, not a stack
      trace.
- [ ] Mocked-client tests run without an API key (CI-safe).
- [x] (2026-06-11) Per-run cost stays under $1.00 for a typical
      50-receipt month. Verified by extrapolation: $0.0204 for 13
      receipts on gpt-4o-mini vision (~$0.0016/receipt) projects to
      ~$0.08 for 50, well under the cap.

**Live calibration result (2026-06-11) — slice 2.2 on real data.**
First run of the OCR pipeline against Chris's 13 real receipts
(git-ignored in `context/drafts/`; aggregate numbers only here, no
vendor/amount data committed). 13/13 extracted; the 3 non-receipt
`.md` call-briefs in the folder were routed to issues, not dropped.
Header coverage: date 13/13, total 13/13, vendor 13/13, currency
13/13, reference 12/13. Three currencies present (USD, EUR, BRL), all
detected correctly; this is the real evidence the FX-judgment path is
load-bearing for Brisken, not synthetic-only. UTF-8 vendor names
(Portuguese) round-trip intact into the extracted objects (a cp1252
console rendered them with replacement chars, but the data is clean).
One vendor name shows a probable single-character OCR misread on a
low-quality photo; that is Tier-2/REVIEW territory by design, not a
pipeline failure. Next: this set becomes the OCR baseline for slice
3b matcher tuning once Chris's statement + reconciled month land.

**Effort:** ~3–4 dev days. Parallelisable: 2.1 + 2.5 + 2.6 can land
while we wait for API access; 2.2 + 2.3 + 2.4 + 2.8 + 2.9 + 2.10 land
the day the key arrives.

**Risk:** Vision OCR accuracy on real Brisken receipts may be lower
than 95% (poor photos, unusual layouts). Mitigation: an "OCR review"
side-sheet for receipts where extraction confidence is low, before
matching even runs. Chris can correct in-place; correction persists in
the run-log (slice 5).

---

## Slice 3 — Real-Data Robustness

**Goal.** The tool survives Chris's first real month without producing
noise that makes her abandon it. This is where the ANNEALING.md items
live.

**Gates:** Chris's first real data sample (one statement + receipt
folder) — drives calibration. Can start defensive items (B1, B5)
without it.

**Deliverables in priority order:**

### 3a. Defensive (start immediately, no real-data dependency)

| # | Item | ANNEALING ref |
|---|---|---|
| 3.1 | Error-output sheet for malformed parser rows | B1 |
| 3.2 | Receipt CSV / folder dedup with explicit error | B5 |
| 3.3 | `--dry-run` flag (Summary only, no xlsx write) | B4 |
| 3.4 | `expense-recon inspect <statement>` subcommand | B2 |
| 3.5 | Structured logging via Python `logging` + `--verbose` | C3 |
| 3.6 | Example `examples/run.example.json` committed | B7 |

### 3b. Calibrated against real data (starts when Chris's data lands)

| # | Item | ANNEALING ref | Why |
|---|---|---|---|
| 3.7 | FX cross-product noise: require date + amount-band before emitting FX_JUDGMENT **[shipped 2026-06-11]** | A1 | Most cited noise source |
| 3.8 | Bipartite receipt assignment (each receipt used at most once) | A2 | Real data will hit this |
| 3.9 | Vendor fuzzy-match + reference number scoring | A3 | Tie-breaker for A2 |
| 3.10 | Refund handling (explicit bucket; pair negative-to-negative) | A5 | Likely month-1 hit |
| 3.11 | Per-bank tolerance profiles (`account_id` keyed `MatchingConfig`) | A7 | Once Chris has 2+ cards |
| 3.12 | Tip-tolerance per region (US 20%, UK 12%, EU 0%) | A6 | When EU/UK card lands |
| 3.13 | Tighten probable-match window after A3 lands | A4 | Last; needs A3 done first |
| 3.14 | Optional `--explain` flag: 5th sheet with per-tx scoring breakdown | A8 | For "why didn't this match" debugging |

**Acceptance criteria for slice 3:**

- [ ] Chris's first real month runs without a stack trace; any parser
      errors land in the "Parse errors" sheet.
- [ ] Match rate on Chris's real month ≥ 90% (deterministic only,
      before LLM). v2 spec §15.5 baseline target.
- [~] FX cases produce ≤ 2x the actual cross-currency-receipt count
      (instead of the current O(N×M) cross-product). **3.7 shipped
      2026-06-11: date + implied-rate-band gate cut Needs-Review
      pair-rows 19-21x on the three real months (10,124→545 / 6,624→337
      / 3,273→153). Now ~6x the foreign-receipt count, down from ~50x;
      the residual is per-receipt candidate collision (40 lines with
      >1 in-band candidate in March), which 3.8 + 3.9 collapse. Not
      fully at ≤2x until those land.**
- [ ] No receipt appears in two different Matches rows.
- [ ] Refunds either pair to negative-receipt counterparts or land
      cleanly in a "Refunds" outcome bucket — never get matched to
      unrelated purchases.
- [ ] All 6 defensive items (3.1–3.6) land before any real-data run.

**Slice 3b calibration result (2026-06-11) — first run on three real
months.** Bank side: Chase multi-card activity export (6 cards in one
file, 2023-11 → 2026-06) + 4 statement PDFs, landed in git-ignored
`context/` the same day. Expense side: the ER-00214/215/216 lines
(Mar/Apr/May 2026; 45+36+20 = 101 lines), extracted from the Zoho PDFs
and verified to the cent against each report's per-currency totals.
Engine ran all three months end-to-end with zero stack traces and zero
parse errors (first acceptance criterion holds on real data). Measured
baselines against the remaining criteria:

- **Match ceiling is high; deterministic floor is near zero.** A
  calibration-side alignment (date ±5d, amount within ±16% of Zoho's
  stamped USD estimate) finds a statement counterpart for **98/101**
  lines. The engine's deterministic layer matched 9 transactions
  total across the quarter, of which **at most 2 are true** (1
  certain: the month's only exact same-currency pair). Cause: ~97% of
  the expense lines are foreign-currency (BRL/EUR) on USD cards, so
  the currency-mismatch branch short-circuits nearly everything to
  FX_JUDGMENT. On this client's data profile the "FX = LLM judgment
  only" split makes the LLM load-bearing for ~95% of volume —
  inverting the "no AI where deterministic works" directive. 3.7 must
  therefore become a deterministic FX band (convert at a daily rate,
  then band-match), not merely a gate in front of the LLM.
- **FX band, empirically calibrated:** of 98 aligned pairs, 72 sit
  within 1% of the stamped-rate estimate, 84 within 3%, and the tail
  runs to 12.8% (DCC markups; receipts confirm 6–12% printed DCC
  fees). Design: ≤3% high-confidence, 3–13% DCC-suspect (review),
  >13% reject. 87/98 lines had >1 candidate inside the band, so 3.9
  (vendor fuzzy + reference) is required for uniqueness, with 3.8 on
  top.
- **Cross-product measured:** 5,064 / 3,312 / 1,639 FX pair-rows for
  months of 119 / 92 / 91 transactions — vs the ≤2×-receipts target
  (~90 pairs/month), a ~50× overshoot. A month's Needs-Review sheet
  is 10,124 rows. Confirms A1 as the top item by an order of
  magnitude.
- **Double-binding live (A2/A4/A6):** each month's single
  same-currency receipt was claimed by 4–5 different transactions
  inside the 20%/5-day probable window; only one claim can be true.
  "No receipt in two Matches rows" fails on month 1 as predicted.
- **Report-writer defect exposed:** Summary "By card Spend" and the
  invariant check count pair-ROWS, not unique transactions, so a
  $8.8K month displays as $1.26M spend and the invariant line
  false-alarms "BROKEN" while the engine-level invariant actually
  holds (per-transaction outcomes sum exactly: 115+4=119 etc.). Fix
  alongside 3.7 (new ANNEALING B-item).
- **Data-quality reality checks for ingest:** one ER line is dated a
  year earlier than its report month (manual-entry year typo); 3/101
  lines have no counterpart anywhere in the 6-card export (large
  installment-able purchase, a fuel charge) — either another
  card/account exists outside this export or payment mode is wrong on
  those lines. Mode→card mapping resolved empirically for the three
  active modes; one mode names a card last-4 with zero transactions
  in the export (likely reissued). Details in git-ignored
  `context/2026-06-11-expense-report-samples.md`.

**Effort:** 3a = ~2 days. 3b = ~4–6 days depending on what real data
surfaces.

**Risk:** Real data may surface a class of issue not in ANNEALING.md.
Mitigation: do not over-anneal before data lands. Ship 3a defensively,
then anneal 3b iteratively against actual Chris-shaped noise.

---

## Slice 4 — Zoho-Ready Output

**Goal.** The tool's output is consumable by Zoho Books with minimal
manual re-entry. This is where the "days to minutes" payoff lands —
the matching is already done in slices 2-3; this slice closes the
loop into the posting system.

**Gates:** Zoho Books API access OR confirmed file-export format.

**Deliverables:**

| # | Item | Path |
|---|---|---|
| 4.1 | Chart-of-accounts ingestion (CSV from Zoho) | `src/expense_recon/ingest/chart_of_accounts.py` |
| 4.2 | Per-line-item LLM categorizer (LD-2: line items only, no vendor input) | `src/expense_recon/categorize.py` |
| 4.3 | Vendor-fallback path for receipts with no/vague line items (LD-2 Tier 2, ⚠ marked) | same |
| 4.4 | Output rewrite for 5+N tab structure (LD-3) — Summary + per-card tabs + Needs Review + Unmatched + Errors | `output/report_xlsx.py` |
| 4.5 | Row coloring per Source tier (LD-4) | `output/report_xlsx.py` |
| 4.6 | Zoho journal-entry export — one entry per categorized line item (LD-2: one receipt → N entries) | `src/expense_recon/output/zoho_export.py` |
| 4.7 | Optional: direct Zoho Books API client (slice 4b) | `src/expense_recon/zoho/client.py` |
| 4.8 | Idempotency: don't double-post same line item (run-log integration, slice 5) | `src/expense_recon/zoho/idempotent.py` |
| 4.9 | Config extension: `zoho:` block (export path OR API creds) | `cli.py` |
| 4.10 | End-to-end tests on Zoho export format | `tests/test_zoho_export.py` |

**Categorization strategy (per LD-2):**

1. **Per-line LLM classifier.** Prompt receives the line item's
   description, quantity, line_total + the 8 categories from LD-1
   + Brisken's chart-of-accounts list. Returns
   `{category, zoho_account, confidence, reasoning}`. The vendor
   name is NOT in the prompt — line item alone drives the decision.
2. **Vendor fallback (Tier 2).** Triggered only when a receipt
   arrives with `line_items: []` OR all line items are vague
   (description matches `/^(item\s*\d+|misc\.?|service|charge)$/i`
   or shorter than 4 chars). A secondary LLM call gets vendor
   name + total + categories → category + confidence. Result
   marked `Source: VENDOR ⚠` in the report.
3. **Forced review (Tier 3).** Confidence below 0.6 on either tier,
   OR no vendor + no line items, OR chart-of-accounts lookup fails.
   Category cell blank, `Source: REVIEW`, lands in the Needs Review
   sheet for Chris to assign.
4. **Per-line cost cap.** Categorizer aggregates line items per
   receipt into a single batched Claude call to control cost
   (~$0.002 per receipt regardless of line-item count).

**Zoho export shape (option 4a — file):**

CSV columns matching Zoho Books journal-entry import format:
`Date, Account, Description, Reference#, Notes, Debit, Credit`.
**One row per categorized line item** (LD-2). A multi-line
Amazon receipt becomes 3 Zoho rows, each with a distinct account,
linked by the same Reference# (= our transaction_id). Chris
uploads the CSV in Zoho's import interface. v2 spec §21.2 fast path.

**Zoho API direct (option 4b):** `POST /api/v3/journals` per matched
transaction. Idempotency key = our transaction_id. Requires Zoho OAuth
setup. v2 spec §21.2 aligned path.

**Decision point:** start with 4a (file export — works today, no API
dependency), add 4b only if Chris finds the upload step painful after
month 2.

**Acceptance criteria:**

- [ ] Chart-of-accounts CSV ingested; the tool knows Brisken's actual
      Zoho categories and maps the 8 LD-1 categories onto them.
- [ ] **Tier 1 (LINE) accuracy ≥ 90%** on Chris's hand-categorized
      ground-truth month (per-line-item, not per-receipt).
- [ ] **Tier 2 (VENDOR ⚠) accuracy ≥ 70%** — lower bar because the
      tool admits it's guessing and Chris reviews.
- [ ] No silent vendor-based classification: every Tier 2 row carries
      ⚠ in the Source column and the category cell is editable.
- [ ] Multi-category receipt example (Amazon: chair + coffee + cable)
      produces 3 distinct rows in the report AND 3 distinct Zoho
      journal entries linked by the same Reference#.
- [ ] Zoho export CSV imports cleanly into Brisken's Zoho Books test
      org (no validation errors).
- [ ] Idempotency: re-running the same month does not produce
      duplicate journal entries (line-item-level idempotency, not
      transaction-level).

**Effort:** 4a (file path) ~2–3 days. 4b (API path) +2 days.

**Risk:** Zoho's import format may differ between regions / versions.
Mitigation: get a sample Zoho import CSV from Chris BEFORE building
4.4; reverse-engineer from the real format.

---

## Slice 5 — Brisken Production Setup

**Goal.** The tool runs reliably on Chris's machine (or a small host).
Configuration is Brisken-shaped. Run history persists so she can ask
"what did I do last month."

**Gates:** Deployment-target decision (local vs hosted). Default: local.

**Deliverables:**

### 5a. Brisken config layer

| # | Item | Path |
|---|---|---|
| 5.1 | `brisken-config/` folder in a separate private repo (NOT in this monorepo) | `<private-repo>/brisken-config/` |
| 5.2 | Per-card `run-{cardname}.json` configs with real column maps | `brisken-config/runs/` |
| 5.3 | Brisken chart-of-accounts CSV | `brisken-config/chart-of-accounts.csv` |
| 5.4 | `.env.brisken` with API keys (gitignored, distributed separately) | `brisken-config/.env.brisken` |
| 5.5 | Monthly run template: one config per (card, month) | `brisken-config/runs/template.json` |
| 5.6 | Brisken onboarding README ("how Chris runs it") | `brisken-config/README.md` |

### 5b. Run history (operationally important)

| # | Item | ANNEALING ref |
|---|---|---|
| 5.7 | SQLite run-log: one row per run + one row per tx-decision — **Done (2026-06-11):** `runlog.py`, opt-in via `run_log:` config block (no block = no file, no behaviour change); every transaction recorded incl. unmatched (guarantee carried into the log) | C1 |
| 5.8 | `expense-recon history` subcommand — **Done (2026-06-11):** list runs (newest first) or `--run <id\|prefix>` for one run's per-tx decisions; resolves db from `--config` or `--db` | new |
| 5.9 | `expense-recon diff <id> <id>` subcommand — **Done (2026-06-11):** count deltas + which transactions changed bucket (matched/review/unmatched) between two runs | new |
| 5.10 | Run-log audit columns — **Done (2026-06-11):** when (created_at UTC), who (operator), source statement path, report path, counts, LLM cost. Stores tx IDs + match types only, never account/vendor/amount data | C1 |

Slice 5b shipped with 11 tests (`tests/test_runlog.py`). NOT yet built: 4.8 line-item idempotency (guards Zoho *posting*, which stays gated; no surface until 4b lands).

### 5c. Deployment

| # | Item | Path |
|---|---|---|
| 5.11 | Local install instructions (Chris's machine, Python via uv) | onboarding doc |
| 5.12 | Optional: tiny VM deployment (Fly.io single-tenant) | deferred until Chris asks |
| 5.13 | CI workflow on the public agentic-ops repo | `.github/workflows/expense-recon.yml` |
| 5.14 | Pre-flight check command — **Done (2026-06-10):** `expense-recon doctor --config X`; read-only, no network; banded OK/WARN/FAIL over config JSON, statement file + column_map vs header, receipt source (csv/folder), `llm:`/`zoho:` env creds, output path; exit 1 on any FAIL. 14 tests | `doctor.py` |

**Onboarding flow once 5a–5c land:**

1. Chris (or her IT person) installs uv on her machine: `winget install astral-sh.uv` (Windows) or equivalent.
2. Clone the public tool repo + the private `brisken-config` repo.
3. Set `OPENAI_API_KEY` from the `.env.brisken` distributed by Matthias (provider pivoted Anthropic to OpenAI on 2026-06-01).
4. Run `expense-recon doctor --config runs/<this-month>.json`; confirms her setup.
5. Monthly: copy `template.json`, fill in the month's statement + receipts folder, run `expense-recon --config runs/2026-05-amex.json`.
6. Open the report.xlsx, review the Needs Review sheet, accept/edit categories on the Matches sheet, run the Zoho export.
7. Upload Zoho CSV in Zoho Books import interface (or `expense-recon zoho-post` if 4b shipped).

**Acceptance criteria:**

- [ ] Chris (or her IT person) can install + run the tool against a
      real month following the onboarding README, no help needed.
- [ ] Doctor command catches: missing env var, bad config JSON,
      unreachable paths, malformed column map.
- [ ] Run history: she can ask "what did we do for Amex in April"
      and the tool opens the relevant report + diff.
- [ ] CI runs on every PR to expense-reconciliation/; merging blocked
      on test failures.

**Effort:** 5a ~1 day. 5b ~2 days. 5c ~1 day. Total ~4 days.

**Risk:** Chris's machine OS / Python availability. Mitigation: doctor
command + clear "what to ask your IT person" section in the onboarding
README.

---

## Slice 6 (optional) — Review UI

**Goal.** Chris reviews and corrects in a local web page instead of
editing an Excel file. Edits write back to the run-log (slice 5b).

**Trigger to build:** Chris asks for it after month 2. Don't pre-build.

**Shape:** Streamlit single-page app reading the latest run from
run-log SQLite. Filter by sheet, click-to-edit category, mark
"confirmed" on probable matches, write back. The xlsx export still
exists as the canonical artifact; the UI is just a faster review path.

**Effort:** ~3–5 days. Streamlit makes this cheap.

---

## Slice 7 (optional) — Mobile Receipt Capture

**Goal.** Receipts flow into the tool the moment Chris takes the photo,
no upload step. Replaces the "drop a folder of images" workflow.

**Trigger to build:** Chris asks; OR Brisken decides to operationalise
this beyond Chris.

**Two paths** (per v2 spec §38.5):

- **Lovable mini-page** — bespoke mobile web page, camera capture →
  upload to a folder the tool watches. Lower setup cost; bespoke.
- **Zoho Expense integration** — receipts already flow into Zoho
  Expense; the tool reads them via Zoho API. Lower build cost; ties
  Brisken to Zoho Expense.

**Effort:** Lovable path ~3 days. Zoho Expense path ~2 days. Decision
depends on whether Brisken wants to be Zoho-Expense-dependent.

---

## Critical-path summary

```
Slice 1 (DONE)     Slice 2 (LLM)      Slice 3 (Robustness)    Slice 4 (Zoho)      Slice 5 (Prod)
─────────────  →   ──────────────  →   ───────────────────  →  ──────────────  →   ──────────────
working tool       OCR + judgment      real-data ready          posting loop        Brisken ready
[uncommitted]      [API gate]          [Chris-data gate]        [Zoho-access gate]  [local install]
                       ↓                    ↓                       ↓                    ↓
                   ~3-4 days            ~6-8 days                ~3-5 days            ~4 days
```

**Total remaining effort:** ~16–21 dev days IF gates land in
sequence. Calendar time = effort + gate-wait time.

**Parallelisable while waiting:**

- Slice 2 design / abstraction work (2.1, 2.5, 2.6) — before API access
- Slice 3a defensive items (3.1–3.6) — before Chris's data
- Slice 4.1, 4.4 design (export format reverse-engineering) — before Zoho access if Chris shares a sample Zoho CSV
- Slice 5c (CI, doctor command) — anytime

---

## Gate-resolution checklist

These are the questions to push back to Dirk + Chris this week, since
they all gate calendar:

**For Dirk:**

- [ ] When does API access to Brisken's Anthropic Pro subscription land? If >2 weeks, decision: Matthias's API key during build (Brisken billed separately) vs blocked-on-access.
- [ ] Does Brisken's Zoho Books have API access enabled? If yes, OAuth setup. If no, do we want it for MVP or stay on file-export?
- [ ] §38.1 stack decision — does this still matter? For the MVP-for-Brisken scope it's IRRELEVANT (no multi-tenant DB needed). Surface that the §38 research was for the SaaS-product scope which is now deferred.
- [ ] Deployment target: Chris's laptop, a Brisken-internal VM, or a Matthias-hosted single-tenant? Drives slice 5c shape.

**For Chris (via Dirk):**

- [ ] Share one statement file (CSV / xlsx) per card she reconciles. Even an old/anonymised month works.
- [ ] Share the receipt folder structure for one recent month (file names, formats, sources — email attachments vs photos vs paper scans).
- [ ] Share the Zoho chart-of-accounts (CSV export from Zoho).
- [ ] Share one month of already-reconciled output as ground truth.
- [ ] Sample Zoho Books import CSV (the format Zoho accepts for journal entries).
- [ ] How many distinct cards/accounts per month? (Sizes slice 5a configs.)
- [ ] Operating system on Chris's machine (Windows / macOS) — drives onboarding doc.

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Vision OCR accuracy < 95% on real receipts | Medium | High | OCR review side-sheet; manual correction loop in slice 6 |
| R2 | LLM cost per month exceeds Brisken's expectation | Low | Medium | Cost tracking in slice 2.5; per-run budget cap config |
| R3 | Chris's real data has format we can't parse | Low | High | Defensive 3.1 error sheet + 3.4 inspect command; iterate |
| R4 | Zoho import format mismatch | Medium | High | Get sample BEFORE building 4.4 |
| R5 | Matcher noise on real data is worse than expected | Medium | Medium | Slice 3b is explicitly empirical; ship → measure → tune |
| R6 | Anthropic API access never lands | Low | High | Fall back to GPT-4o or Claude via Bedrock; D1 abstraction makes this swap-able |
| R7 | Chris's IT environment blocks Python install | Low | High | Distribute as standalone exe via PyInstaller; ~1 day extra work |
| R8 | Brisken wants multi-tenant later, current MVP can't scale | Low | Low | MVP is intentionally narrow; rewrite from spec when/if that decision comes back |

---

## Done-state checklist ("on its feet, working for Brisken")

The build is done when ALL of these are checked:

- [ ] Chris runs `expense-recon --config runs/2026-XX-amex.json` on her own machine without help.
- [ ] One run takes < 5 minutes wall-clock for a typical 50-transaction / 30-receipt month.
- [ ] Deterministic match rate ≥ 90% on her real data.
- [ ] FX / ambiguous cases are LLM-judged with reasoning visible in the report.
- [ ] Every matched row has a suggested Zoho category with ≥75% accuracy.
- [ ] She can export a Zoho-compatible CSV (or post directly via API) in one command.
- [ ] She can ask "what did we do last month" and the tool answers.
- [ ] She finishes a month's reconciliation in < 30 minutes total time (down from 2-3 days).
- [ ] Tool failures produce clean error messages, never stack traces.
- [ ] Per-run LLM cost < $1 USD.
- [ ] All 30 ANNEALING.md items either resolved, struck through, or explicitly deferred with a documented reason.

When that list is fully checked, the tool is "on its feet for Brisken"
and the next decision is whether to commercialise (re-enter v2 spec
multi-tenant scope) or operate it as Brisken-internal indefinitely.

---

## How to use this document

- **Re-read at the start of every Brisken work session** until done-state is reached.
- **Tick items as they land.** Date the tick: `- [x] (2026-06-XX) item`.
- **Slice boundaries are commit boundaries.** Each slice → one PR.
- **Update slices when reality diverges.** If real data forces a re-scope, edit the slice + note the divergence reason.
- **Companion file:** [ANNEALING.md](ANNEALING.md) is the rolling punch list; this BLUEPRINT.md is the directed plan. New items found mid-build go in ANNEALING; the plan to address them goes here.
