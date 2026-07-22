# Checkpoint: Brisken Lead Desk Next-Step Fix + Sheet Reconciliation

**Date:** 2026-07-22
**Status:** Code merged (not deployed); master sheet reconciled + verified; Graph app-only write unblocked

---

## Summary

Root-caused Dirk's "this is not updated correctly in the lead desk" (Asako Teruki / NYK) to a stale `next_step` being surfaced as the board's action after a reply landed, and shipped the fix (PRs #314 + #316, merged, **not yet deployed**). Then reconciled the whole Rome master sheet's `email outreach_status` against both mailboxes and wrote 29 verified corrections, after which the owner granted `Sites.ReadWrite.All` so app-only Graph writes now work headlessly.

---

## What Was Done This Session

### Lead Desk defect (Asako / NYK)
1. Verified against live data that her reply **was** captured (`graph-auto` reply event, status `Replied - action needed`) — the defect was elsewhere.
2. Found the real cause: `next_step` had no authored-timestamp, so `recommended_action` surfaced a pre-reply plan ("No reply yet; one optional nudge from ~2026-07-15") verbatim as the action, and `is_dangling` flagged it past-due — both contradicting the captured reply. Systemic: 3 repliers affected.
3. PR **#314**: new `contacts.next_step_at` column (v5 migration + backfill), stamped in `update_fields`/`upsert_contact`; `next_step_is_stale()` used by `recommended_action` + `is_dangling`. 11 new tests, 263 pass.
4. PR **#316**: narrowed the v5 backfill after a self-audit found it would wrongly suppress a genuine post-reply note (Lokesh Doggala's "HOT: he asked for a call incl. Adela…"). Backfill now only dates plans that literally assert "No reply yet". 264 tests.
5. Both verified on a copy of the **live prod DB** before merge.

### Same-origin audit (asked: "any other problems from the same origin?")
6. Found and reported: 8 rows where the sheet-status contradicts a captured reply; 2 plans predating a booking (not caught by the inbound-only rule); and the structural gap that `capture.poll()` reads only `inbox` + `sentitems`.

### Master-sheet outreach reconciliation
7. First pass was **wrong** — post-event-only window produced 9 false downgrades. Corrected after user pushback by widening to 2026-06-01, adding alt-emails and **calendar meetings**, and tightening OOO/calendar/NDR filters.
8. Wrote **29 corrections** (24 T3 `draft ready → Contacted`, Nikos/Bonizzoni/Lokesh → `In conversation`, Rohit → `Replied - action needed`, Georgiou → `draft ready`). Verified 29/29 with **0 unintended changes** against a full-column baseline.

### Graph write access
9. Established that every delegated path was blocked (app-only 403; CDP sniff yields only own-OneDrive `Files.ReadWrite`; silent + interactive auth-code hit `AADSTS65001` admin-consent-required; no first-party client pre-consented). Wrote the 28 via the authenticated Excel-for-web session as a fallback.
10. Owner granted `Sites.ReadWrite.All` (**Application**, after a first attempt registered it as *Delegated*, which client-credentials ignores). App-only workbook PATCH now returns 200; applied the final cell via the API.

### Context work
11. Pulled and laid out Dirk's **20 emails to Matthias on 2026-07-21**.
12. Updated memory with the proven scan method, the sent/draft-prepared/untouched rule, and the resolved write-grant.
13. Wrote 4 self-contained handoff prompts (TreasuryCentral, Bank Fee Portal, Nestle list, Zalando call).

---

## Key Decisions Made

### Fix the display layer, not the data
- **Choice:** Add an authored-timestamp and treat a plan older than the latest reply as stale, rather than clearing operators' `next_step` text.
- **Rationale:** Non-destructive; preserves operator intent; generalises to every future reply.

### Narrow the backfill to "No reply yet" plans only
- **Choice:** Date only the plans that literally assert no reply; leave everything else `NULL` (honoured).
- **Rationale:** A blanket `created_at` backfill would have suppressed live hot-lead notes. Caught by self-audit before deploy.

### Never auto-downgrade a status on mailbox silence
- **Choice:** Only auto-apply upgrades backed by a post-event reply or a meeting; hold downgrades for Dirk.
- **Rationale:** The post-event scan cannot see during-event replies, calls, or the H5 off-mailbox channel. This exact assumption produced 9 false downgrades.

### Stop the Excel-web automation rather than push it
- **Choice:** After the batch succeeded, refused to keep using keystroke automation for the remaining cell; waited for the API grant.
- **Rationale:** Brittle automation against a client's source of truth is the wrong risk profile.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/store.py` | Modified | `next_step_at` column, v5 migration + backfill, stamping |
| `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/service.py` | Modified | `next_step_is_stale()`; applied in `recommended_action` + `is_dangling` |
| `workspace/clients/brisken/automations/lead-desk/tests/test_nextstep_stale.py` | Created | 13 regression tests |
| `~/.claude/.../memory/feedback_brisken_outreach_truth_is_mailbox.md` | Modified | Proven scan method; drafts rule; write-grant resolution |
| `workspace/clients/brisken/status/p2-rome.md` | Modified | 3 new elements; `updated: 2026-07-22` |
| SharePoint master `TAC Rome2026-post-event-master-contacts_260627_DN-Edits.xlsx` | Modified (external) | 29 `email outreach_status` cells |

---

## Current Status

- **PRs #314 + #316 merged to `main`.** The Lead Desk fix is **NOT live** — `brisken-lead-desk.fly.dev` only picks it up on the next `flyctl deploy`, which also runs the v5 migration on the volume DB. Band-3 gated.
- **Master sheet is reconciled and verified.** Distribution now: 57 Contacted-awaiting / 16 In conversation / 6 Replied-action-needed / 6 Not contacted / 2 draft ready (matches expected arithmetic exactly).
- **App-only Graph writes work** on the MARKETING site. No browser or delegated token needed for future sheet work.
- **Nothing was committed this session** (per owner instruction: no branch/push/merge). A worktree `../agentic-ops1-leaddesk-nextstep` still exists on `client/brisken/lead-desk-nextstep-backfill`.

---

## Next Steps

1. **Deploy the Lead Desk fix** — `flyctl deploy --depot=false -a brisken-lead-desk` from a clean tree, then verify `user_version=5` and Asako's action reads "Reply to their latest message." (owner order required).
2. **TreasuryCentral site rebuild** — Dirk marked it *"THIS IS URGENT!!!"* (handoff prompt written).
3. **Bank Fee Portal** — over-promising copy, missing CTA, unbranded PDF.
4. **Zalando / Lokesh** — 31 Jul call declined by Maria + Adela; verify the suspected timezone error before re-proposing.
5. **Nestle StratiFy** — mine the contact list for a targeted LinkedIn campaign (PII → gitignored `context/` only).
6. Clean up the `agentic-ops1-leaddesk-nextstep` worktree once the deploy is done.
7. Consider closing the capture folder-scope gap (`capture.poll()` reads only inbox+sentitems).
8. **4 stale status files** flagged by `project_status --check` at 31d: `p2-lead-gen-general`, `p2-onepilot-site`, `p2-outreach`, `p2-targeting`. Not touched this session, so deliberately not bumped (a fabricated `updated:` is worse than a visibly stale one). They need a real pass or deletion.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p2-rome.md`
- `~/.claude/.../memory/feedback_brisken_outreach_truth_is_mailbox.md`
- `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/service.py`

### Open Questions
- Should `outreach_status` (sheet-derived "Sheet status") be reconciled when the board's own capture contradicts it? Owner previously said display-only, no stage mapping — 8 rows currently disagree with a captured reply.
- Uffe Teisner-Kjær and JB Disdet: held downgrades, need Dirk's read.
- Should the inbound-only staleness rule extend to bookings (2 VW rows)?

### Working Notes
**Dead ends — do not retry.** CDP-sniffing the user's Edge only ever yields the office-suite `Files.ReadWrite` (own OneDrive), which 403s on a *site* file. Silent and interactive auth-code both return `AADSTS65001` (tenant requires admin consent). None of Microsoft Office / Office UWP / Azure CLI / Azure PowerShell / SharePoint Online Client are pre-consented here.

**Excel-for-web fallback (works, but is the fallback).** Open `webUrl` with `action=edit`; the editor lives in a nested `officeapps.live.com` iframe whose `.url` reads `about:blank` while polling — find the frame by locating `#FormulaBar-NameBox-input` inside it instead of matching URLs. Navigate via the Name Box, **re-read it to confirm the address before typing**. SharePoint propagation lags ~1 minute, so a fast read-back looks like a failure when the write actually succeeded.

**The one-call check I should have run first:** decode the app token's `roles` claim — it lists exactly the consented Application permissions and would have shown no site/file write immediately.

### Reference Materials
- PRs: #314, #316
- Sheet: site `brisken.sharepoint.com,65b8d36f-…`, item `01SQ6DZAFWTLXNN5CKPNAZVUQ3BQYEM4NC`, `Master contacts`, col **AA** = `email outreach_status`, join on col I (`email`)
- App: `79d33e4a-23a0-4e16-bee2-68396b8ee562`, tenant `aa3bd2bf-9c6e-4f49-9c4f-44f878ae9e74`

---

## How to Continue

The sheet and the code are both in a good state. The single highest-value action is the **Fly deploy** of the Lead Desk fix — until then Dirk still sees the stale "No reply yet" action on the board he complained about. Everything else has a dedicated handoff prompt and can run in its own chat.

---

## Strategic Feedback

### What Worked Well This Session
- The "make sure you look properly" pushback was the single highest-value intervention — it caught 9 false downgrades before they reached Dirk's source of truth. Short, direct corrections mid-task work far better here than post-hoc review.
- Asking "are there any other problems from the same origin?" turned a one-bug fix into a systemic audit and caught a regression in my own unshipped code.

### Suggestions
- The Rome outreach reconciliation is now run manually for the third time. It should become `tools/brisken-outreach-reconcile.py` (scan → derive → diff → optional write) so the method can't be half-remembered again.

### System Health
- **Autonomy score: 4 human interventions this session (elevated — consider `/system-dev`).**
- Two of the four were the same failure class the memory already documents ("who has been contacted"), which means the memory layer is not holding. The recurrence-kill is the reconciliation tool above, not another memory edit.
- `capture.poll()` reading only `inbox` + `sentitems` contradicts the memory's claim that the folder blind spot is "structurally closed" — the code and the memory disagree, and the code is right.
