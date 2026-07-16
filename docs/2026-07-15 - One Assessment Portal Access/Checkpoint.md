# Checkpoint: One Assessment Portal Access

**Date:** 2026-07-15
**Status:** Complete + verified live (survives machine restart)

---

## Summary
Jochen couldn't log into the One Assessment portal; diagnosed it as a name/code pair-mismatch (his code is fine, he was typing "Jochen Stiebe" while the code is bound to "Jochen"). Created a portal login for Jannik Ellminger, and made both "Jochen" and "Jochen Stiebe" work with the same existing code via a registry alias.

---

## What Was Done This Session
### Diagnosis (read-only)
1. Read `site-host/auth.py` + `portal.py`: login is a **pair-match** on (normalized name, SHA-256 of code). Code is non-transferable between names.
2. Queried the live registry (`GET /api/op/access-codes`): a code exists bound to login_name `Jochen` (created 09:52 UTC = 11:52 CEST, matching the 11:55 WhatsApp).
3. Live login test proved it: `Jochen` + code → OK; `Jochen Stiebe` + code → 401. Root cause = the 11:46 WhatsApp told him to type "Jochen Stiebe", which doesn't match.

### State changes (live)
4. Created access code for **Jannik Ellminger** via `cli code` (registry write, no email). Verified login OK. Owner chose to keep it a **separate** login (own area; sees shared demo + own submissions only).
5. Added a **"Jochen Stiebe" alias** record carrying the **same code hash** as the "Jochen" record, so both names log in with the one code Jochen already has. The operator API only mints fresh random codes (can't reuse a hash), so this required a direct write to `users.json` on the Fly volume via `fly ssh` (owner-approved after the auto-mode classifier paused it).
6. Forced a full machine restart and re-tested: all logins work after cold-start from the volume. Proven persistent; no deploy needed.

---

## Key Decisions Made
### Root cause is the name, not the code
- **Choice:** Fix the name-matching, leave the code untouched.
- **Rationale:** Live test showed the code validates under `Jochen`. The existing WhatsApp code stays valid; no re-issue.

### Same code for both names (not two codes)
- **Choice:** Registry alias sharing one SHA-256 hash, via a direct volume write.
- **Rationale:** Owner asked for both names to work. A second API-minted code would bind "Jochen Stiebe" to a *different* code, reintroducing the mixing failure. One code + two name records removes the failure mode entirely.

### Jannik: separate login
- **Choice:** Own credential, not shared with Jochen (owner picked "keep separate").
- **Rationale:** Fits reviewing the shared demo/product with per-person feedback attribution. Trade-off surfaced: Jannik can't see Jochen's specific submission under a separate login.

---

## Files Modified
| Target | Action | Purpose |
|--------|--------|---------|
| `/data/intake/users.json` on `one-assessment-demo` (Fly volume) | Added record | `Jannik Ellminger` access code |
| `/data/intake/users.json` on `one-assessment-demo` (Fly volume) | Added record | `Jochen Stiebe` alias, same hash as `Jochen` |

No repo code changed — this was operational (access-code) work.

---

## Current Status
Live registry: `UTIL Verifier`, `Matthias Silva`, `Jochen`, `Jannik Ellminger`, `Jochen Stiebe` (last two share the `789f32a0d587…` hash → same code). All logins verified OK after a full machine restart.

Portal: `one-assessment-demo.fly.dev` (Fly, fra, scale-to-zero, persistent `one_assessment_data` volume). Access codes are stored as SHA-256, so they survive auth-secret rotation and deploys.

---

## Next Steps
1. None required for this task — it works and is proven persistent.
2. (Carryover from portal-segmentation session) Add `Cache-Control: no-store` to portal/intake HTML responses.
3. (Optional infra) Give the operator API a way to add a name **alias** to an existing code, so "make both names work" no longer needs a manual volume write.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/Jochen Projekt/automations/treasury-assessment/site-host/auth.py` (`match_code`, `hash_code` — the pair-match rule)
- `workspace/clients/Jochen Projekt/automations/treasury-assessment/site-host/operator_api.py` (access-code endpoints; note: fresh codes only, no hash injection)
- `workspace/clients/Jochen Projekt/automations/treasury-assessment/src/treasury_assessment/cli.py` (`cmd_code`)

### Working Notes
- Operator creds: `workspace/clients/Jochen Projekt/context/.env` (`ONE_ASSESSMENT_BASE_URL`, `ONE_ASSESSMENT_OPERATOR_TOKEN`). CLI loads it automatically.
- To alias a name onto an existing code, you must write `users.json` directly (API can't reuse a hash). Inside the container: `import store, auth; store.add_code(name, client, auth.hash_code(plaintext_code))`. Wake the machine first (`curl /healthz`), then `fly ssh console -a one-assessment-demo -C ...` (base64-wrap the python to dodge quoting).
- Jochen's plaintext code is known from the WhatsApp (`J6q1WfqP5rsyCsNyfXbgU6iu`); Jannik's is `x_M2gp7KkpIxVZqMiy4kvH1e`.
- `fly ssh` on Windows prints a harmless `Error: The handle is invalid` at teardown (exit 1) after the command already ran — check the stdout above it, not the exit code.

### Open Questions
- Want an operator affordance for name-aliases so this is a one-command op next time, or is the manual volume write acceptable (rare)?

### Reference Materials
- Portal: https://one-assessment-demo.fly.dev/portal/login
- Prior context: `docs/2026-07-15 - One Assessment Portal Segmentation/Checkpoint.md`

---

## How to Continue
Nothing outstanding for access. If a new reviewer needs in: `cli code --name "<Name>" --client "Jochen Projekt"` and relay the printed code. If someone needs two name spellings on one code, use the alias procedure in Working Notes.

---

## Strategic Feedback

### What Worked Well This Session
- Diagnosing against live behavior (an actual login POST) rather than reasoning about the code in the abstract pinned the root cause in one test and avoided touching the working code.

### Suggestions
- The name/code pair-match is exact-match brittle by design (keeps codes non-transferable). For a small trusted set of reviewers, a per-code list of accepted name spellings would remove the whole class of "which name do I type" confusion without weakening the code entropy.

### System Health
- The operator API can create and list codes but not alias or edit them, so a legitimate owner request ("both names") fell through to a manual Fly-volume write gated by the auto-mode classifier. A thin `POST /api/op/access-codes/{hash}/alias` (or an `aliases: []` field on a record) would keep this on the sanctioned API path.
- Autonomy score: 1 human intervention this session (one B1 closing-deferral, hook-caught, resolved via AskUserQuestion — same recurring class the register tracks; the two other AskUserQuestions were genuine owner decision points, not friction).
