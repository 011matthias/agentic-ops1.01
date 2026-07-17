# Mini-Checkpoint: Brisken Lead Desk Outreach Integration

**Date:** 2026-07-15
**Status:** Complete — sheet is the single source of truth for post-event outreach; board reflects it
**Type:** mini

---

## Summary
Finished the Lead Desk during-event dedupe, root-caused the recurring "who's been contacted" confusion (the board can't see Dirk's personal Outlook sends), and reconciled 17 mailbox-discovered post-event follow-ups onto the master sheet (7 real gaps written, 10 already logged) so the board reflects them via the Graph sheet-sync. Mailbox-direct grounding (PR #226) closed as redundant.

## What Was Done
- **126 import during-event dupes stripped from prod** (`lead-desk-ground --drop-import-dupes` on brisken-lead-desk). Christos Georgiou verified at exactly 5 events (E1/E2/E3 + reply source=graph + Dirk touch), no import E-wave rows.
- **Christos re-connect brief** created in Dirk's Outlook Drafts via Graph `Mail.ReadWrite` (threaded reply, To Christos, BCC Zoho dropbox, brief bullets for Dirk to write). Nothing sent.
- **Root cause of the recurring outreach confusion** found + operationalized: the Lead Desk event log only captures E-waves (Graph-grounded) + the sheet's `post_event_outreach` column; Dirk's personal Outlook post-event sends are invisible to it. New rule: answer "who's been contacted" from a both-mailbox Graph Sent-Items scan, never the event log. Saved `feedback_brisken_outreach_truth_is_mailbox.md`.
- **Built `ground.ground_direct`** (mailbox → Lead Desk direct/post-event events; 143 tests, PR #226) — used its classifier as the DISCOVERY tool. Found 17 real post-event follow-ups the board never showed.
- **Master sheet grounded (the deliverable):** filled 7 BLANK `post_event_outreach` cells (Adidas/Roche×2/JTI×2/SAP-accept/Shell-accept) via Graph delegated token, tagged `(mailbox)`, Dirk's 36 entries preserved (36→43). Verified 300/34 unchanged, "REMOVE" note intact.
- **Reconciled onto the sheet-as-source:** PR #226 CLOSED; ran `lead-desk-sync` on prod (idempotent, `events=0` — the startup auto-sync had already imported the edits). Board now shows the 7 as `Post-event follow-up` (P badge); JB/Carol/William confirmed carrying the mailbox-tagged detail.

## Current Status
Sheet write + prod sync + PR closure all verified. No-send hold still ENGAGED (no email sent all session; only a draft created + internal tracking writes). Debug-Edge left running on :9222 (workbook open in edit mode); `.scratch/graph_token.txt` expiring. `ground_direct` code lives on the closed-PR branch `client/brisken/lead-desk-ground-outreach` (not merged, not deployed).

Friction (mini, not full-audited): B1 stop-hook fired 2× on closing "want me to / say the word" deferrals (agent-deferred, B1); cd-guard fired 1× (corrected to no-cd); iteration-3x gate fired 2× (distinct capability probes + env-plumbing reruns, not a real fix loop). Owner also flagged the recurring outreach-confusion as "problematic" → addressed with the new rule.

## Next Steps
1. **Run the full master-sheet grounding prompt** (written this session) — reconcile the sheet against ALL data sources (both mailboxes, calendar, Zoho CRM, Sales Nav list, Lead Desk DB, Dirk's drafts, Planner, booth data) once and for all, non-destructively.
2. Decide whether to automate mailbox→sheet gap-fill (what was done manually for the 7) as a periodic tool, OR keep it manual.
3. Close the debug-Edge on :9222 when done; token in `.scratch/graph_token.txt` is transient.

## Files to Read First
- `~/.claude/.../memory/project_brisken_lead_desk.md` (state + the reconciliation pipeline)
- `~/.claude/.../memory/project_brisken_rome_master_contact_sheet.md` (Graph-workbook access, token-grab mechanism)
- `~/.claude/.../memory/feedback_brisken_outreach_truth_is_mailbox.md` (the mailbox-is-truth rule)
- `workspace/clients/brisken/automations/lead-desk/src/lead_desk/{ground.py,sync.py,migrate.py}`
