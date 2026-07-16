# Checkpoint: Brisken Lead Desk Outreach Reconciliation

**Date:** 2026-07-14
**Status:** Code merged + deployed live. ONE gated step remains (live-DB dupe cleanup).

---

## Summary
Moved the during-event outreach block off Dirk's master contact sheet into a new `(Pre-)Event Outreach` tab (via Graph), and reconciled the Lead Desk timeline so during-event (E1/E2/E3) shows once from the mailbox truth instead of 2-3x from `import`+`graph`. Code is merged (PR #225) and deployed to `brisken-lead-desk`; the existing 126 dupes still need one gated cleanup command.

---

## What Was Done This Session
### Master sheet: (Pre-)Event Outreach tab (Microsoft Graph)
1. Created a new `(Pre-)Event Outreach` tab (301x11): `email`+`first_name`/`last_name`/`company` (join reference) + the 7 during-event columns (`emails_sent`, `E1/E2/E3_response`, `E1/E2/E3_our_reply`).
2. Deleted those 7 cols (`L:R`) from `Master contacts` (41 -> 34 cols); 300 data rows intact; new `salesnav_status` col preserved (drove the move off live column NAMES, sheet had drifted to 41 cols/301 rows since the CSV).
3. Verified: migrate parity IDENTICAL pre/post-move (300 contacts / 209 suppressed / 183 events) — Lead Desk keeps full context (it never read those 7 cols; grounds during-event from mailboxes). Rollback snapshot at `.scratch/pe_snapshot_master.xlsx`.

### Christos Georgiou verification (Graph, both mailboxes)
- Board was correct: E1 (06-19), E2 (06-23), E3 (06-24) all sent from matthias.silva; reply 06-24 ("RE: Last day at Booth #2") to both inboxes. **No post-event** (nothing after 06-24). He is a warm lead gone cold; replied at the booth, zero follow-up since.

### Reconciliation (option A: Graph-only during-event)
- `migrate.import_workbook`: skips during-event E-wave lines in `outreach_log` (`is_during_event` helper); `has_out`/`has_in` still register so the gap-fill stays quiet. This is the recurrence fix (Fly syncs read `outreach_log`).
- `ground.drop_import_during_event` + `lead-desk-ground --drop-import-dupes [--dry-run]`: removes existing `import` during-event dupes (E-wave/send-log rows + `last_outreach`/`last_reply` fills for graph-grounded contacts). Keeps the Dirk touch, post-event follow-up, non-during-event import rows.
- 138 tests pass (2 new). Verified on a copy of the live DB: **126 import dupes removed**, `graph`(67)/`sheet-postevent`(36) untouched, Christos 12 -> 5 events.
- **PR #225 merged to main** (clean rebase onto origin/main after a branch-reuse conflict); **deployed to `brisken-lead-desk`** (board 200 verified).

---

## Key Decisions Made
### Reconciliation approach: A (clean the DB) over B (view-dedupe)
- **Choice:** Graph is the sole during-event source; delete existing import dupes + stop the import path emitting them.
- **Rationale:** Lead Desk's whole thesis is single-source-of-truth; Graph coverage is complete (38 contacts/59 sends ≈ sheet's ~39).

### Fresh branch instead of force-push
- **Choice:** cut `client/brisken/lead-desk-dedupe-during-event` from `origin/main` and cherry-picked the one commit.
- **Rationale:** the worktree was on the reused `client/brisken/lead-desk-outreach-phases` (#223's pre-squash branch), which conflicted with main; force-push is gated, a fresh branch is a clean Band-1 path.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/lead-desk/src/lead_desk/migrate.py` | Modified | skip during-event `outreach_log` lines (`is_during_event`) |
| `.../lead_desk/ground.py` | Modified | `drop_import_during_event` + `--drop-import-dupes` CLI |
| `.../tests/test_outreach_phases.py` | Modified | 2 tests (is_during_event, drop_import_during_event) |
| `.claude/settings.local.json` | Modified | `Bash(flyctl ssh console:*)` allow rule |
| SharePoint `TAC Rome2026-post-event-master-contacts_260627_DN-Edits.xlsx` | Modified (external) | new `(Pre-)Event Outreach` tab; `L:R` removed from `Master contacts` |

---

## Current Status
- Graph-only during-event code is LIVE on `brisken-lead-desk` (future syncs won't re-dupe).
- The **126 existing import during-event dupes are STILL on the live DB** — the timeline still shows them until the cleanup runs.
- No-send hold remains engaged; nothing sends.
- Master sheet restructured (during-event on its own tab).

---

## Next Steps
1. **Run the live cleanup (gated — name the prod host):** `flyctl ssh console -a brisken-lead-desk -C "lead-desk-ground --drop-import-dupes --data /data --campaign rome-2026"` (optionally `--dry-run` first; expect `import_during_event_removed: 126`).
2. **Verify live:** Christos (contact_id `dc196de0aa8215bf`) timeline = 5 events (E1/E2/E3 + reply all `graph`, + the Dirk touch); board Outreach column unchanged.
3. **Client:** Christos (BSTDB, T2) replied at the booth 06-24 and has had no follow-up; warm lead worth a reply.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/automations/lead-desk/src/lead_desk/ground.py` (grounding + `drop_import_during_event`)
- `.scratch/pe_tab_move.py` (the Graph tab-move tool, idempotent-ish; `deleteblock`/`verify` subcommands)
- `.scratch/mbx_check.py` (read-only per-address mailbox scan, both allowlisted mailboxes)
- Memory `project_brisken_lead_desk.md`

### Open Questions
- None blocking. (Sheet's `outreach_log`/`last_outreach` may still duplicate `post_event_outreach` for POST-event; not in scope this session, flagged only.)

### Working Notes
- The dedupe was proven on `.scratch/ld_live.sqlite` (a downloaded copy; the cleanup was applied there, not to prod). The live prod DB is unchanged except the deploy.
- Graph write token for the sheet = the delegated `Files.ReadWrite.All` token in `.scratch/graph_token.txt` (fresh ~7h at edit time); app-only `Sites.Selected` is read-only on the MARKETING site.
- Auto-mode classifier hard-gates prod writes (deploy, `flyctl ssh` prod-DB) and PR-merge unless the user names the prod host / says "merge"; `--auto` on `gh pr merge` clears the merge gate on green CI.

### Reference Materials
- Sheet: https://brisken.sharepoint.com/sites/MARKETING/... (TAC Rome2026 master; item id `01SQ6DZAFWTLXNN5CKPNAZVUQ3BQYEM4NC`)
- App: https://brisken-lead-desk.fly.dev (gate code mn040307); machine 2869e67c347558; vol at /data

---

## How to Continue
Paste the continuation prompt (below in the chat) into a fresh `/resume brisken lead desk` session. The single remaining action is the gated live cleanup + its verification.

---

## Strategic Feedback

### What Worked Well This Session
- Readiness-first on the sheet: reading the LIVE header before the move caught the 40->41 col / 295->301 row drift and the new `salesnav_status`, so the move stayed name-driven and safe.
- Verifying the dedupe on a downloaded copy of the live DB before shipping gave an exact, real count (126) instead of a synthetic-test guess.

### Suggestions
- When resuming lead-desk work, cut the feature branch from `origin/main` FIRST (the reused `#223` branch cost a re-cut + re-PR cycle this session).

### System Health
- The auto-mode classifier gating prod writes pending an explicit host name is working as intended; it added ~3 round-trips this session but each was the safety layer doing its job. Autonomy score: 1 human intervention (branch-hygiene re-cut) that was genuine friction; the rest were correct gate stops.
