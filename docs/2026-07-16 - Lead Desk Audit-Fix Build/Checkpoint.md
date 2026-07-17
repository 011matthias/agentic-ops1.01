# Checkpoint: Lead Desk Audit-Fix Build

**Date:** 2026-07-16
**Status:** COMPLETE — all 53 audit-fix findings shipped, merged, deployed, live-verified. No-send hold intact. 4d is the committed follow-up build.

---

## Summary
Executed the approved 54-finding Lead Desk audit-fix plan (everything except 4d)
as 9 phases (P0–P8 + a P1a addendum), each a full branch → tests → PR → CI-green
squash-merge → `flyctl deploy` → live-verify cycle on `brisken-lead-desk.fly.dev`.
212 tests pass; prod schema at `user_version=4`; the no-send hold
(`kill_switch=1`, rome-2026 `done`, `send_attempts=0`, `sequences=0`) was asserted
at every phase and confirmed at the end.

---

## What Was Done This Session
### Shipped phases (PRs #229–#238)
1. **P0** migration runner (`PRAGMA user_version`, `_MIGRATIONS`, `_add_column`; views moved to `_VIEWS`, DROP+CREATE so definition changes reach the deployed DB), tzdata pinned, `lead-desk-maint clean-orphan-state`.
2. **P1** board truth: enroll-on-sync + `build_board` UNION of un-enrolled → full roster (live 80/210 → **92 active/245 suppressed**; hot repliers Askew/Gupta visible), search falls back to suppressed, sheet-status display column.
3. **P1a** name-aware anon key (caught in rehearsal — see Key Decisions).
4. **P2** derivation correctness (11): full-precision answered test, future-due deferral, stage-agnostic dangling, bant_budget, demo/verdict reversibility, "Needs action" chip.
5. **P3** legibility (11): tier legend, STAGE_LABELS, hide empty cols, Mark replied, sticky save bar, modal a11y, responsive, login theme.
6. **P4** engine safety (5): kill-switch "HALTED not LIVE" banner both surfaces, affordance inversion, done-campaign closed record, retry resets attempt_count, approve done-guard. **Also fixed a pre-existing test time-bomb.**
7. **P5** sync robustness (7): backoff + last_sync state, freshness strip, sheet-differs warning, CSV collapse+degree validation, optimistic lock, ground.py subject hardening.
8. **P6** operator features (4): merge-duplicate (tombstone + `merged_into`), 4b context brief, board inline quick-edit, saved views.
9. **P7** security (5): token iat+expiry, /login throttle (Fly-Client-IP), CSRF (double-submit + pure-ASGI middleware), security headers, /sync OPEN_PATHS.
10. **P8** capture readiness (5, provably inert): calendar +60d, auto-reply→note, NDR→bounce, dual-mailbox allowlist.

### Prod ops (rehearsed on pulled copies, backups on volume, PII copies deleted)
- P0 orphan-state cleanup (11 keys); P1 named-anon rekey (1 true dup merged); P1 adopt/enroll backfill (all 337 enrolled). Backups `bak-p0-20260715`, `bak-p1-20260716`.

### Closeout
- Updated `project_brisken_lead_desk` memory (fixes + corrected the stale "sync inert/503" note — Graph sync is LIVE).
- Logged +8.5h to the Lead Generation hours tab (rows 41–43).

---

## Key Decisions Made
### P1a — anon key made name-aware (a B4 data-integrity catch)
- **Choice:** The plan assumed "~41 duplicate anon placeholders" to merge on a name+company content key. Rehearsing on the pulled prod DB revealed **124 of 133 email-less rows are distinct TA Cook PII-withheld opt-outs** (org-only headcount, e.g. 8 distinct Zanders attendees) and only **1** was a true duplicate. A bare content key would have collapsed ~68 distinct records.
- **Rationale:** B4/B3 — verify the target before an irreversible write. Shipped P1a: named rows key on content (safe dedup), nameless org-only rows keep the ordinal (stay distinct). Surfaced to owner; a future "one aggregate row per company" model is the clean fix if opt-out headcount ever matters.

### Migration framework (P0)
- **Choice:** `user_version`-gated one-shot runner, not per-connect DDL.
- **Rationale:** per-request autocommitted `DROP VIEW` would race the threadpool at cold boot; BEGIN IMMEDIATE + busy_timeout serialise the first-boot migration.

### Sheet status = display-only; next_step stays app-owned (owner decisions, pre-set)
- Honored: no stage mapping from the sheet status; sync preserves app-owned next_step and emits a "sheet differs" warning.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../lead-desk/src/lead_desk/web/store.py` | Modified | migration runner, `_VIEWS`, `merge_contacts`, `enroll_campaign_contacts`, `outreach_status`+`merged_into` cols |
| `.../web/service.py` | Modified | build_board UNION, derivation fixes, StaleWriteError, merge candidates, freshness/kill_switch |
| `.../web/app.py` | Modified | mark-replied/merge routes, CSRF + security-headers middleware, login throttle, sync banners |
| `.../web/auth.py` | Modified | token iat+expiry, CSRF helpers, login throttle |
| `.../web/uploads.py`, `.../migrate.py`, `.../sync.py`, `.../ground.py`, `.../identity.py`, `.../capture.py` | Modified | per-phase fixes |
| `.../web/templates/*.html` | Modified | board/contact/campaign/campaigns/base/login |
| `.../maintenance.py` | Created | `lead-desk-maint` (clean-orphan-state, rekey-anon) |
| `.../tests/*` + `conftest.py` | Created/Modified | 212 tests (+ clock pin) |
| `~/.claude/.../memory/project_brisken_lead_desk.md` | Modified | build summary + corrected sync note |
| `workspace/hours-tracker/hours-tracker-2026-07-july.xlsx` | Modified | +8.5h lead-gen |

---

## Current Status
All phases live on `brisken-lead-desk.fly.dev` (latest image post-P8). `user_version=4`.
No-send hold intact and verified. 337 contacts, all enrolled. Graph sheet-sync
LIVE (POST /sync → 337 contacts, 16 sheet-diffs). Existing sessions will hit a
one-time forced re-login (new token format).

---

## Next Steps
1. **Build 4d** — Graph app-only sender + cloud capture, retire the Outlook-COM worker. Its trigger condition (audit-fix build merged+deployed) is now met. Anchored in `[[project_lead_desk_4d_graph_send]]`. Needs its own watched send-gate drill before arming. Do NOT let this drop.
2. Optional: adjust hours rows 42/43 if actual operator engaged time differed (build was largely autonomous).
3. Optional future: aggregate-per-company model for the org-only TA Cook opt-outs (removes the residual reorder-dup cosmetic).

---

## Context for Next Session
### Files to Read First
- `~/.claude/.../memory/project_brisken_lead_desk.md` (the 2026-07-16 entry)
- `~/.claude/.../memory/project_lead_desk_4d_graph_send.md` (the next build)
- `workspace/clients/brisken/automations/lead-desk/src/lead_desk/capture.py` (P8 readied it; 4d wires the sender)

### Open Questions
- 4d credential decision: reuse `BRISKEN_GRAPH_*` (already Fly secrets) vs a dedicated least-privilege app (PHASE2-IT-REQUEST.md). Deferred to the 4d build.

### Working Notes
- Deploy: `flyctl deploy <pkg> --config <toml> -a brisken-lead-desk --depot=false`. Machine scales to zero — `flyctl machine start 2869e67c347558` before ssh/sftp; `flyctl ssh console` trails a harmless "handle is invalid".
- Live auth: `POST /login code=$CODE_MATTHIAS` from `.scratch/ld_secrets.env`; `/sync` now in OPEN_PATHS.
- Test: `uv run --directory <pkg> --extra web --extra dev --extra capture --extra worker pytest -q` (212; conftest pins `cadence.now_utc` to 2026-07-15 09:00 UTC — the fix for the time-bomb).
- No-send verify: `.scratch/nosend_check.py <db>` on a pulled copy (kill_switch/status/send_attempts/sequences/user_version).

### Reference Materials
- Plan: `~/.claude/plans/plan-how-to-integrate-cozy-clover.md`
- Findings: `.scratch/final_findings.json` (54 entries)
- PRs #229–#238 on `011matthias/agentic-ops1.01`

---

## How to Continue
The audit-fix build is done and live. The next unit of work is the **4d build**
(separate, owner-committed). Resume brisken, read the two memory files above,
and start 4d: Graph sender mirroring `sync.py`'s app-only pattern with the hard
dirk+matthias mailbox allowlist, cold auto-send from matthias.silva@ via
Mail.Send, warm drafts in Dirk's mailbox via Mail.ReadWrite, wire `capture.py`
(P8-readied) for reply/bounce polling, then retire the COM worker. Re-run the
full watched send-gate drill before ANY real send.

---

## Strategic Feedback

### What Worked Well This Session
- The phased plan with explicit prod-op authorizations + a hard no-send invariant let the whole build run autonomously with a single "continue".
- Rehearsing every prod DB op on a pulled copy first is what caught the anon-merge data-loss (the plan's assumption was wrong); the rehearsal step paid for itself.

### Suggestions
- The hours model for largely-autonomous agent builds is ambiguous (billable operator time vs agent runtime). A convention for how to log agent-autonomous work would remove the guesswork each time.

### System Health
- The test suite carried a latent verification-theater time-bomb (`approved_at` used the real clock vs a fixed claim window); "181 passed" was fragile and would have gone red on any run after 2026-07-15 with no code change. Fixed structurally (injectable clock + conftest pin). Worth a lint/convention: engine tests that assert on fixed datetimes must pin the clock.
- Autonomy score: 0 correcting interventions — fully autonomous session (the only user inputs were "continue" and "/compact").
