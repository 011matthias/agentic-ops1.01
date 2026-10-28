# Checkpoint: Brisken Recon Duplicates Bound Together

**Date:** 2026-09-25
**Status:** Item 209 Lovable prompt written, design approved on screenshots, verified on a scratch clone; NOT pasted

---

## Summary

The owner asked for a duplicates filter inside each month, then widened it: every suggested duplicate stays bound together across the tool (Expenses and Matching) until someone deletes a copy or clicks "Not a copy", with copies folded under their main. Delivered as one SPA-only Lovable prompt (backlog item 209), approved on real-data screenshots and fully verified read-only against a scratch clone of the current Lovable code.

---

## What Was Done This Session

### Item 209, first shape (grouped filter)
1. Found item 188's "Show duplicates" filter already live; measured that it still scatters pairs (July 10 of 11 not side by side, September 3 of 19, August 3 of 5, June 2 of 2).
2. Wrote the grouped-filter prompt, proved it on a scratch clone (build + headless drive); the drive caught a prompt defect (`fmtDate` printed "02:00 AM" on a date-only header) before handover. PR #1370 (item renumbered 208 -> 209 after a sibling took 208).

### Item 209, final shape (bound together), owner-approved
1. Prototyped in the scratch clone and screenshotted on real July data twice (full rows, then compressed copies + Matching); owner approved.
2. Read live that both matching rules the owner named already hold: 0 of 35 presumed copies matched / offered / assignable; all 6 receipts of July's "Not a copy" groups back in matching unmarked. So the binding is a pure render of `duplicate`.
3. Found and fixed a gap in the prototype: 2 July mains sit only as the proposed receipt on a "Needs review" charge; the host rule is now held-by, else proposed-by, else unmatched receipt.
4. Rewrote `docs/lovable-duplicate-groups-prompt.md` (PR #1394), rebased the scratch clone onto Lovable `9b822f1` (clean, build green), ran the full drive: ALL PASS on July / August / September, card scope, release (in-browser payload with markers removed) and PT. Evidence in PROMPT-STATUS (PR #1399). Status line PR #1407.

---

## Key Decisions Made

### Placement of a bound unit on the Expenses tab
- **Choice:** the unit sits in the section of its most urgent member (Needs a look > Assign a category > Ready).
- **Rationale:** nothing that needs a look hides under Ready; section badges still sum to every row.

### Card scope vs a bound pair
- **Choice:** a unit shows whole when any member passes the filters; the out-of-scope copy is marked "Not on this card".
- **Rationale:** many live pairs are one card-less copy + one carded copy; a strict scope would show them half.

### Where a copy sits on Matching
- **Choice:** under the charge holding its main, else the charge proposing it, else the main's unmatched-receipt row; set-aside list keeps only copies whose main is on no page.
- **Rationale:** owner: "stay bound together until a user separates them, even if in matching"; live July needs all three host kinds (7 / 2 / 2).

---

## What Did NOT Work (and why)
- **Verification drive re-fetching month payloads on every page load against the live API:** each `/api/runs/{id}` and `/api/expense-batches/{id}` call rebuilds the month view; with a polled job (`cef052e61645`) already loading the single Fly machine, reads went to 40-116 s, one 502, and health checks flapped 01:37-01:58 UTC. Replaced by one read per payload + `route.fulfill` replay + a 45 s brake.
- **Fixed 4 s wait before counting Matching copy lines:** under load the page had not rendered, so counts read 0 (a false negative, not a failed build). Wait for the tab text instead.
- **Page-wide vendor count for the Matching release check:** read 4, not 2, because the expanded Duplicates panel lists the group's members too; count open-receipt rows.
- **`TaskStop` on the vite dev server:** killed the shell, not the node child; the dev server kept regenerating `routeTree.gen.ts` and blocked the rebase. Stopped by the PID owning port 5199.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-duplicate-groups-prompt.md` | Created, then rewritten | The item 209 Lovable prompt (bound together) |
| `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` | Edited | Not-applied row with full drive evidence |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edited | Item 209 (owner quotes, live matching-rule reads, design) |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edited | Dated status line (PR #1407) |
| memory `feedback_recon_drive_replay_payloads.md` | Created | Replay payloads + brake on live recon drives |

---

## Current Status

Prompt merged on main (#1370, #1394, #1399); not pasted into Lovable. No backend change, no Fly deploy. The scratch clone with the approved build may still be serving at http://localhost:5199 until this session ends. Live backend healthy again since 01:58 UTC. brisken ops status: `platform: unknown plan` in `infrastructure.yaml` (no platform section assessed).

---

## Next Steps
1. Owner pastes `lovable-duplicate-groups-prompt.md` into Lovable and publishes.
2. After publish: bundle-audit the six decisive keys, then drive the published SPA read-only with payload replay (the prompt's "Checking it landed" list), move the PROMPT-STATUS row to Applied.
3. Merge PR #1407 on CI green if a sibling has not.
4. Optional: build the shared recon drive helper in `tools/` (prefetch, replay, write-abort guard, hydration-safe login), since every recon SPA verification re-derives it.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-duplicate-groups-prompt.md`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (item 209 row)

### Open Questions
- Which client/job was polling `cef052e61645` during the 01:37 UTC degradation (not investigated; not ours).

### Working Notes
- Live duplicate facts (2026-09-25): all groups are pairs; `copy 1` = main (`is_extra` false), extras live in `copies_set_aside` keyed by `duplicate.of`. Mains on Matching: July 7 held / 2 proposed / 2 unmatched, August 3 / 0 / 2, September 2 / 0 / 17.
- Drive scripts (scratchpad, ephemeral): `drive_bound.py` (full check set with replay + `ONLY_RELEASE=1`), `shot_bound2.py` (approval screenshots). Login trap: retype the code until "Log in" enables (hydration).
- Scratch SPA clone is on branch `bound` at `0cc142c` over Lovable `9b822f1`.

### Reference Materials
- PRs #1370, #1394, #1399, #1407; Lovable repo `011matthias/brisken-expense-review`.

---

## How to Continue

After the owner publishes, run the post-publish drive (Next Steps 2) with payload replay; never click delete / "Not a copy" on a real month.

---

## Strategic Feedback

### What Worked Well This Session
- Showing the owner the design on real data before writing the final prompt turned two direction changes into one clean prompt instead of a pasted-then-reworked one.

### Suggestions
- Build the recon drive helper in `tools/`: the replay, write guard and login loop were re-written four times in this session alone.

### System Health
- Sibling sessions edited PROMPT-STATUS during every CI window (three merge rounds on #1399); the Not-applied table is a hot spot for concurrent edits.
- Autonomy: 0 corrective interventions (2 approval rounds the owner asked for).
