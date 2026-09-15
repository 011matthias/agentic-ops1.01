# Checkpoint: Brisken P1 Failure Probe And Cleanup Round

**Date:** 2026-09-15
**Status:** Item 50's probe built, merged, deployed and driven live. Lint cleanup and two p2 status corrections merged. Four PRs, all green.

---

## Summary

The autonomous half of the previous checkpoint's next steps, done: the probe that makes the next "Failed to fetch" provable is live on the expense-recon app, the module's twelve lint findings are cleared, two p2 status files that asserted things the repo contradicts are corrected, and the one undated live row is identified as a correctly-flagged review exception rather than a defect.

---

## What Was Done This Session

### Item 50, the client-failure probe (PR #855, merged, deployed)
1. `web/machine.py`: one home for the process's identity and age, read by `/healthz` and by every report, so the two cannot disagree about which machine answered. Uptime is monotonic, so a clock correction cannot age a process.
2. `/healthz` keeps `status` untouched and gains a parallel `server` block; empty off Fly rather than invented.
3. `POST /api/client-errors` records one client-side failure, `GET` reads them back, both behind the ordinary session gate. Bounded to 500 rows with a 20-per-caller-per-minute burst cap.
4. `process_predates_failure` is the decisive field: a process younger than the failure did not exist when the request was made, which proves a machine replacement.
5. Twelve tests through the routes; six wiring points regress-checked green to red to green.
6. `docs/lovable-failure-probe-prompt.md` written and registered as not applied.

### The undated row (read-only diagnosis)
1. The single row behind `n_undated: 1` is a French bank receipt in Criss's live July month whose extraction read neither date nor amount.
2. It already reads `check` / `missing_fields` with "Missing date", so the new count and the existing review state agree. That agreement doubles as a validity check on the new field.

### Lint cleanup (PR #856, merged)
1. Twelve findings cleared, none of them runtime faults. Eight dead imports auto-fixed; three quoted annotations naming types the module never imported, fixed with TYPE_CHECKING imports; one dead local in a test, read and removed by hand.
2. CI's ruff has never covered this module, which is why they accumulated.

### p2 status corrections (PR #857, merged)
1. `p2-rome` said the GA wave was still to prepare; it was sent 2026-07-27, nineteen by id, verified into Sent Items. It also still listed the Lead Desk fix as awaiting a deploy order; the Lead Desk is live.
2. `p2-lead-gen-general` said there had been no Dirk contact yet; he has been sending since July and was mailed the review packet on 2026-09-08.

---

## Key Decisions Made

### The probe is client-side by necessity, not by preference
- **Choice:** the browser reports the failure; the server stamps what it was when the report arrived.
- **Rationale:** a rejected fetch never reaches the app, so no server-side log can ever contain it. Any amount of extra server logging would have been theatre.

### The elapsed time comes from the browser, never from comparing clocks
- **Choice:** `seconds_ago` drives the comparison; `occurred_at` is only for a human reading the row.
- **Rationale:** a browser clock skewed by minutes would fabricate or hide a restart.

### Unknown stays null and never collapses to false
- **Choice:** no failure time means no verdict.
- **Rationale:** a fabricated "the machine restarted" would send the next investigation back to the hosting theory that already cost this item a cycle.

### CI's ruff scope was deliberately not extended
- **Choice:** fix the twelve, leave the gate alone.
- **Rationale:** nine branches of the parallel round are in flight; a stricter gate now fails other people's PRs for findings they did not introduce. It is the durable half and belongs after the round closes.

### Two p2 files corrected, not four refreshed
- **Choice:** correct only what the repo provably contradicts, and say in each file what this pass did and did not re-verify.
- **Rationale:** bumping the date while silently carrying July rows forward would launder them as current and delete the reader's only signal of which rows to trust. The other two contain nothing provably wrong, and inventing their state from a p1 session would be worse than the staleness.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../web/machine.py` | new | process identity and age, one home |
| `.../web/app.py` | edit | healthz server block; the two probe routes |
| `.../web/store.py` | edit | `client_errors` table and accessors |
| `.../tests/test_client_error_probe.py` | new | 12 tests through the routes |
| `.../docs/api-contract.md` | edit | the probe section |
| `.../docs/lovable-failure-probe-prompt.md` | new | the SPA half, not applied |
| `.../docs/PROMPT-STATUS.md` | edit | not-applied row |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 50 probe recorded |
| 11 module files | edit | lint cleanup, no behaviour change |
| `workspace/clients/brisken/status/p2-rome.md` | edit | GA wave and Lead Desk corrected |
| `workspace/clients/brisken/status/p2-lead-gen-general.md` | edit | go-live framing corrected |

---

## Current Status

Four PRs merged (#855, #856, #857, plus #834 and the docs checkpoint earlier in the day). The expense-recon app is deployed and the probe is driven live in all three directions. The registry for cost centers is still empty in production, so those fields stay inert. Ops status from pre-flight: platform unknown plan, no comms-log on file. Project status: p1 files current; p2-targeting (55d) and p2-product-decks (54d) remain stale and were deliberately left.

---

## Next Steps

1. Owner-side: paste `lovable-cost-centers-prompt.md` sections 1 and 2 first, publish, prove the settings bundle round-trips both maps, then the rest.
2. Owner-side: paste `lovable-failure-probe-prompt.md`. Until then the browser reports nothing and the probe records nothing, so **item 50 stays open**.
3. Owner-side: define the cost centers; the review flag starts firing only then.
4. July receipts: 19 PDFs in the primary clone's `.scratch/recon-july/criss-receipts/` await the app's OCR; the ingest writes into Criss's live July month and needs a per-action go plus the route choice.
5. Refresh or retire `p2-targeting` and `p2-product-decks` from a p2-scoped session with live access.
6. After the parallel round closes, extend CI's ruff scope to the module.
7. Harden `deploy-consumer-gate.py`: it closes its marker when a browser command is observed, not when an assertion is made.
8. The undated July row needs a date; it is a write to live records and is the owner's call.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md`, items 47 to 54
- `.../expense-reconciliation/docs/api-contract.md`, the cost-centers and probe sections
- `.../docs/lovable-cost-centers-prompt.md` and `.../docs/lovable-failure-probe-prompt.md`

### Open Questions
- Which route for the July ingest, direct or mail forward.
- Whether the cross-month cost-center screen should show the all-unassigned table while no centre exists.

### Working Notes
- `tools/regress_check.py` spawns the test outside Git Bash: `--test` and `--file` need `C:/` paths. Same inside any `python -c`.
- `agent-browser wait --load networkidle` never returns on the live SPA. Open, sleep, snapshot. Use a named `--session`; Playwright MCP here is CDP to the user's Edge and was not listening.
- The live API answers 401 before routing, so an unauthenticated status probe cannot tell a present route from an absent one. Log in via `POST /api/login` with the operator code from the local vault.
- Three drill rows labelled `probe-drill` sit in the live `client_errors` table from the deploy verification. They are evidence the probe works and will age out of the 500-row cap.
- A first draft of the probe test asserted a millisecond-old test process had been "running half a second ago". It went red correctly; the fix was to move the process clock, not to weaken the assertion.
- GitHub's `mergeable` field is computed asynchronously: reading it right after a push returns the pre-push verdict.

### Reference Materials
- PRs: #855 (probe), #856 (lint), #857 (p2 status)
- Live API `brisken-expense-recon.fly.dev`; SPA `expenses.brisken.com`

---

## How to Continue

Everything autonomous in the previous checkpoint's list is done and nothing is half-wired. What remains is owner-gated or belongs to a p2 session. Start from the p1 status row and the backlog's items 48 to 54.

---

## Strategic Feedback

### What Worked Well This Session
- Asking the instrument-validity question before designing the probe changed the design: the fact that no server log can ever see a rejected fetch is what made it a client-side beacon instead of more logging.
- Driving the deployed probe in both directions, not just once, is what proves it discriminates. A probe that answered the same for "restarted" and "did not" would have passed a single-case check.

### Suggestions
- `deploy-consumer-gate.py` closes its marker on observing a browser command, before any assertion exists. It printed "consumer driven" while my drive was still a backgrounded command that had asserted nothing. A gate that can be closed by a command proving nothing protects less than it appears to.

### System Health
- Autonomy: 0 human interventions, fully autonomous session.
- The parallel round means a Fly release number no longer identifies a tree, and main moves under every branch; two PRs needed a merge of main mid-flight.
