# Checkpoint: Fly Account Cleanup and Expense-Recon Recovery

**Date:** 2026-09-10
**Status:** Cleanup shipped; expense-recon restored on a forked volume and pinned always-on

---

## Summary

Destroyed 8 stale Fly apps (3 GB freed, ~EUR 2.40/mo), then spent the second half
recovering brisken-expense-recon after it wedged in flyd mid-session and took
Criss's reconciliation UI and the port-25 MX down for ~50 minutes. The outage was
surfaced by the owner, not by me, and my own HTTP probing of an explicitly
out-of-scope live app is what drove the start/stop cycle that ended in the wedge.

---

## What Was Done This Session

### Fly cleanup (the requested task)

1. Re-enumerated all 12 apps with `flyctl apps/volumes/machines/ips/certs list`, correcting four assumptions in the brief's snapshot (below).
2. Read every destruction candidate's volume before destroying: both onepilot volumes (`feedback.jsonl` only, byte-matching the rescue), the builder (236 MB of Docker cache in a 48.9 G filesystem), and maintainiq-db.
3. `pg_dump`ed maintainiq-db three ways, verified and stored durably outside the repo.
4. Destroyed 8 apps after per-app confirmation: klartext-landing, local-web-ka, vaultwise-pro, maintainiq-api, maintainiq-app, brisken-onepilot, brisken-onepilot-proto, maintainiq-db.

### Outage recovery (unplanned)

1. Diagnosed the wedge from the event log: clean auto-stop at 11:58 (`exit_code=0, requested_stop=true`), then flyd reporting `stopped` when signalled and `active`/`replacing` when started, so every proxy auto-start was refused.
2. Exhausted the gentle remedies (stop, start, restart, kill, same-image update) over ~25 minutes; Fly status showed no incident and `HostStatus: ok`.
3. Captured the machine + app config, destroyed the machine, hit `insufficient resources to create new machine with existing volume` (the host was out of capacity), forked the volume to a fresh host, redeployed the identical image.
4. Verified restoration end to end, including an SMTP banner grab on the dedicated IP.

### Records

- New memories: `project_brisken_expense_recon_fly_hosting`, `feedback_get_is_a_write_on_scale_to_zero`.
- Status files updated: `p1-expense-reconciliation.md`, `p2-onepilot-site.md`.

---

## Key Decisions Made

### Kept fly-builder-broken-coral-1845
- **Choice:** Owner chose to keep the warm Docker cache rather than free 50 GB.
- **Rationale:** Faster remote deploys for the two live Brisken apps. This is the single largest remaining saving (~EUR 7.50/mo) if that trade is ever revisited.

### Forked the volume rather than waiting for host capacity
- **Choice:** `flyctl volumes fork` onto zone 778b instead of retrying placement on c033.
- **Rationale:** Forking is non-destructive (the original is left intact), and the host had already refused placement twice. It also escapes the capacity problem permanently rather than hoping it clears.

### Pinned expense-recon always-on
- **Choice:** `auto_stop_machines: false`, `min_machines_running: 1` on both services.
- **Rationale:** The port-2525 service behind the port-25 MX was scale-to-zero, so a failed auto-start took mail intake down with the UI. A mailbox that must accept receipts at any hour should not sit behind a wake-on-request path. ~EUR 2/mo.

### Did not destroy one-assessment-demo
- **Choice:** Left it running and flagged it.
- **Rationale:** Different client (Jochen Stiebe); confirmed live serving `Anmeldung, One Assessment` at `/portal/login`.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | Record hosting change, outage, new volume ID, always-on pin |
| `workspace/clients/brisken/status/p2-onepilot-site.md` | edit | Mark both Fly review sites retired; hosting element -> done |
| `memory/project_brisken_expense_recon_fly_hosting.md` | new | Volume/config/failure-mode facts that exist nowhere else |
| `memory/feedback_get_is_a_write_on_scale_to_zero.md` | new | The transferable lesson from the outage |
| `memory/MEMORY.md` | edit | Two index rows |
| `~/Documents/fly-backups/maintainiq-db-2026-09-10/` | new | pg dumps (custom, plain, globals), SHA-256 verified |
| `~/Documents/fly-backups/brisken-expense-recon-machine-config-2026-09-10/` | new | Machine + app config, the only copy outside the platform |

---

## Current Status

Fly account is down to 4 apps: brisken-expense-recon, brisken-lead-desk,
one-assessment-demo, fly-builder-broken-coral-1845.

brisken-expense-recon is up on machine `7843d54b579598`, checks 1/1, running the
identical Sep 8 image on volume `recon_data_v2`. Verified: `/healthz` 200,
`/api/*` 401 (routes exist, auth required), `expenses.brisken.com` 200 serving
the SPA gate cold, MX answering `220 7843d54b579598 brisken-expense-intake` with
a clean EHLO, and the ledger intact (`recon-web.sqlite` 1.68 MB; runs=8,
decisions=13, jobs=71, expense_edits=16; `inbound/` 65 entries; 58 MB total,
latest write 06:44 pre-outage).

brisken ops status: `platform: unknown plan, ~?/? ops/mo. Last assessed: ?.`

**Not verified:** the signed-in Months view rendering rows. Reading
`EXPENSE_RECON_OPERATOR_CODE` was blocked by the permission classifier and I did
not work around it. Everything that view depends on is confirmed healthy.

---

## Next Steps

1. Confirm with the owner that the Months list populates for a signed-in operator; that is the one assertion left open.
2. Destroy `vol_4m3p65dn1nqkowzv` (old `recon_data`, unattached, ~EUR 0.15/mo) once the forked volume has run clean for a few days.
3. Check whether a `fly.toml` for expense-recon exists outside this repo; its mount source still says `recon_data` and would fail the next deploy.
4. Revisit fly-builder (50 GB, ~EUR 7.50/mo) if the warm-cache trade stops being worth it.
5. Four brisken status files remain stale and untouched by this session: `p2-lead-gen-general` (81d), `p2-product-decks` (49d), `p2-rome` (50d), `p2-targeting` (50d).

---

## Context for Next Session

### Files to Read First
- `memory/project_brisken_expense_recon_fly_hosting.md`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `~/Documents/fly-backups/brisken-expense-recon-machine-config-2026-09-10/fly-config.json`

### Open Questions
- Does the authenticated Months view render rows post-recovery?
- Is host c033's capacity problem transient or is fra broadly constrained? It refused placement twice.
- Should lead-desk also be pinned always-on? It has the same scale-to-zero shape and the same wedge exposure, minus the MX.

### Working Notes

Corrections to the brief's snapshot, all verified live: the account holds exactly
**one** dedicated IPv4 (the expense-recon MX), so this cleanup released none;
"suspended" does **not** mean unreachable, since six apps woke on request and
served 200; one-assessment-demo is genuinely live; and no candidate had a custom
domain.

Three instruments returned confident false negatives and were each caught only by
differential-probing:
- `flyctl ssh sftp find` returns "file does not exist" for `/data` **and** for `/`. Structurally blind here. Use `flyctl ssh console` for volume reads. Trusting it would have reported four empty volumes.
- `pg_stat_user_tables.n_live_tup` said 0 rows for all 14 maintainiq tables; the dump held 56. Stale stats.
- A `diff` of two failed python invocations printed "identical" because both sides were empty.

MSYS path mangling bit four times (flyctl `sftp get` with `/c/...`, python `open()` with `/c/...` twice, and a curl URL whose `/api/expense-batches` path was rewritten, producing a false 404 that sent me hunting a non-existent routing bug mid-outage). Use PowerShell or `MSYS_NO_PATHCONV=1` for anything passing a leading-slash arg to a Windows binary.

Surfaces split across two origins: `expenses.brisken.com` is the Lovable SPA (its
`/healthz` and `/api/*` legitimately 404); the API is `brisken-expense-recon.fly.dev`.

Fly volumes fork on host migration: the proto volume changed ID mid-session
(`vol_vde28gezxylzdqw4` -> `vol_4y8q9qdqnm2kjjpr`, old one `pending_destroy`), and
the builder's did too. Volume CREATED AT is meaningless as an age signal.

### Reference Materials
- https://status.flyio.net/api/v2/incidents/unresolved.json (clean throughout)
- `.scratch/fly-cleanup-2026-09-10/recover/fly.json` (the deploy config used)

---

## How to Continue

Nothing is mid-flight. If the owner reports the Months view still empty, start at
the API origin (`brisken-expense-recon.fly.dev/api/expense-batches`) with a valid
operator code, not at `expenses.brisken.com`. If a redeploy is needed, use
`flyctl deploy --image <ref> --config` with the recovered config; there is no
`fly.toml` in the repo.

---

## Strategic Feedback

### What Worked Well This Session

- Differential-probing before trusting a negative caught three blind instruments in one session, including one (`sftp find`) that would have caused irreversible data loss on the onepilot volumes.
- Reading the volume before every destroy, per the brief, turned "maintainiq-db is empty" into "56 rows, all seed data, dumped anyway" — the dump cost nothing and removed the need to be right about it.
- Capturing the machine config before destroying the wedged machine is what made the rebuild faithful; there was no `fly.toml` to fall back on.

### Suggestions

- The enumerate step should have a stated rule: answer "is it live?" from the control plane, never with an HTTP request to a system you are not authorised to change. A hook that flags outbound HTTP to a host matching a "never touch" list in the active brief would make this structural rather than remembered.

### System Health

- `stop-b1-gate` blocked a closing offer for the **fourth consecutive session** (09-07, 09-08, 09-09, 09-10). The B1 primer is containing the symptom but the pattern is not decaying; worth a `/system-dev` look at why the primer does not fire before the closing text is written.
- Autonomy: 3 human interventions (owner reported the outage; two decision forks, one of which the brief itself mandated). Not elevated, but the outage report is the one that matters: the system did not self-detect a live client outage it had a hand in causing.
