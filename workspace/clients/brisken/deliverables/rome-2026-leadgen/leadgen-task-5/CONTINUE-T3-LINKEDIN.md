# Fresh-chat prompt: Rome Tier 3 LinkedIn outreach

Paste everything below into a new Claude Code chat.

---

Load agentic-ops, Brisken Lead Generation. This continues the Rome post-event LinkedIn motion. A prior session finished Tier 2 (warm-engaged) LinkedIn + Sales Nav; now do **Tier 3**.

## Step 1 — Reference the Planner task

In Microsoft Planner, plan "MARKETING PLAN", bucket "Lead Generation", open the task **"Rome Tier 3 booth/token-network: LinkedIn + Sales Nav"** (id `a7c6yU3_DEOjqnG08LBR22UAL5yv`, currently the 4th open task on the board). Read its description and both checklist items. Also read the sibling **"Rome Tier 3 booth/token-network: email outreach"** for the segment definition, and skim **"Rome booth/token-network: GDPR consent email"** so you keep the LinkedIn connect distinct from the consent email (they are different tasks). Restate in one sentence which task you resolved before doing any work. If the board will not load, stop and ask rather than guess.

Access (all read-only): Graph token via `.scratch/grabtoken.py` (sniffs a bearer off the CDP Edge on `:9222`); board listing via `.scratch/leadgen_open.py`; task detail via a small Graph GET on `/planner/tasks/{id}/details`.

## Step 2 — Build the Tier-3 roster

Segment = the **`fob_encoded`** booth/token-network set in the master sheet `workspace/clients/brisken/context/lead-generation/Rome-Event/event-admin/rome2026-post-event-master-contacts.xlsx`. Posture is **relationship-first (the Brisken Token network), no product pitch** (that is the whole point of Tier 3; the pitch lives in higher tiers).

**Dedup by explicit name against every prior tier so nobody is double-contacted:**
- **hottest-5:** VW (Zucknick, Landrø), JTI (Disdet, Cuello), Roche (Herrera La Grotta, Yesil), Adidas (Tse), LSEG (Bonizzoni, Favalli).
- **Tier-1 nineteen:** enumerated in the "Rome Tier 1 leads: LinkedIn + Sales Nav" task description.
- **Tier-2 eighteen:** `output/leadgen-task-5/tier2-roster.csv` (from the prior session).

WARNING: the master sheet was regenerated 2026-07-10 and the `post_event_outreach` status column that used to flag the 19 Tier-1 was **dropped** (row count 298 -> 290). Dedup by NAME against the rosters above, NOT by any sheet status column, or the 19 will slip back in. Re-read the sheet fresh; it is a moving target across the parallel sessions.

Expected pool: about 45 after dedup (roughly 68 `fob_encoded` survive stop + Tier-2 removal, but that still includes the 19 Tier-1 and hottest-5 because the status column is gone). Around 23 have no LinkedIn URL on file.

## Step 3 — Mirror the Tier-2 deliverables exactly (they worked)

Copy the shape of `output/leadgen-task-5/`:
1. **Roster CSV** — one row per contact: segment/branch, booth record (`in_our_booth` / `scanned_at_booth`), on-file `linkedin_url` or a built Sales Nav search URL, the connect note, and `salesnav_add` + `linkedin_connect` status columns to tick in place. Strip legal suffixes (`A/S`, `ASA`, `AG`, `SE`, `GmbH`) from Sales Nav search keywords and percent-encode; they hurt recall.
2. **LinkedIn connect runbook** — from Dirk's account, paced ~20/day (LinkedIn throttles note-invites). Relationship / token-network note, **no pitch**. Branch the opener on booth attendance: "good to meet you at our booth" for scanned/booth-registered, a softer "good to connect after Rome" for the rest. Every note **≤200 chars** (free-account cap) and **zero em-dashes**.
3. **Sales Nav add runbook** — Matthias's seat, add to the **"TA Cook Rome 26"** list, in paced batches of six. `.scratch/open_tabs.py` opens tabs over CDP if wanted; it only opens tabs.
4. **Resolved-profiles pass** — most Tier-3 rows have no URL on file, and Sales Nav keyword search will not surface everyone. Run a web-search workflow (one agent per contact, verify each hit on company AND a treasury/SAP role, return null rather than a wrong person, since these feed connection requests under Dirk's name). Fold the results into the roster as `resolved_linkedin_url` / `resolve_confidence` / `resolve_note`, and write a `resolved-profiles.md`. This is what turned the Tier-2 stragglers into direct links.

**Volume flag:** ~45 people is a multi-day LinkedIn motion (throttle ~20/day; a free account also caps note-invites at ~5/month). Surface whether to send note-less connects at this volume, or spread it, rather than assuming.

## Reference files
- Segmentation method + how a tier is derived: `output/leadgen-task-5/segmentation.md` and `SUMMARY.md`.
- Token-network track (Tier-3 posture, "share info, explain the network, relationship not pitch"): `workspace/clients/brisken/context/lead-generation/Rome-Event/rome-post-event-plan.md` (track 1) and `post-event-sequences.md` (Tier 3 paragraph + the did-not-attend branch copy).
- Naming: `workspace/clients/brisken/TASK-NAMING-STANDARD.md` (§2/§3 partly superseded; see the planner memory).

## Isolation (parallel sessions run concurrently, strict)
- Work in a git worktree/branch `leadgen/task-4` (T3 LinkedIn is board-position 4; confirm before naming). Sibling worktrees live at `../agentic-ops1-leadgen-task-N`.
- Write all outputs to `output/leadgen-task-4/`. Do NOT edit shared files (write proposals to `output/leadgen-task-4/shared-file-proposals.md` instead), do NOT mark the Planner task complete, do NOT touch other tasks. Comment on your own task only. Note cross-task findings in `output/leadgen-task-4/notes-for-other-tasks.md`.

## Definition of done
Roster + both runbooks + resolved profile URLs committed on `leadgen/task-4`; a `SUMMARY.md` (what was built, what needs a manual step with exact instructions, open questions); and a short paste-ready Planner status comment.

---
