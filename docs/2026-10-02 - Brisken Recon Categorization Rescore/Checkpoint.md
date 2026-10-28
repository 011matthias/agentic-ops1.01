# Checkpoint: Brisken Recon Categorization Rescore

**Date:** 2026-10-02
**Status:** Analysis only (owner question "why is the categorization of the months still so bad?"); no code, no live write

---

## Summary
The live re-score against Criss's own Zoho postings shows the tool's answers are now mostly right (82 of 100, rules 68 of 68). It answers too few rows: 67 of 186 July to September receipts carry a rule account. The blanks are merchants with no per-company rule plus receipts with no company, and nothing has started learning.

---

## What Was Done This Session
### Measurement (read-only)
1. Ran `tools/recon-categorization-score.py --fetch --pull-zoho` from a detached origin/main worktree against July `50622baec444`, August `074a7b8905d7` and September `51a22ad72864` (11 GETs, 15 s apart, longest 2.6 s; a fresh Zoho Books pull, 193 expenses over three orgs). Payloads and the score are in `.scratch/recon-score-2026-09-28/` (fetched 2026-09-27 23:47 UTC).
2. Split the 119 receipts not decided by a rule by company, merchant and reason, and checked each merchant against Criss's pre-July Zoho history.
3. Split the 81 charges with no account by bucket and entry status.
4. Read Matthias's inbox read-only through Graph for Dirk's reply to the 2026-09-28 account questions. The control found the sent mail; there was no reply.

### Answer given to the owner
Accuracy is no longer the problem; coverage is. The blanks fall into four groups: no company, no rule for the merchant in that company, model answers now refused by the item 224 guards, and no learning yet. The answer also named the levers and who acts on each.

---

## Key Decisions Made
### Measure before explaining
- **Choice:** answered from a fresh live score rather than the 09-25 memory figures.
- **Rationale:** items 219 and 224 plus the 09-27 map write had landed since 09-25. The old 21/100 figure would have pointed at the model, but the real gap is coverage.

---

## What Did NOT Work (and why)
- **Matching merchant names to Criss's Zoho history by shared word tokens:** too loose. Shared words like `ltda`, `posto` or a person's surname pulled in unrelated postings, so the "split across accounts" class (40 rows) is inflated, and the history counts were only safe to report as rough. Next time run the names through the engine's own `merchant_identity.MerchantIdentityResolver`.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit | 2026-10-02 status line: the re-score and what blocks coverage |
| memory `project_brisken_recon_categorization_analysis.md` + `MEMORY.md` index line | Edit | 09-28 re-score facts (outside the repo) |
| `.scratch/recon-score-2026-09-28/` | Create | payloads + `categorization-score.{json,md}` (gitignored) |

---

## Current Status
Figures as of 2026-09-27 23:47 UTC:

- **Receipts (186, copies excluded):** 67 rule, 37 suggestion only, 82 blank, 0 picked by a person (`summary.categories_by_origin`).
- **Charges (314):** 136 rule, 97 suggestion, 81 none. Of the 81, 32 are July rows Criss already booked (`entry_status: posted`) and 10 are refunds or payments, leaving about 39 real blanks.
- **Accuracy against her postings:** 82 of 100 answered rows agree, 75 of 91 on the strict join. On open rows the tool is right on 23 of 24 it answered. The per-company map answers 64 rows and agrees on 64.

These figures predate item 239 (Gemini reads every receipt, Fly v276) and item 240 (stored receipts re-read and all seven months re-matched on 2026-09-28). Item 240 re-categorizes a receipt whose merchant or company moved, and its re-match lands every pending charge change, so the counts have moved since.

Dirk got six account questions on 2026-09-28 08:42 UTC (comms log; Lovable, Microsoft, Google, Consulting, AWS, never-booked tools). There is no reply in Matthias's inbox as of 2026-10-02.

Ops status: platform unknown plan, never assessed (infrastructure.yaml has no platform section).

---

## Next Steps
1. Re-score on today's months before quoting any figure (command in Working Notes); compare against this checkpoint's baseline.
2. When Dirk answers, build the per-company account write for his six cells as a read-modify-write of `settings.merchants`, shown to the owner with its diff. It is a live settings write, so it needs the owner's yes.
3. Check whether the two July MARTINO SUPERMERCADO receipts (`0053__...Marinho.pdf`, `0067__...Marinho.pdf`) still show company Corporate Services with a stale `entity_missing` refusal after item 240. If so, read the code path before naming a cause (see Open Questions).
4. Compact `MEMORY.md` under 140 lines (hook advisory: 164).
5. Run `/ops-audit brisken`, or decide it does not apply: infrastructure.yaml carries no `platform` section for a FastAPI-on-Fly client.

---

## Context for Next Session
### Files to Read First
- `.scratch/recon-score-2026-09-28/categorization-score.md` (the baseline)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 216, 219, 224, 239, 240
- `workspace/clients/brisken/context/comms-log.md` entry "2026-09-28, Matthias -> Dirk: card-account questions"
- `workspace/clients/brisken/context/expense-reconciliation/merchant-account-suggestions-260925.md`

### Open Questions
- Do the two MARTINO receipts carry a stale refusal because their company arrived after categorization (item 206 class), or for another reason? I named that cause to the owner without reading the code. Treat it as a hypothesis.
- Does Dirk answer by mail, or in Teams where Graph does not reach?

### Working Notes
- Re-score command (from a detached origin/main worktree, so the module matches what is deployed): `uv run tools/recon-categorization-score.py --fetch --pull-zoho --payload-dir <main clone>/.scratch/recon-score-<date> --batch 50622baec444 --batch 074a7b8905d7 --batch 51a22ad72864`.
- Receipts not decided by a rule (119), grouped:
  - No company (33): 17 wait for a statement, 6 need a company, 6 suggested private.
  - Lovable (about 14): her bookings split, 33 to CorpServ IT and 13 to Marketing.
  - Never booked by Criss (about 29): Hostinger, Vercel, OpenRouter, Obsidian, Trello, Twilio, Typora; Anthropic, Brave and ElevenLabs under Consulting; small Brazilian food places.
  - 1 or 2 bookings on one account (about 13).
  - The rest split across accounts (Microsoft, Google, Amazon, Fireflies, Rize, Network Solutions, gas stations).
- The item 224 guards (v262) turned 62 pre-filled model suggestions into "pick an account" on 09-27. This is why the screen reads emptier than before 09-27 even though the answers it shows are better.
- Nothing compounds: `person` is 0 on all three months, the 35 bucket-era picks were retired at the GL conversion, and only corrections teach, only at Publish.
- Owner rulings that bound any proposal: no live writes on Criss's months; only corrections are memorized; trip never decides a category.

### Reference Materials
- Memory `project_brisken_recon_categorization_analysis.md` (09-28 bullet)
- Memory `feedback_recon_no_live_writes_criss_acts.md`

---

## How to Continue
`/resume brisken`. For categorization, re-score first, then compare against the baseline above. Dirk's reply is the gate for the next settings write.

---

## Strategic Feedback

### What Worked Well This Session
- Splitting "categorized" by who answered (rule, suggestion, person) turned a vague complaint into specific counts. The screen's "categorized" count mixes suggestions in with decided rows, which is why it looks better than it is.
- Checking the inbox read with a control (the sent mail had to be visible) before trusting an empty reply list.

### Suggestions
- Add a coverage section to `recon-categorization-score.py`: receipts and charges by origin, plus the not-decided rows grouped by company, merchant and history class through `MerchantIdentityResolver`. This session did that grouping by hand with a loose matcher. As a tool it becomes the standing answer to "why is it still bad".

### System Health
- The checkout was 64 commits behind origin/main at session start. Running the scorer from a detached origin/main worktree avoided measuring with stale module code.
- Autonomy: 0 human interventions (fully autonomous session).
