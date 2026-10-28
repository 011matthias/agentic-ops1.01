# The five front prompts (condensed record)

Handed 2026-09-25 evening, one per fresh Claude Code chat, all running at once.
Each full prompt started with `/comd_resume brisken`, carried the shared block
below, its own front section, and the SESSION LOOP section verbatim from
`docs/2026-09-25 - Recon Card Ending Wordings/Mini-Checkpoint-1.md`. This file
keeps the substance (what each front was told to build, measure, not build and
ask); the boilerplate is the protocol.

## Shared block (identical in all five)

- Source: the verified map `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\.scratch\recon-matching-gaps-2026-09-25.md` (read your front's section in full first) and the frozen payloads `.scratch\recon-score-2026-09-25\` (July 50622baec444, August 074a7b8905d7, September 51a22ad72864; `boxes == []` = copies). Re-fetch fresh payloads (GET only) before measuring; siblings deploy during your session.
- Four siblings run at once; follow `automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md` to the letter (own worktree `agentic-ops1-front{N}` off origin/main, branch `client/brisken/p1-front{N}-{slug}`, append-never-reflow on the shared files, merge origin/main after any push and re-run the suite, deploy only through `deploy.py` from a detached origin/main worktree, own browser session `recon-front{N}`, checkpoint topic `Expense-Recon Front {N} {slug}` in worktree `agentic-ops1-ckpt-front{N}`, cleanup proof, final reply per §11 then the remaining queue).
- The main checkout is shared and stale: never edit, commit or stash there; never trust an absence read from it.
- Rules: no live writes on Criss's months without a per-action yes via `AskUserQuestion` (decision + recommendation + consequence); read-time rules predicted per row on the frozen payloads first (item-203 method) and checked after deploy; Zoho production read-only and never imported from `web/`; OpenAI/Anthropic/Lovable registry writes and the 44-merchant write plan owner-gated (do not re-ask about Lovable); TEST- fixtures only; measure before and after with the front's instrument; every fix = route-level test through the caller + one `regress_check` proof; B4.
- Record: one backlog item at the END of Open, numbered with the next free number after merging origin/main right before the push (220 free at 2026-09-25 17:47 UTC), Shipped row max+1 at merge, status row, api-contract section + view-contract pin for every new field, Lovable prompt doc + PROMPT-STATUS Pending row handed as pasteable text.

## Front 1: charges with nothing behind them (chase, already booked, completeness)

Build order: (1) charge reasons `closed_recurring` / `no_receipt_expected` with labels; the reviewer's already-booked verdict honoured by every counter; non-purchase rows out of `n_already_posted`. (2) `summary.n_cards_uncovered` + sentence in `not_complete_detail`, advisory. (3) chase names the charge date range and groups by the charge's own month. (4) `days_since_requested`, `overdue` (settings threshold, default 14 d), bulk `mark-all` per holder. (5) CLI-only read-only `python -m expense_recon.zoho.booked_report` joining open charges to the three orgs' expenses (company + cent + 3 days) with a differential-probed pull. (6) `receipt_chase[].charges[].inbound_hint` from the inbound log.
Not built: the sender, holder addresses, portal hints, Zoho reads from `web/`, a Publish gate on coverage.
Instrument: fresh GETs before/after, per-row prediction of every reason change.
Decisions: Publish warn vs refuse on uncovered cards (recommend warn); writing already-booked verdicts from the report (recommend no); holders map = known senders, no send.
Outcome per the memory file: item 221, PR #1468, Fly `f92a2f87`; owner said warn only, YES to the verdict writes (22 written), holders = Dirk + Nicolas; the inbound link not built (0 held/pooled mails live).

## Front 2: receipts with nothing to land on (reasons, coverage span, month placement, company spelling)

Build order: (1) receipt reasons test the card before the edge; new `statement_not_loaded_for_date` with `waits_for`; German cash/debit words in NON_CARD_TENDER. (2) `n_receipts_waiting_statement` split out of `n_receipts_need_charge`; the completeness sentence names the real wait. (3) declared statement period stored from the PDF's printed dates / the export file name; `covers()` reads it; family uploads cover a subcard only with a printed charge or a declared span. (4) `cards[].statement_expected` (default true); `waits_for` skips false. (5) `entity_key()` alias resolution in pair_in_scope, the hand-match guard, the per-row entity_mismatch advisory and the memory / map keys (August Lovable 15.00 gains its candidate at the next natural re-match). (6) adjacent borrow keyed by (source batch, id) and carrying the receipt's card scope. (7) a confirmed-private receipt is not refused `entity_missing`.
Not built: item 211's wider window, bills with no payment words (D2), the 5-day windows, deterministic.py scoring.
Instrument: per-row reason tables; attribution on July + August + six bundles (70/95 floor, 0 right pairs move).
Decisions: item 211 (+3 days at the start edge, recommend yes); `statement_expected=false` on 0113/6013/8311 (recommend yes); picker offers only the five provisioning spellings (recommend yes).
Outcome per the memory file: item 220, PR #1466.

## Front 3: the posting account (identity, per-company accounts, model suggestions)

Build order: (1) identity read live in the grid and charge rows (`vendor.stamped` kept as a parallel field); a merchant that NOW has a per-company account answers at read time as origin `rule`, the model's answer moves to `suggested_category`, never the reverse. (2) descriptor tier in `MerchantRegistry.resolve` for Chase descriptions (URL / state / reference stripped, lead word + product word for multi-product platforms), measured on all 314 descriptors under the live and the planned list. (3) containment guard on the fuzzy tier (Twilio must not become SendGrid). (4) ZOHO ERP guard: E500010-10 only for the Zoho identity; stored picks read as refusals. (5) stored parent-account suggestions read `model_picked_parent`. (6) `expenses[].line_sum_gap` + export marker `(lines do not add up)`; pro-rating unchanged. (7) report the Lovable twin entries per row; propose the merge, do not write.
Not built: any registry write, the write plan, Confirm-teaches, a joint card x category model, a model re-run over live months.
Instrument: `tools/recon-categorization-score.py --fetch --pull-zoho` before/after (post-re-run baseline 38/120, rules 22/23, model 16/97).
Decisions: item 115 (seeded rules may decide lined receipts with the glance, recommend yes); merge the two Lovable entries (recommend yes, no account change); execute the uncontested write-plan rows (present once, 3+ postings first).

## Front 4: copies and double counting

Build order: (1) investigate the 27 + 23 `__BENCH-nnn.pdf` files read-only (provenance, inbound log, archive) before anything else; delete nothing. (2) reference key by digit core (>= 6 digits) plus a one-digit-misread rung gated on vendor + date + amount + currency; the three September OpenAI 80.12 invoices are the pinned negative. (3) rendered mail body twinned to a non-body receipt by amount, currency, date +-1 and merchant identity; the body is never kept. (4) `document_kind` added to the extraction SCHEMA only (A/B twice old vs twice new, smallest set); kept_member reads it; a `reminder` is a read-time review note, never a deletion. (5) a reference seen in another month with the same total is a billing-account key, excluded from the reference key; cross-month vendor/date/amount pairs advisory only. (6) intake records `twin_of` for Invoice + Receipt of one mail. (7) `POST /api/runs/{id}/duplicates/reapply` (operator, typed confirm), built, run on nothing.
Not built: overriding a reviewer ruling, read-time kept-copy swaps on statement months, row deletion.
Instrument: per-row group prediction; attribution on July + August + bundles.
Decisions: delete the BENCH rows if they are a benchmark load; order the September re-match so 12 groups swap; the Redis reminder stays Criss's (D3).

## Front 5: pairs in Reconciled that still need a click

Build order: (1) the FX judge receives the candidate's fx block, the resolved card evidence and the vendor score; the prompt says the rate is given; judgment-cache key carries a prompt version; the model is skipped when a demoted pair already has card 100 + vendor >= 75 + band match (the reason names the rival). (2) `review.cause` / `review.cause_detail` (rival_agrees / model_doubts / merchant_disagrees / no_card_rival / fx_review_zone / probable_date_gap); PROBABLE rows say why. (3) posted charges are not judged and leave `n_review` (July 13 -> 0). (4) `row_type_of` reads payoff descriptors on Type-less sources (`payment`, Aug 4 rows USD 13,848.16, Sep 2 rows USD 4,660.00). (5) `rows[].reverses_transaction_id` advisory for merchant refunds (0 live). (6) candidate-level merchant floor for exact pairs (item 133 rules 1 + 3), shipped only if 0 labelled-right pairs move.
Not built: self-confirm for fx pairs, any threshold or band, the unmatched rescue pass.
Instrument: attribution --live on July + August with labels, six bundles, `recon-accuracy-guard.py` vs the baseline; per-row tables for 2, 3, 4.
Decisions: item 76 revisit (fx_reference self-confirm on a daily/ECB rate within 1 %, card agrees or unknown, vendor >= 75, uniqueness passed; recommend yes with the measured August count); p >= 0.85 verdicts lifting a pair (recommend no).
