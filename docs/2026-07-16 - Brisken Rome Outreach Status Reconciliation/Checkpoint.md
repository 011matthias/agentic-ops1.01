# Checkpoint: Brisken Rome Outreach Status Reconciliation

**Date:** 2026-07-16
**Status:** COMPLETE — sheet verified clean, zero remaining false-negatives

---

## Summary
Worked the Shell prep-brief and 17-contact outreach tasks, then found and fixed a mailbox-verification bug that was misclassifying during-Rome (19.06 booth) contact as post-Rome outreach on the TA Cook Rome master sheet; corrected all affected rows and confirmed via a reliable per-contact sweep that no further mistakes remain.

---

## What Was Done This Session

### Shell call prep (27 Jul, Bill Askew)
1. Created `shell-call-prep-2026-07-27.md` — internal brief on where Brisken fits Shell's SAP treasury landscape (IHB/Bank Hub/TRM). Flagged "IGF" as unclarified rather than guessed.
2. Committed locally (`2f763ed`) — **not pushed** (repo is public; brief contains Shell-specific PII/commercial detail — push decision deferred to the user).

### 17-contact outreach + TAC Rome classification
3. Classified all 17 contacts against the TA Cook Rome master-sheet Tier/lead_type scheme (H5/T1/T2/T3, sap_internal/partner_si) and explained the fit to the user.
4. Wrote context-bulletpoint briefs (not finished emails — per [[feedback_dirk_draftbox_notes_not_drafts]]) into Dirk's Outlook Drafts for every contact not yet reached post-Rome, so Dirk writes the actual email himself.
5. Fixed the Kulkarni row: "Contacted - awaiting" was reflecting the 19.06 booth invite, not a post-Rome send — corrected to "Not contacted" with the drafted brief loaded alongside the others.

### The during/post-Rome sheet reconciliation (the core of the session)
6. User flagged the general problem: "contacted-awaiting post rome is different than during rome, and this difference can not be underestimated." Set out to re-verify every "Contacted" row against actual post-27.06 mailbox activity and correct any row still reflecting only the 19.06 booth touch.
7. **Verification-theater incident:** the first pass scanned only the Inbox + Sent Items folders of both mailboxes. This missed Dirk's custom "TA Cook 2026 Rome - Outreach" folder, which holds the 07-12 T2 outreach batch — so several genuinely-contacted people got wrongly flagged "Not contacted" and duplicate drafts got created for them. User caught it: "im pretty sure these have been reached out to post rome check dirks and my email."
8. Fixed the method: switched to `/users/{mbx}/messages` (all folders, no folder restriction) with `isDraft eq false` (drafts carry a `sentDateTime` too, so without this filter a parked draft reads as a real send) and OOO-string stripping on the reply side.
9. Reverted the 6 wrongly-flipped cells back to "Contacted - awaiting reply": Diet, Lasecki, Koekkoek, Fjotland, Vergel, Jellonek. Deleted the 7 duplicate drafts created off the bad data.
10. Ran a whole-sheet reconciliation with the corrected method (`reconcile_status.py`) — hit and fixed a `NameError` (dropped `cur` assignment) before it could apply anything, then re-ran clean. Applied 9 real false-negative upgrades the original state had been carrying: Richter, Schelstraete, Bonizzoni (→ Replied), Favalli, Hetesi, Kiosses, Meyerhoff, Hamid, Reinsfelder.
11. Ran `final_audit.py` against all 19 touched cells: 18/19 exact match, 1 held for manual confirmation (Carol Tse, AA9) — confirmed correct on inspection (genuinely sent 07-09).
12. Per the user's final ask ("make sure no more mistakes anywhere else"), built and ran `robust_check.py` — a reliable per-contact `$search` (not the bulk address/name-match, which is what missed Tse) against every remaining "Not contacted" row that has a Tier assigned (32-row at-risk population). Result: **0 missed false-negatives.**

### Memory correction
13. Rewrote `feedback_brisken_outreach_truth_is_mailbox.md` to require: all-folders mailbox scan (never Inbox+Sent-only), `isDraft eq false` filtering, OOO stripping, "sheet status reflects POST-event contact only" as the standing convention, and the residual caveat that bulk address/name matching is not fully reliable — per-contact `$search` is the only method proven to catch every case (it's what found Tse).
14. Updated the `MEMORY.md` index line to match.

---

## Key Decisions Made

### Sheet status semantics
- **Choice:** "Contacted / awaiting reply" on the master sheet means a **post-2026-06-27** touch, never a during-event (19.06) booth interaction.
- **Rationale:** User explicitly called this distinction load-bearing; conflating them made the sheet lie about actual outreach state and would have caused Dirk to under- or over-contact people.

### Verification method for "was this person reached"
- **Choice:** Definitive per-contact answers use `$search` across all mail folders of both mailboxes with `isDraft eq false`; bulk address/name matching is an efficient first pass but not authoritative.
- **Rationale:** The bulk method missed Carol Tse's real 07-09 send even after adding name-matching; only the per-contact search caught it in the final robust check.

### Shell brief: commit but don't push
- **Choice:** Committed locally, left unpushed.
- **Rationale:** Repo is public (`011matthias/agentic-ops1.01`); the brief contains Shell-specific commercial/PII detail. Push is the user's call.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/deliverables/lead-generation/shell-call-prep-2026-07-27.md` | Created, committed locally (`2f763ed`) | Internal prep brief for Dirk's 27 Jul Shell call |
| TA Cook Rome master contact sheet (SharePoint, via Graph workbook API) | 19 cells corrected: 6 reverts, 9 upgrades, Kulkarni fix, Tse held/confirmed | During/post-Rome status distinction now evidence-backed |
| Dirk's Outlook Drafts (via Graph, delegated) | ~14 context-bulletpoint briefs created; 7 duplicate drafts (created off bad data) deleted | Briefs for every contact not yet reached post-Rome |
| `feedback_brisken_outreach_truth_is_mailbox.md` (memory) | Extensively rewritten | All-folders + isDraft + OOO + post-event-only convention + per-contact-search caveat |
| `MEMORY.md` (memory index) | Updated index line | Reflects the corrected method |
| `docs/sessions/2026-07-15-context.yaml` | Edited (master-sheet reconciliation marked done) | Session continuity note — later touched again by user/linter, current content is authoritative, do not revert |

---

## Current Status

The TA Cook Rome master sheet's `email outreach_status` column now correctly distinguishes during-Rome (19.06 booth) contact from genuine post-Rome (≥2026-06-27) outreach, verified two ways: `final_audit.py` (18/19 exact match on the 19 touched cells, 1 held-and-confirmed) and `robust_check.py` (0/32 false-negatives across the full "Not contacted"-with-Tier population). No further sheet writes are needed from this reconciliation.

Genuinely open outreach (not sheet errors — real gaps): **Kulkarni** and **Georgiou** have ready drafts waiting in Dirk's Drafts; **Gupta** has nothing sent or drafted yet.

Platform/ops: no `platform` section change this session; no Make.com/n8n/Trigger.dev touch.

---

## Next Steps

1. Dirk to review and send the outreach drafts now sitting in his Drafts folder (Kulkarni, Georgiou, Gupta, and the other not-yet-reached contacts) — nothing further to build; this is his action.
2. ~~User decision: push the Shell brief commit (`2f763ed`) to the public repo, or keep it local given it names Shell-specific commercial detail.~~ **RESOLVED 2026-07-16:** user chose to keep it out of the public repo. Commit `2f763ed` dropped from the branch; brief relocated to `workspace/clients/brisken/context/shell-call-prep-2026-07-27.md` (gitignored). Do not recreate it under `deliverables/`.
3. Carry forward from the prior (Sanofi Sign-Off) checkpoint, still open: Sanofi Planner slide-10 check-off (gated, owner yes needed before Friday's 16:00 call), Ashok/Accenture MDH referral confirmation, Website GTC Planner check-off, Protokoll EN verdict watch, Expense Recon card-list authoring, Lead Desk send-gate drill scheduling. None of these were touched this session; see the 2026-07-16 Sanofi Call Sign-Off checkpoint for full detail.

---

## Context for Next Session

### Files to Read First
- `feedback_brisken_outreach_truth_is_mailbox.md` (memory) — the corrected method, read before touching outreach status again
- `workspace/clients/brisken/context/pilot-routing.md` — Rome tier/lead_type classification reference
- This checkpoint, for the exact 19-cell correction list if a future audit needs to re-verify

### Open Questions
- None specific to this reconciliation — it closed clean. General Brisken open questions (4d credential decision, positioning coherence) carry over unchanged from the prior checkpoint.

### Working Notes
- **Root cause of the verification-theater incident:** Graph's `/mailFolders/{Inbox,SentItems}/messages` scoping felt "thorough enough" because it covers the two folders that hold outreach mail *by default* — but Dirk actively files sent Rome mail into a custom "TA Cook 2026 Rome - Outreach" folder (and per-account subfolders), so folder-restricted scans systematically miss his organized mail. The transferable principle: when the ground truth is "did a person receive mail," never assume a folder taxonomy — scan the whole mailbox (`/users/{mbx}/messages`) and filter by content/date, not by folder guess.
- **`isDraft` is not optional.** A parked Outlook draft carries a `sentDateTime` field even though it was never sent; any bulk sent-mail query must explicitly exclude `isDraft eq true`, or "wrote a draft" reads as "sent the email."
- **Bulk vs per-contact reliability gap:** address+name bulk matching against a 5,661-message post-event corpus missed one real send (Tse) that a targeted `$search` caught. For any future "prove nobody was missed" ask, go straight to the per-contact method — the bulk pass is a good first filter, not a final answer.
- Read-after-write lag was observed once (a Graph workbook PATCH returned 200 but an immediate re-read showed the old value) — a short retry confirmed the write had actually stuck. Not a data bug, just eventual-consistency on the SharePoint workbook API; worth a beat of delay before treating a stale re-read as a failed write.

### Reference Materials
- `workspace/clients/brisken/context/pilot-routing.md` — Tier/lead_type canonical classification
- Rome 2026 master contact sheet (SharePoint, 30_Events/TA Cook 2026) — see [[project_brisken_rome_master_contact_sheet]]

---

## How to Continue

The reconciliation task is closed — no further sheet work needed. The Shell-brief push question is resolved (kept local, moved to gitignored `context/`, commit dropped — see Next Steps item 2). If a fresh session picks this up, the only live thread is Dirk actually sending the outreach drafts now waiting for him. Everything else is the carryover Brisken backlog from the Sanofi Call Sign-Off checkpoint, unrelated to this reconciliation.

---

## Strategic Feedback

### What Worked Well This Session
- The user's specific, evidence-pointed correction ("check dirks and my email") redirected the debugging immediately to the actual root cause (folder scoping) instead of a longer blind search.
- Building `robust_check.py` as a distinct, more-reliable verification pass (rather than trusting the same bulk method twice) is what actually surfaced the "0 missed" confidence the user asked for.

### Suggestions
- None outstanding beyond what's already banked in the memory file — the all-folders + isDraft + per-contact-search method is now written down and should be the default starting point next time, not something to rediscover under correction.

### System Health
- The corrected memory file directly targets a recurrence class (folder-scoped mailbox reads) that had already cost one full debugging cycle this session; worth watching whether it holds the next time a Brisken outreach-status question comes up.
- This is the third documented-only occurrence of the same root class (folder/mailbox-scope verification-theater on Brisken outreach checks — see 2026-07-14 Wix-sweep and 2026-07-11 #381 entries in the friction register). A memory fix has now been written three times for variants of this pattern without a structural backstop; a `brisken-mailbox-watch.py`-style all-folders helper (proposed in earlier register rows) would close it at the tool layer instead of relying on recall each time.

Autonomy score: 1 human intervention this session (the mailbox-scope correction). Everything else — the Shell brief, the 17-contact classification, the drafts, the final robust-check sweep — ran without a correction.
