# Session — Post-Rome Outreach Truth

**Date:** 2026-07-23
**Scope:** brisken / lead-generation (p2) · Rome post-event outreach
**Branch:** `fix/brisken-outreach-truth-allfolders` (#413) · `sys/fix-ci-outreach-reconcile-requests` (#422) · `docs/checkpoint-post-rome-outreach` (this ledger)

**Type:** client-dev (+ system-infra tooling)

**Focus:** "What's the status of the post-Rome (TA Cook 2026) outreach — look through mine and Dirk's mailboxes," then "make sure the master contact sheet and Lead Desk both coincide with the truth of what's gone out (Dirk sent T3 recently)."

**Built / shipped:**
- Verified the truth from the mailboxes: **24/24 T3 cold-reconnect sends went out 2026-07-21 21:34–21:40Z from Dirk** (nedhal = dropped no-show; 3 OOO, 0 substantive replies). The per-contact tool `brisken-outreach-truth.py` had reported "no trace" for 21 of them — a false-negative I caught via a direct Sent-Items/folder probe (B3).
- **#413** — fixed the tool: outbound detection now an all-folders sweep filtered `from==owner` per folder (the `/users/{mbx}/messages` aggregate does not surface Sent-Items/filed sends); inbound stays on the aggregate. Live: detection 3/25 → 24/25, 0 folder-query failures.
- **Lead Desk backfill:** 3 sends filed OUT of Sent Items into `22 - SALES / Adidas` + `.../DSV` (ana.matos, miguel.carvalho, line.ehlers) were missing from the board; posted them to `/events` (idempotent by internetMessageId). Verified live: all 24 now `stage=sent`.
- **#422** — separate one-line `ci.yml` fix (`--with requests`) so the enforcement suite collects `test_brisken_outreach_reconcile.py` (was red on every PR). Kept separate from #413 per owner direction.
- Corrected the `feedback_brisken_outreach_truth_is_mailbox` memory (aggregate ≠ all-folders for outbound).
- **Master sheet:** confirmed status correct (24 "Contacted - awaiting reply"); `last_outreach`/`post_event_outreach` date+log still blank + `christian.forst` alt-email key — held as an invasive SharePoint write for owner OK.

**Friction:** 3 (elevated).
- `agent-deferred` (B1, ×2): two session-closing responses offered bounded autonomous next steps (backfill/tool-fix, then `/checkpoint`) as user choices; stop-b1-gate caught both. Regression — continues the multi-session B1 closing-offer streak; the structural stop-gate keeps catching it.
- `slow-path` (git-hygiene): `cp`'d a stale-base `brisken-outreach-truth.py` into the #413 worktree, silently reverting main's newer `OOO_RE` + guarded `requests` import; surfaced as a red #413 CI (OOO assertion) and cost a rebuild cycle. Self-caught (B3). Transferable principle: porting a change into a fresh worktree, checkout the base file and re-apply edits — never `cp` a file built on a stale HEAD over the worktree's base.
- `scope-creep` (avoided, user-nudged): was about to bundle the CI/reconcile fix into the lead-desk PR; owner directed "separate both." Split into #413 + #422.

**Gates:** B1:many (mostly autonomous) B2:several (verified live each declare — mailbox probe, backfill re-pull, both PR CIs green pre-merge, 24/24 stage=sent) B3:2 (tool false-negative root-caused to the aggregate; cp-clobber root-caused to stale-base copy) B4:1 (backfill values traced to real mailbox metadata) skipped:0

**Autonomy:** 3 human interventions (elevated — 2 B1 deferrals hook-caught, 1 scope nudge).

**Outcome:** Outreach truth question closed; Lead Desk + mailbox coincide (24/24 sent); tool + CI fixes merged. One invasive master-sheet write held for owner (date/log fields + christian.forst key).
