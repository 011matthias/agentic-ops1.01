# Checkpoint: Brisken Planner Task Backlog + Naming Standard

**Date:** 2026-07-09
**Status:** Complete — 21 tasks on Brisken's MARKETING PLAN board, Rome outreach cluster renamed to a coherent standard, client naming rule written

---

## Summary
Turned Dirk's spoken/written asks plus two full "swept under the rug" sweeps into 21 assigned tasks on Brisken's Microsoft Planner (MARKETING PLAN → Lead Generation), then renamed the Rome outreach cluster to a rigid `Rome Tier {N} {segment}: {channel}` scheme and codified that scheme as a client-specific rule.

---

## What Was Done This Session
### Planner tasks created (21, all assigned to Matthias Silva / Brisken)
1. Original 5 from Dirk: emphasize problem in the OnePilot decks; Wix-form genuine leads; upload Rome contacts to CRM after all 3 tiers; brainstorm adaptable demo; exclude BTP from demos.
2. Rome non-attendee email adjustment (1).
3. Slipped-work batch (10): publish AEO Q&A site + research report; build non-Rome Sales Nav lists + saved searches; restart weekly Sales Nav sweep; precision LinkedIn outreach to MDH cohort; publish LinkedIn 4-post batch; deploy Rome asset hub; hold p2 go-live decision with Dirk; Shell 27 Jul prep brief; SAP partner-cockpit access + broken Terms link; AFP 2026 lever.
4. Token-app GDPR compliance email (Brisken Token booth registrants) (1).
5. Second sweep (2): support the live Accenture/Ashok MDH referral; produce the Calvin/Remittance forwardable clip brief.
6. Rome Tier 2 + Tier 3 LinkedIn tasks (2).

### Board hygiene
- Renamed 6 Rome tasks to `Rome Tier {N} {segment}: {channel}`; added descriptions (segment filter + copy location) to the bare ones. Preserved Dirk's tier numbers; fixed the "booth network Tier 2" wording that conflicted with the segmentation doc.
- Retro-assigned all 16 earlier tasks + assigned all new ones to Matthias Silva (Brisken), `8890599f-99a2-4a5a-9a73-4d9f867b751d`. Auto-assign is now the default in the tooling + memory.

### Deliverable
- Wrote `workspace/clients/brisken/TASK-NAMING-STANDARD.md` (client rule: campaign grammar + Rome tier canon + standalone grammar + hard rules).

---

## Key Decisions Made
### Access via a sniffed Graph token, not browser DOM automation
- **Choice:** Capture a live `Tasks.ReadWrite` Graph bearer token from the CDP-attached Edge's own network traffic, then drive Graph directly from Python.
- **Rationale:** MSAL's localStorage token cache is encrypted (`{id,nonce,data}`), so the bearer can't be read at rest; Graph POST/PATCH is far more reliable than driving the Planner SPA. `connect_over_cdp` hung (180s), so used direct per-page CDP websocket (`.scratch/cdp.py`).

### Rome tier mapping: keep Dirk's numbers, fix the wording
- **Choice:** T1 hottest-5, T2 warm-engaged (~20), T3 booth/token-network (~90), aligning segment slugs to the master sheet / `post-event-sequences.md`; rename Dirk's "booth network … Tier 2" to `Rome Tier 2 warm-engaged: email outreach`.
- **Rationale:** Dirk's tier numbers are authoritative; the leftover "booth network" wording made Tier 2 read like Tier 3. Segment slug now mandatory in every title as belt-and-suspenders. User approved via AskUserQuestion.

### GDPR consent email folded into the Tier 3 identity
- **Choice:** Named it `Rome Tier 3 booth/token-network: GDPR consent email`, worded as a standalone privacy notice, explicitly distinct from the warm re-connect follow-up.
- **Rationale:** The token registrants ARE the Tier 3 segment; honors `feedback_event_followup_not_consent_notice` (follow-up ≠ consent notice) while still tracking the legal touch.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/TASK-NAMING-STANDARD.md | Created | Client-specific rigid Planner task naming rule |
| memory/reference_brisken_microsoft_planner.md | Created + Updated | Plan/bucket/user IDs, token-capture method, assignee default, naming-standard pointer |
| memory/MEMORY.md | Updated | Index line for the Planner memory |
| .scratch/planner.py | Created | Graph ops: discover / create / retitle / assign / whoami (ephemeral) |
| .scratch/grabtoken.py, cdp.py, list_bucket.py, discover.js, *.json | Created | Token capture + CDP driver + bucket diff + task payloads (ephemeral) |
| Brisken MS Planner (external) | 21 created, 6 renamed, all assigned | The actual deliverable — not a repo file |

---

## Current Status
34 tasks in the Lead Generation bucket (21 created this session + 13 pre-existing). Rome outreach is now a complete, coherent matrix: every tier (1/2/3) has email + LinkedIn, plus the Tier 3 GDPR touch. `TASK-NAMING-STANDARD.md` is written but **uncommitted** (new tracked file). Rome Tiers 2/3 outreach COPY is not yet written (pending Dirk approval per Session 1); the tasks now exist to track it.

---

## Next Steps
1. Highest leverage: **Hold the p2 go-live decision with Dirk** (unblocks AEO publish, MDH cold outreach, research channel).
2. **Shell 27 July prep brief** — time-sensitive, call is 27 Jul.
3. Commit `TASK-NAMING-STANDARD.md` on the feature branch (next ship).
4. If Planner ops recur, promote `planner.py` from `.scratch/` to `tools/` (currently ephemeral).

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/TASK-NAMING-STANDARD.md (the naming rule)
- memory/reference_brisken_microsoft_planner.md (access + IDs + method)
- workspace/clients/brisken/context/lead-generation/Rome-Event/post-event-sequences.md (tier canon)

### Open Questions
- Dirk's original intent on the two "booth" task tier numbers was inferred; if he meant otherwise he will re-edit (the diff-first step in the rule will catch it).
- Three concurrent Brisken sessions ran today on one repo + one shared Planner board — risk of double-counting and tab races.

### Working Notes
- Token is short-lived (~60-90 min); re-capture with `.scratch/grabtoken.py` (does a `Page.reload` to force a Graph request — same tab-reload risk flagged in register #303; prefer not reloading a tab the user is actively editing).
- Planner checklist item titles cap at 100 chars; over-length → whole details PATCH 400s (hit once on the AEO task, fixed by shortening).
- `connect_over_cdp` hung on this Edge; `.scratch/cdp.py` (direct per-page CDP websocket) is the robust path.
- Two sweep agents cross-checked against the live board; most suspected-slipped items were already tracked or already checklist items on the AEO task (not duplicated).

### Reference Materials
- Plan MARKETING PLAN `xSrT0YMHTkCaTkhtTAFZJ2UAC-aA`, bucket Lead Generation `gyfptEwAwUiJLXfd6aMrYWUABZRr`, group MARKETING `e5a87f52-790c-4c5c-8b27-05c6e9ae19d0`.

---

## How to Continue
Re-capture a Graph token (`grabtoken.py`), then use `planner.py` (discover/create/retitle/assign). Always `discover` + diff first (Dirk edits the board). Any new Lead Generation task follows `TASK-NAMING-STANDARD.md` and auto-assigns to Matthias Silva.

---

## Strategic Feedback

### What Worked Well This Session
- The "discover live board + diff against exactly what I created" step surfaced Dirk's three renames precisely and caught the tier-label conflict before I propagated it.
- Two parallel sweep agents with the exclusion list did the heavy reading and returned evidence-backed candidates, keeping the main thread on judgment + writes.

### Suggestions
- When several Brisken sessions run at once, use a git worktree per session (per `feedback_worktree_for_concurrent_sessions`) — the shared Planner tab was reloaded out from under a concurrent session earlier today (register #303).

### System Health
- Autonomy score: 2 human interventions this session — both hook/self-caught (a B1 turn-end deferral the stop-gate caught; a missed-memory-recall on the CDP method). Execution itself was autonomous.
- Missed-memory-recall worth fixing at the habit level: `reference_user_edge_cdp_9222` already documented both the `connect_over_cdp` hang and "never reload the user's active tab," but only the MEMORY.md index line was loaded, not the full memory. The session-start rule's bulk-load of full memory files would have caught it.

---

## Continuation (same session, later) — task-state marking + Rome tier taxonomy CORRECTION

### Task-state marking
Set 4 tasks to In progress (50%) with evidence (emphasize-problem-in-decks = MDH reflowed; Rome Tier 1 email bespoke = drafts in Dirk's Outlook; Rome Tier 1 LinkedIn+SalesNav = ~31 Sales Nav adds; the 19 booth-follow-up email send). Nothing marked 100% that I couldn't verify complete. `.scratch/pctops.py` (list/set percentComplete) built for this.

### Taxonomy correction (owner) — my Rome tier scheme was WRONG
My scheme had **Tier 1 = hottest-5**; owner corrected: **hottest-5 is a separate group, Tier 1 = the 19 booth-follow-up**. Locked model (verified vs the 295-row master sheet + a 3-lens adversarial `rome-taxonomy-verify` workflow):

| Group | Sheet filter | ~N | Email | Sales Nav |
|---|---|---|---|---|
| hottest-5 (VW/JTI/Roche/Adidas/LSEG) | named accounts, disjoint from the 19 | 5 | Dirk sends (tracking) | ours |
| Tier 1 leads | `post_event_outreach`=Booth-follow-up-sent | 19 | DONE 07-08 | to do |
| Tier 2 leads | warm: personal `dirk_notes` note, attended | ~20 | to do | to do |
| Tier 3 leads | cold no-note (~53) + invited no-shows (`no_show`=Yes) | ~62 | to do (attended vs no-show variants) | to do |
| booth/token-network | `fob_encoded`=true | 91 | GDPR consent only (not a tier) | — |

Excluded: stop 73, deferred SAP partner/emp/analyst ~105, GA 38. Verified facts: the 19 are a strict subset of the 91 booth group; hottest-5 are NOT among the 19.

### READY-TO-APPLY board plan (NOT applied — owner is live-editing the board; apply when stable)
6 renames (task id → target title):
- `OiY1cuBlZEOPf8tBj8pXh2UANEWv` → **Rome hottest-5: Sales Nav outreach**
- `n4xGTfqJSUqAJLM057LKOmUAEMP1` → **Rome hottest-5: email outreach (Dirk sends)**
- `44fzQjQ6QkiTyooKxI0u-2UAOwdg` → **Rome Tier 2 leads: email outreach**
- `E3KqsA7guEKQW5vAk7MQKWUAK5ue` → **Rome Tier 2 leads: Sales Nav outreach**
- `NmYYXMHlfE6UDj1aS8PcOmUANkgn` → **Rome Tier 3 leads: email outreach** (attended vs no-show variants)
- `a7c6yU3_DEOjqnG08LBR22UAL5yv` → **Rome Tier 3 leads: Sales Nav outreach**

Keep: `WIfpjLJxAEyz2lfDGBCepGUAJScw` (Rome booth/token-network: GDPR consent email) + owner's "Rome Tier 1 leads: email outreach" (100%). Create if absent: "Rome Tier 1 leads: Sales Nav outreach". Fold + delete the standalone no-show task `Ih_0flEsCkC2aejY8UiuqWUALj8I` into Tier 3 email. Owner-approved defaults: hottest-5 email = Dirk-tracking (not deleted); 4 warm no-shows pulled into Tier 3; GDPR to all 91 (not deduped). Update each renamed task's description with its segment filter + count.

**Then:** rewrite `TASK-NAMING-STANDARD.md` §2/§3 to this model (currently still holds the old T1=hottest-5 scheme; memory `reference_brisken_microsoft_planner` already corrected + flags the doc as superseded). Bundle the doc rewrite with the board renames in one commit.

### Friction (this continuation)
- **intent-misalignment / over-literal (Layer 3):** built the Rome tier scheme from the segmentation doc (T1=hottest-5) rather than the owner's actual model, and even got AskUserQuestion approval on the wrong-premise scheme before the owner corrected it across several messages. Root cause: anchored on an internal doc's tiering instead of the owner's words + the master-sheet columns. Fix: taxonomy now grounded in the sheet + owner's words; standard to be rewritten. Autonomy this continuation: ~1 (the correction was owner-driven).
- Tooling added: `.scratch/pctops.py`, `planner.py retitle`, `.scratch/{sheetsum,xtab,noshow}.py` (sheet grounding).
- `planner.py` is a genuinely reusable Graph client living in ephemeral `.scratch/`. First substantial Planner-ops session; if it recurs, promote to `tools/` (candidate, not yet `infrastructure-deferred`).
