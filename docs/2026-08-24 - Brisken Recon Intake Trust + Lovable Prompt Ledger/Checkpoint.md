# Checkpoint: Brisken Recon Intake Trust + Lovable Prompt Ledger

**Date:** 2026-08-24
**Status:** Backlog item 30 closed and deployed (Fly v90). Lovable is applying the three rewritten prompts now.

---

## Summary

Closed backlog item 30 end to end (the intake could not tell anyone whether a
receipt arrived) plus the backend half of the "Arriving" mislabel, in three
shipped PRs. Then an owner challenge on coordination exposed that our record of
which Lovable prompts had been pasted was guesswork; replaced it with a measured
ledger, which surfaced a bigger defect than any missing prompt: **the published
SPA has no months list at all.**

---

## What Was Done This Session

### Item 30, the intake trust round (PRs #607, #608, #609)

1. **Known senders (30a).** Settings `intake.known_senders` lists outside
   addresses that count as ours. `graph_notify.send_mail` gained an explicit
   per-call `allow_external` and now asserts the structural recipient guard
   BEFORE consulting it, so a listed address widens the rule by exactly itself
   and a smuggled second recipient stays refused.
2. **Auto-render (30c).** A known sender's body-only mail is rendered on arrival
   instead of waiting for a click, reusing the operator render path unchanged.
   All six mails held on 2026-08-24 delivered no file at all: a forwarded vendor
   receipt IS the body. Strangers still hold, so the mailbox does not pay a
   vision call per newsletter.
3. **Refusal ledger (30b).** Every refusal is written to
   `inbound/refusals.jsonl` (sender, recipient, stage, reason, peer), covering
   the DATA-stage guards as well as a refused RCPT, size-trimmed so a scanner
   cannot fill the volume. Surfaced as `n_refused` (7-day window) + `refusals[]`.
4. **Parallel status view.** Every log row carries `status_kind`
   (`resting`/`held`/`working`/`done`/`unknown`) and a composed `status_label`.
   An unrecognised status degrades to the raw value instead of borrowing a
   label. api-contract **rule 5** now covers enum growth, enforced by
   `test_every_status_has_a_label`.
5. **Two defects found by the round's own adversarial review**, both fixed in
   the same PRs: a `rendering` status that stranded until the next boot when an
   exception escaped `render_ingest`, and a 7-day cutoff comparing ISO strings
   with mismatched `timespec`.
6. **One defect found only by driving the live SPA** (#609): dismissed archives
   rendered as "The month it was added to was deleted" with kind `held`, while
   the Held badge correctly said 0. Dismissal is terminal and outranks where the
   mail used to live.

### The prompt ledger and the months-list finding (PRs #611, #612, #614, #615)

7. **`docs/PROMPT-STATUS.md`** — every Lovable prompt audited against the
   published SPA with verbatim signature strings. **Sixteen applied, three not.**
8. **`/months` has no list.** 0 tables, 0 rows, 518 characters; `/`, `/expenses`
   and `/expenses/new` render the same create form. The page calls
   `GET /api/expense-batches`, gets 200 with six batches, and discards them.
   Wrote `docs/lovable-months-list-prompt.md`; backlog item 32.
9. **Backlog item 31**: the "Accepted senders" editor is live and the backend has
   ignored `intake.senders` since #587, so it silently discards operator input.
10. **All three remaining prompts rewritten** to open with a measured inventory
    of the published build and ask only for the delta.

### Date correction (PR #616)

11. Every artifact authored this session was stamped **2026-08-25**. Swept back
    to 2026-08-24 against the live drill timestamps.

---

## Key Decisions Made

### One list, not two: `known_senders` rather than `ack_addresses`
- **Choice:** the backlog proposed `intake.ack_addresses`; shipped as
  `intake.known_senders`.
- **Rationale:** the same list also gates auto-render. A name saying "ack" would
  be one name answering two questions, which is the failure the api-contract
  counts section already warns about.

### Auto-render gated on the sender, not opened to everyone
- **Choice:** only a known sender's body-only mail renders itself.
- **Rationale:** submission is open to anyone. Rendering every stranger's
  newsletter costs a vision call and puts junk in the pool. All six real mails
  came from Dirk (work + iCloud) or Criss, so the gate covers the actual traffic
  and the list widens it.

### Refusals are not `entries`
- **Choice:** a separate top-level `refusals[]`, never a row in the mail table.
- **Rationale:** a refusal has no archive, so it cannot be deduped, replayed or
  dismissed, and a row carrying a status no consumer knows is precisely the
  "Arriving" failure.

### Prompts rewritten rather than re-sequenced
- **Choice:** each remaining prompt opens with what the app already has and asks
  only for the delta; month-pool §0/§12 extracted and DELETED from that file.
- **Rationale:** the prompts were written as a sequence and pasted out of it.
  month-pool §1 ("label it Waiting for its month") directly contradicts §0
  ("render `status_label`"), so re-pasting the file would have Lovable arguing
  with itself.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/expense_recon/web/intake_mail.py` | edit | `known_senders`, `is_known_sender`, `_auto_render`, refusal ledger, `annotate_status_view` |
| `src/expense_recon/web/graph_notify.py` | edit | per-call `allow_external`; structural guard asserted first |
| `src/expense_recon/web/smtp_server.py` | edit | record every RCPT and DATA-stage refusal |
| `src/expense_recon/web/app.py` | edit | `n_refused` / `refusals` / `annotate_status_view` on the inbound log |
| `tests/test_intake_mail.py` | edit | +20 tests; body-only fixtures moved to `OUTSIDE` |
| `docs/api-contract.md` | edit | rule 5 (enum growth), the new field rows |
| `docs/PROMPT-STATUS.md` | new | the prompt ledger |
| `docs/lovable-months-list-prompt.md` | new | the missing screen |
| `docs/lovable-inbound-status-refusals-prompt.md` | new | month-pool §0 + §12, extracted |
| `docs/lovable-known-senders-prompt.md` | rewrite | folds in open-intake; live inventory |
| `docs/lovable-month-pool-prompt.md` | edit | banner-marked APPLIED; §0/§12 removed |
| `docs/lovable-open-intake-prompt.md` | delete | folded into known-senders |
| `status/p1-expense-reconciliation.md` · `p1-improvement-backlog.md` · `p1-recon-loop-prompt.md` | edit | items 30/31/32, SPA parity row, runbook |

---

## Current Status

Backend: **Fly v90**, `/healthz` 200. Suite **1257 passed / 2 skipped**,
calibrate green, ruff (E9,F) clean on the diff. Nine PRs merged on green CI.

brisken ops status: platform unknown plan, `~?/?` ops/mo, last assessed `?`
(no `platform` section in `infrastructure.yaml`).

Live intake: 24 archives, 10 ingested, 6 pooled, 8 dismissed (all TEST, cleaned
to zero non-dismissed), `n_held` 0, `n_refused` 1 (a deliberate relay-refusal
drill; it ages out of the 7-day window).

The six pooled receipts are real and waiting for August 2026 (4) and July 2026
(2), neither of which exists as a batch.

Lovable is applying the three rewritten prompts as of this checkpoint.

---

## Next Steps

1. **Re-audit the SPA once Lovable publishes** — run
   `%TEMP%/claude/recon-probe/prompt_ledger.py`, update `docs/PROMPT-STATUS.md`.
   Confirm the months list renders six batches, the Status cells read "Waiting
   for August 2026", and the "Accepted senders" editor is gone.
2. **Open August 2026 and July 2026** so the six waiting receipts land. Needs one
   real uploaded receipt each (`create_expense_batch` refuses an empty batch);
   never seed a fabricated one.
3. **Card registry data entry** (item 26): entities for 0113 / 6013 / 9693 /
   8311 and the missing 0340 card. Until then a real-month test is dominated by
   MISSING ENTITY noise.
4. **Decide on `dirk_.neumann@icloud.com`** in `intake.known_senders`. Owner's
   call: it starts automated confirmations to a private mailbox.
5. **PR 2 of the living month** (item 29) is the next build: stable
   content-derived transaction ids, append-capable statement uploads,
   `has_statement` no longer closing the month, incremental re-match.
6. Six `p2-*` status files are 32-64 days stale. Not touched this session; they
   belong to the lead-gen workstream and bumping `updated:` without doing the
   work would be dishonest.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` (the runbook)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 29, 31, 32)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`

### Open Questions
- Does the create-time month advisory already render? Unverifiable without
  creating a live batch; the months-list prompt handles both cases.
- `lovable-issue-codes-prompt.md` and `lovable-re-ingest-prompt.md` status is
  genuinely unknown: no live batch carries `upload_issues`, and no archive is
  both stranded and non-terminal.

### Working Notes
- **A RED-proof harness must snapshot the WORKING TREE, not restore from git.**
  `git checkout -- <path>` between regression cases destroyed uncommitted edits
  twice before the harness was changed. Both proof scripts now snapshot file
  contents in memory.
- **Audit method matters more than audit coverage.** A loose regex matched a
  Cards help line ("every company card the tool can recognise") and reported the
  known-senders editor as present. Per-row intake actions are an icon-only
  `button[aria-label="Actions"]` menu, so enumerating button TEXT reports no
  actions on any row; that made me report body-only handling as missing when it
  is live. Match exact strings; open the menu.
- **After a squash-merge, cut a fresh branch.** Pushing more commits onto the
  pre-squash history produced a conflicting PR (#613) that had to be closed and
  recreated as #614.
- The batch `ae61e122a505` (April 2026) is the richest audit target: set_aside 1,
  splits 1, variance 2, unresolved card hints 25, parse_issues 1, needs_entity 33.

### Reference Materials
- Probes: `%TEMP%/claude/recon-probe/` — `api.py`, `prompt_ledger.py`,
  `held_menu.py`, `drill_autorender.py`, `dismiss_drill.py`, `smtp_probe.py`
- App: https://brisken-expense-recon.fly.dev · SPA:
  https://brisken-reconcile-dash.lovable.app

---

## How to Continue

Read the runbook, then the ledger. If Lovable has published, re-audit first:
that is the one input that changes what is worth doing next. Otherwise start
item 29 (PR 2 of the living month) — nothing is on fire there, which is exactly
why it is now the top build.

---

## Strategic Feedback

### What Worked Well This Session
- **Driving the live SPA found two defects an API read could not**: the
  dismissed-row mislabel (#609) and the missing months list. The "verify the
  consumer, not just the API" rule from the previous round paid for itself twice.
- **The RED-first discipline held at 21 regressions**, and the adversarial review
  over the diff found a real defect in every one of the three code PRs.

### Suggestions
- **The prompt ledger should be generated, not hand-maintained.**
  `prompt_ledger.py` already produces the table; wiring it to write
  `PROMPT-STATUS.md` directly would remove the drift that caused this session's
  coordination complaint. Today the script prints and a human transcribes.

### System Health
- **Autonomy: 2 human interventions** (the coordination challenge, and the
  request to rewrite the prompts for out-of-order pasting). Both were corrections
  of output quality rather than direction.
- The date error survived a whole session and four merged PRs without any gate
  catching it. `validate-output.py` checks unsourced claims but not date
  plausibility; a check that a date stamp is not in the future would be cheap.
