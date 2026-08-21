---
project: brisken
workstream: p1-expense-reconciliation
kind: improvement-backlog
state: active
updated: 2026-08-21
---

# Expense tool: improvement backlog (the one list)

Every improvement idea for the receipt-first expense tool lives HERE and
only here. The status file (`p1-expense-reconciliation.md`) records what
shipped; this file records what we think should happen next and why. When
an item ships, move it to the "Shipped" section at the bottom with its PR
number. New ideas from any session get appended here, never scattered
across checkpoints or chat.

Ranking rule (from the loop brief): wrong money beats wrong text, things
that stop the tool from learning beat cosmetics, and anything Criss would
have to hand-fix every month beats a one-off.

## Open

### The 2026-08-21 feedback wave (14 notes, sequencing decided)

The operator walked the whole tool on 2026-08-21 and left 14 notes via the
in-app widget (the first full wave since capture went global, iteration 7).
Every note maps to a planned PR round; the user picked cards-first
sequencing the same day. Items 10-17 below are that wave; the cards
program is item 10. Full design: the 2026-08-21 plan (checkpoint folder).

### 10. Cards as first-class identities, Zoho-independent (notes 1/6/9/11)

**Owner direction:** "cards do not need zoho accounts... we must create
our own identification system"; stop asking for the legal entity at batch
creation — lay out the card identities, let the user assign each to an
entity once, learn it.

**The design fact that drove the model:** one physical card carries TWO
digit identities (Chase statement marker "2838", plastic last-4 "1672";
Zoho labels print both). The last4-keyed map could never resolve
"Visa ...1672" — the January batch's 13 unassigned rows are this bug.

**Rounds:** R1 registry + read-time composition (settings `cards` key,
GET /api/cards, zero behavior change) — SHIPPED PR #555; R2 Zoho decoupling
(per-card OPTIONAL warning wording, conservative export resolution:
bare-digit keys resolve labels, ambiguity placeholders, merchants
inert-hint, dropdown relabels answering notes 5/7) — SHIPPED PR #556; R3
entity-less batch + card-review strip + hint-to-card assignment that
persists ("learning") + refresh-master-data endpoint (snapshot-trap fix)
— SHIPPED PR #559 (3-lens adversarial review; every HIGH fixed + pinned:
single-digit-run learn rule, compound/DE generic tenders, ambiguity
blocks the paid-through flat map, graduation bakes chain entities —
pre-fix an assigned entity-less batch reconciled 0 silently; restore +
attach final-write now serialized under the batch lock. Lovable half:
`docs/lovable-cards-r3-prompt.md`, owner applies); R4 mixed-entity
export + persisted migration (pending owner answers: per-entity export
files? cash/personal tenders as cards? per-entity zoho_account?).

**R3 review residue (logged, not built):** re-stamp semantics after a
registry correction (stale ingest-stamped entity shows source "learned";
chain + provenance make it visible, operator overrides per row — design
call whether refresh should re-stamp, vs memory-origin stamps);
settings PUT whole-map RMW race (single-operator, cosmetic); GET->PUT
settings round-trip 400s if a generic alias was stored PRE-R3 behind the
API (read-side the alias is inert; verify prod settings clean at
deploy); assignment during an in-flight attach match window is not baked
into that match (assignments happen on the batch page pre-attach in
practice; the pool-based mismatch warning fires on a 0-match outcome).

**Export policy (user ruling 2026-08-21):** unresolved card/entity never
blocks an export — placeholders, adjustable later, re-export folds it in.

### 11. Intake: delivered files + Month column + delete month (SHIPPED — PR #561)

Shipped with the delete-month cascade (note 2, which had no own item) as
the quick-wins round; see the Shipped table row 9. Review residue worth
knowing: item 18 below (pre-existing async lock acquirers), and the
stranded-mail design call folded into item 12.

### 12. Body-only mail handling (SHIPPED — see Shipped row 10)

Shipped: sanitized body view, body-to-PDF render through the normal
pipeline, per-mail dismiss. The leftover design call moved to item 19.

### 19. Re-ingest for attachment mail stranded by a deleted month (owner call)

From the delete-month review (2026-08-21): a mail with ATTACHMENTS
already ingested into a month that is later deleted has no re-ingest
path if the operator recreates the month — replay skips status
`ingested`. The bytes survive in the custody archive (`parts/`), so
this is stranding, not loss. Natural fix: a per-archive "re-ingest into
the open month" action beside the shipped view/render/dismiss (explicit,
so receipts never drain into an unintended month). Needs an owner
ruling on whether the case is worth the surface; body-only mail already
recovers via render.

### 13. Learned memory: validate + adjust (SHIPPED — see Shipped row 11)

Shipped: PUT/DELETE per row, validation stamps + unvalidated filter,
reset confirm gate. NOTE: the live SPA's Reset button is a silent no-op
until `docs/lovable-memory-edit-prompt.md` is applied (fails closed).

### 14. Language contract: stable codes, SPA localizes (note 4)

The note's trigger ("Taxa de entrega") is extracted receipt DATA — right
to stay in receipt language. The real leaks: two reason codes with no
i18n key fall through to English prose, missing_fields interpolates
English field names server-side, parse/upload/restore sentences are
un-localizable free text, "(uncategorized - assign)" renders inside PT
lines. Fix: codes + structured payloads beside the prose; SPA maps them;
mark extracted-data fields visually.

### 15. Receipt column tells the truth (note 8)

`receipt_image_available` is True for every `manual:` id — a manual
expense with no file renders a View button that 404s; the empty state
says "No image" (reads as preview-broken, not receipt-missing); the
missing-receipt tile is computed and never displayed. Fix: honest
`receipt: {has_document, image_available}` contract + the tile + row
source-file identity.

### 16. Rejected matches need a "what now" (2026-07-27 note, untracked)

STATUS_REJECTED sends the transaction back to unmatched and is reversible
pre-export, but no rejected bucket exists in the API and no affordance
answers "what happens to rejected matches?". Spec fresh.

### 17. Workbench filter/sort (2026-07-27 note, untracked)

"There should be a filter somewhere: alphabetic, unmatched elements."
Natural home: the grouped-queue render (PR #454/#455's remaining Lovable
half). Spec with it.

### 18. Async endpoints acquire the batch lock on the event loop (pre-existing)

Found by the delete-month adversarial review (2026-08-21): the delete
handler was fixed (kept sync), but `restore-set-aside` and the cards
assignment endpoint are `async def` and take `_BATCH_ADD_LOCK` directly —
while an OCR ingest holds that lock for minutes, either call parks the
EVENT LOOP and freezes every endpoint including `/healthz` (Fly health
checks fail, machine restart kills the in-flight ingest). Fix is
mechanical: make them sync (threadpool) or wrap the locked span in
`run_in_threadpool`. Small, ship with the next code round. Also worth a
one-line comment at `_BATCH_ADD_LOCK` that scale-out past one process
breaks the serialization model (single-machine volume pin makes it safe
today).

### 3. Put the set-aside statement pages to work (later)

**What happens today:** statement pages found among the receipts are set
aside and that is the end of it.

**Why it matters (eventually):** those pages are exactly what the OTHER
half of the tool (statement reconciliation, Mode B) needs as input. Criss
uploading them "wrong" is actually her handing us the month-end statement
early.

**The fix, someday:** offer set-aside statements to the statement side of
the same batch instead of only quarantining them. Do this only after the
statement-attach flow is in daily use; until then it is speculative.

**Status:** idea, deliberately not scheduled.

### 4. Category flips on identical inputs (watch, do not build yet)

**What happens today:** the reading cache (shipped 2026-08-15) pins what
the AI SEES on each photo, but the categorize step still asks the AI
fresh every run. Across the August test runs the same PagBank receipt was
filed three ways on three days (no category, "Professional Services",
"Software & Subscriptions") while its money never moved. In the two
back-to-back runs after the cache shipped, categories came out identical
both times, so with pinned inputs the wobble may be rare in practice.
2026-08-16 check: a third smoke10 run (R7) came out byte-identical to
R6, categories included; the watch stays quiet. 2026-08-18 (round 5):
the May fresh-read pair showed one category change, but it was caused by
the item-6 vendor flip (bank-as-vendor carries no category signal), not
by categorize-call wobble on a pinned input — the watch condition has
still never fired.

**Why it might matter:** a category that flips between runs creates the
same trust problem as a vendor spelling that flips. But the merchant name
book and learned memory already outrank the AI for every merchant Criss
has corrected once, so the exposed surface shrinks on its own as she uses
the tool.

**The fix, if needed:** extend the same store to categorize calls (keyed
on the line-item descriptions + the account list). Only build this if a
flip is actually observed on cache-pinned inputs.

**Status:** watching; re-check the diff on the next loop iteration.

### 5. Stale "excluded" warning after a restore (cosmetic)

**What happens today:** when a reviewer restores a set-aside file, the
strip entry flips to "restored" but the original technical parse warning
("excluded from expenses, no row exported") stays in the issues list,
now contradicting the grid.

**Why it barely matters:** the strip is the surface Criss reads; the
issues list is ours. Fix only if the contradiction confuses someone in
practice.

**Status:** open, cosmetic, low priority.

### 7. Round-5 fresh-read drift record (evidence, no action)

Two fresh reads of Criss's May folder 5 days apart (2026-08-13 vs
2026-08-18, no cache in the local config): all 20 rows kept identical
amounts, currencies, and dates, and the statement quarantine held 7 of 7
both times. All drift was in text fields: the item-6 vendor flip, one
vendor spelling (Enimove vs Enilive, real brand Enilive), tax-label and
reference noise, and one row that lost its card-hint Paid-Through
resolution. Set 6 (13 never-tested receipts: Uber email-forwards, MBTA,
DB tickets, BRL service invoices) produced exact sums against every
source total spot-checked (three Uber trips to the cent, DB 6.65 EUR);
its misses were vendor names only ("CIV" instead of DB AG, "Uber
Receipts" instead of Uber). Conclusion: money is stable across fresh
reads; residual noise is text-field-only and shrinks as the merchant
book grows.

### 8. Cross-month vendor history in the drill-down (build on demand)

The shipped variance chip (row 6 below) covers THIS batch. The richer
half — "this vendor was Meals in May, Software in June" — needs a small
backend endpoint over run history. Build it only when Criss confirms the
within-batch drill-down is something she uses.

**Status:** deliberately deferred; evidence-gated.

### 9. Multi-category vendors (SHIPPED as row 6 — design record)

**The situation (owner direction, 2026-08-19):** the same vendor can
legitimately produce receipts in different categories (reality), or the
same kind of purchase can flip categories by AI wobble (error). No rule
distinguishes them; a human seeing the vendor's receipts side by side
can. Criss raised the underlying problem in her r1 feedback
(vendor→multi-category, previously parked in the status file).

**The design (pending Criss's concrete example):**

- **Variance chip:** a receipt row whose vendor carries different
  categories within the batch gets an indicator; click →
  **vendor drill-down** (all of that vendor's receipts). Within-batch
  half is nearly free (SPA already holds the rows, Lovable-only);
  cross-month history needs a small backend endpoint over run history —
  add when she confirms she'd use it.
- **Blind spot this fixes:** a vendor with a merchant-book default
  category is auto-stamped and the LLM never runs, so registry-covered
  vendors can never show variance, right or wrong — exactly Criss's
  complaint. Resolution: a per-vendor **multi-category flag** in the
  merchant book — the book keeps canonicalizing the NAME (spelling
  stability) but stops auto-stamping the CATEGORY for flagged vendors;
  each receipt judged on contents, variance auditable via the chip.
  Decouples name stability from category flexibility; no global
  precedence reversal.

**Still needed from Criss:** which vendors actually get the flag turned
on, and what tells her the category on such a receipt (items? card?
entity?) — that answer is Merchants-editor data entry now, not code.

## Related but tracked elsewhere (do not duplicate here)

- Merchant name book seed cleanup (merge the MEGA CENTER/CENTRE duplicate
  entries, fix the mislabeled construction-materials category): an owner
  task in the Merchants editor; noted in the status file row "Canonical
  merchant registry". Round 5 adds the non-BRL vendor families the book
  does not know yet: DB AG (one ticket read the "CIV" tariff marker as
  the vendor), Uber (email-forwards read as "Uber Receipts"), Enilive
  (read once as "Enimove").
- Two parked design questions from the r1 feedback round (entity from an
  upload column, currency guessing): status file row "Zoho import headers
  + card-first fix". The third (one merchant, different categories)
  shipped as row 6 below.
- Remaining Lovable halves (confirm-all queue rendering, folder-attach
  picker, paid-through cell): each named in its status file row.

## Shipped (loop history)

| Iteration | What | Why it mattered | Shipped |
|---|---|---|---|
| 8 | Mail intake (the app's own mailbox): faculty mail receipts to any-name@expenses.brisken.com and they land in the open month batch automatically — in-app SMTP listener on Fly port 25, raw mail archived on the volume as system of record, per-file "submitted by" provenance (To-alias beats From-sender), deny-by-default sender allowlist answered in-protocol (550, we send nothing), day spend budget + disk/in-flight guards, held-mail strip + one-click replay. Hardened pre-ship by a 3-lens adversarial review (6 highs fixed: archive-before-250 custody, batch-mutation lock killing a silent receipt-loss race, snapshot-keyed dedupe so killed jobs can't make loss resend-proof, raceproof caps, zip refusal, replay/status truth) | Dirk's directive (2026-08-20): one address collects expenses and their paraphernalia; Criss's workload shrinks to review + reconcile. Direct faculty mail also removes her relay role and attributes each expense to a person | PR #548, 2026-08-20; Lovable half `docs/lovable-mail-intake-prompt.md` |
| 1 | Non-receipt quarantine: the tool now recognizes bank-statement pages and report summary sheets among the uploads and sets them aside loudly instead of inventing an expense from them | Criss's real May folder had 7 statement PDFs among 27 files; a report summary page had become a phantom 8,796.35 BRL "expense" | PR #516, Fly v58, 2026-08-13 |
| 2 | The word "null" can no longer appear as an expense account in the export; those rows now show the honest "(uncategorized - assign)" placeholder | The AI sometimes answers "no category" as the literal word "null", which Zoho cannot import and Criss would trip over monthly | PR #518, Fly v58, 2026-08-13 |
| 3 | Same photo, same answer: once a photo has been read, the reading is stored keyed on the photo's content fingerprint and reused instead of asking the AI again; re-runs are identical by construction and cost nothing | The identical image had come back MEGA CENTER / CENTRO / CENTRE across runs, and the 2026-08-15 baseline added a BRL-to-EUR currency flip and a tax drift; every new spelling fragmented learned memory. Verified: smoke10 run twice on the fixed code, the two CSVs byte-identical, second run made zero extraction calls | PR #536, 2026-08-15 |
| 3b | Test runs use the merchant name book too: a run config can carry expense.merchants (inline) or expense.merchants_path (JSON file or full settings dump), and the exported CSV now shows the canonical merchant name over the raw OCR spelling | Offline quality runs were judging the tool WITHOUT the canonicalization Criss actually gets, so the loop was steering on the wrong signal | PR #536, 2026-08-15 |
| 4 | Set-aside strip: the review screen now gets a first-class list of what the quarantine set aside (file, reason code for PT wording, restored state) plus a one-click "this is a receipt" restore that reuses the stored reading (no second AI read) and runs the normal categorize pass. Mid-month exclusions survive later adds; the May run derives its strip from the old warnings. Lovable UI half handed to the owner (`docs/lovable-set-aside-prompt.md` in the module) | Trust: a tool that silently ignores an upload reads as broken; one that says "I set these aside, tap here if I'm wrong" reads as careful. Also closed a real hole: a mid-month exclusion vanished from view on the NEXT add | PR #538, 2026-08-16 |
| 6 | Multi-category vendors: a merchant-book entry can carry multi_category: true — the book still corrects the vendor's NAME everywhere but stops auto-applying its category, so each of that vendor's receipts is judged on its own contents; and every grid row carries category_variance (does this vendor have receipts in other categories in this batch), powering a "Mixed categories" chip + vendor drill-down in the UI | Her own r1 feedback: one vendor legitimately books to different categories, but the book's default silently overrode that; variance was invisible whether right or wrong. Owner direction 2026-08-19: surface it, let a human judge | PR #543, 2026-08-19 |
| 6b | Split depiction ("Lançado como"): every grid row carries books_as — the exact per-account fan-out the Zoho export writes (same shared code path, so grid and export cannot disagree) + an is_split flag; the UI renders one receipt booking to N accounts instead of N mystery rows | Owner ruling: splits ARE the truth and must not be collapsed; what was missing was seeing the fan-out ON the receipt instead of discovering it in the export | PR #543, 2026-08-19 |
| 7 | Feedback capture on every page (owner directive 2026-08-19): the double-click location-specific note widget becomes a single global mount across all SPA pages; `POST /api/feedback` now accepts an explicit `run_id` so notes on expense-batch pages attribute to the batch regardless of route shape (path parse stays as fallback) | The existing widget captured exact click locations and produced Criss's r1 notes, but only on the home/run/memory pages; the receipt-first batch pages — the surface she actually reviews — had no capture at all (0 notes ever) | PRs #544+#545, 2026-08-19; Lovable half `docs/lovable-feedback-capture-prompt.md` published + live-verified end-to-end (batch note attributed run_id 7d2fea33d39a) |
| 6c | Vendor is the merchant, never the card-terminal bank: one extraction-prompt line (backlog item 6) so a card slip showing both the shop and the acquiring bank reads the SHOP; invalidates the reading cache by design (fingerprint bump) | Round-5 evidence: the same French card slip read ANNADA ROUEN one day and CREDIT AGRICOLE NORMANDIE another; the bank name teaches the merchant book garbage | PR #543, 2026-08-19 |
| 11 | Learned memory validate + adjust: the 103 learned categories are editable (single-row PUT, count-preserving — an operator correction is not another confirmation; category-only edits never wipe the learned Zoho account), deletable one row at a time (aliases/FX stay), and reviewable (validated stamps + a "needs review" filter; ANY value change clears the stamp so machine re-teaches can never wear an old sign-off); reset now previews what it would delete and requires typed-through confirmation | Her note 10 ("this must be validated and adjustable") on the /memory page; the review caught stale sign-off stamps, a migration race on the live store, and a silent account-wipe before they shipped | PR #565, 2026-08-21; Lovable half `docs/lovable-memory-edit-prompt.md` (REQUIRED — old Reset button becomes a safe no-op until applied) |
| 10 | Body-only mail handling: held mail with no attachment (Uber forwards, credit notices) gets three per-mail actions — view the body (sanitized text off the custody eml, never the raw archive), render it to a PDF and add it to the open month through the NORMAL pipeline (same vision reading and quarantine as any scanned receipt; deterministic bytes so a retry can never double-ingest), and dismiss as junk (terminal, custody untouched, held strip can reach zero). Transient `rendering` status makes render/dismiss/replay mutually exclusive; replay now rescues body-only mail a router crash left as "received"; interrupted renders reconcile to retryable at startup; container gets a full-Latin font so German bodies ("Gebühr", "27,90 €") render legibly for extraction | Her note 12 ("where can user handle this?") + Dirk's first real organic mail sat stuck in held_body_only with no path; adversarial review caught a Pillow timestamp defect that would have let retries create duplicate expense rows | PR #563, 2026-08-21; Lovable half `docs/lovable-body-only-prompt.md` |
| 9 | Intake quick-wins: the Email-intake log shows WHICH files each mail delivered (recorded at accept time; legacy archives derived from parts/) and an honest Month column (batch_label resolved for every routed row, held rows say held, deleted months say "month deleted" instead of misreporting each expense as operator-removed); and Delete month exists behind a typed confirm phrase — cascade under the batch writer lock, job rows purged, mail archives stamped batch_deleted but NEVER deleted (custody/retention), response reports where inbound mail routes next + that learned memory is kept. 3-lens adversarial review pre-commit: sync handler (async version froze the event loop on the OCR-held lock), deleted-run refusal at every locked batch writer, DONE-stamp re-check, replay clears stale stamps, atomic serialized meta writes | Her notes 2/3/13: "need to see which files were delivered", "month says no date", "there needs to be some kind of delete month option" — plus the review closing a real freeze + three race defects before they shipped | PR #561, 2026-08-21; Lovable half `docs/lovable-intake-quickwins-prompt.md` |
