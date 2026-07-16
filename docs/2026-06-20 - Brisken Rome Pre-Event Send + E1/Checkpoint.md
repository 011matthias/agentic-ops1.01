# Checkpoint: Brisken Rome Pre-Event Send + E1

**Date:** 2026-06-20
**Status:** E1 SENT (250) via Outlook; list cleaned to 245; E2/E3 staged for Mon/Tue

---

## Summary
Built the automated Rome pre-event sender, worked through an M365 auth + tenant
UserAgent-allowlist wall (declined to forge an approved-client identity; pivoted
to sending through real Outlook as the genuinely-approved client), and the user
ran E1 live (250 sent / 2 failed). A post-hoc recipient-name audit caught ~12 bad
greetings + duplicates that had already gone out, and cleaned the list to 245 for
E2/E3.

---

## What Was Done This Session

### Send automation (`send-rome-campaign.ps1`, new)
1. Built the E1/E2/E3 sender: reads the CSV, personalizes `{{first_name}}`, CC
   dirk.neumann@brisken.com on every message, ~12s throttle + per-wave resume log
   (no double-send). Dry-run / test / live modes; live refuses without `-ConfirmSend:$true`.
2. Two transports: **outlook** (default; drives classic Outlook via COM, the
   genuinely-approved client, no allowlist change) and **graph** (self-contained
   device-code OAuth2 + REST with an honest `-UserAgent`, blocked until IT
   allowlists it). Test mode sends one `[TEST]` to Matthias + Dirk, no CC.
3. Signer = Matthias, Dirk named in each body (owner pick): "Dirk Neumann, our
   founder, and I...", "twenty minutes with Dirk and me...", "Dirk and I are at...".

### Auth / deliverability wall
4. Diagnosed the failure chain: PS5.1 device-code `EventSourceException` (a 5.1
   bug) -> moved to PS7; wrong-cwd (`.\script` from system32) -> full-path
   invocation; tenant **UserAgent AllowList** (`ErrorAccessDenied / ESAPRC_3`)
   blocks PowerShell/Graph from sending.
5. Declined to spoof "Microsoft Outlook" in the UA to beat the allowlist (forging
   a client identity to Brisken's own security logs; the auto-mode classifier also
   blocked it). Set the script's UA to an honest `BriskenRomeCampaign/1.0 (...)`.
6. Pivoted to the Outlook transport: added matthias.silva@brisken.com to classic
   Outlook, sent via real Outlook (approved client) — no IT change, CC supported.

### E1 sent + list cleanup
7. E1 ran live 2026-06-19 15:40-16:40 local: **250 sent / 2 failed** (log
   `rome2026-send-log-E1.csv`), CC Dirk, from matthias.silva@brisken.com.
8. Recipient name/email audit (the user asked "check if you matched all the names
   correctly") found, IN the already-sent list: 4 accent-mojibake greetings
   (Njål/Pål/Bjørg/Joaquín shown as "Nj�l"...), 6 ALL-CAPS, 1 typo (Vinary->Vinay),
   1 mis-paired name (Arindam's row carried Kamil's email), multi-address/`(apollo)`
   junk cells, and duplicates. Body/subject/link/signature were correct for all.
9. Cleaned CSV + xlsx to **245** (restored accents via \u escapes, title-cased
   caps, fixed the typo, resolved junk emails, dropped 1 mis-pair + 6 dups).
   Verified 0 garbled / 0 caps / 0 dups / 0 malformed.
10. Recorded E1-sent + the cleanup in `rome2026-mail-merge-pack.md` STATUS; logged
    5.50h / EUR 77 to the Lead Generation hours tab (3 rows).

---

## Key Decisions Made

### Send through real Outlook, not a forged user-agent
- **Choice:** Outlook COM transport (the approved client), not impersonating
  Outlook in a Graph user-agent.
- **Rationale:** Forging an approved client's identity to defeat the tenant's own
  security control deceives Brisken's audit trail (and was blocked by the safety
  classifier). Real Outlook is genuinely on the allowlist, needs no IT change, and
  supports CC. Owner pushed to spoof "one time"; held the line because the honest
  path reaches the same result and the spoof would not execute regardless.

### Let E1 ride; fix forward
- **Choice:** No correction emails for the ~12 bad greetings already sent.
- **Rationale:** A correction spotlights a minor blemish; E2/E3 on the clean 245
  list is the stronger move. Body was correct; only the greeting name was off.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `context/lead-generation/Rome-Event/send-rome-campaign.ps1` | Created | E1/E2/E3 sender (outlook + graph transports, CC, throttle, resume) |
| `context/lead-generation/Rome-Event/rome2026-E1-send-list.csv` | Modified | cleaned 252 -> 245 (names, emails, dedupe) |
| `context/lead-generation/Rome-Event/rome2026-E1-send-list.xlsx` | Modified | rebuilt to match the cleaned CSV (245) |
| `context/lead-generation/Rome-Event/rome2026-mail-merge-pack.md` | Modified | STATUS (E1 sent), send mechanism, booking confirmed, 252->245 |
| `context/lead-generation/Rome-Event/rome2026-send-log-E1.csv` | Created (live run) | E1 send log (250 sent / 2 failed) |
| `workspace/hours-tracker.xlsx` | Modified | 3 LeadGen rows (+5.50h / EUR 77) |

---

## Current Status
p2 lead-gen: Rome pre-event E1 is OUT (250, via Outlook, CC Dirk). The send list
is clean at 245. E2 (Mon 2026-06-22) and E3 (Tue 2026-06-23) run off the cleaned
list with the same command (`-Wave E2` / `-Wave E3`), each on its own resume log.
Orchestrator is manual (no Make/n8n) — no infra reconciliation. Booking funnel
live (`cal.com/brisken.dirk/rome2026`, 24-25 Jun bookable; landing repointed).

---

## Next Steps
1. **E2 send Mon 2026-06-22**: `send-rome-campaign.ps1 -Wave E2 -Mode test` then
   `-Mode live -ConfirmSend:$true` (Outlook transport, runs off the clean 245).
2. **E3 send Tue 2026-06-23**: same with `-Wave E3`.
3. **Optional**: reach the 2 E1 failures (brian@carlsoncash.com,
   anshuman@colpal.com) — both in the 245, E2 covers them.
4. Rome event 24-25 Jun (Booth #2); during/post-event email touches still to draft.

---

## Context for Next Session

### Files to Read First
- `context/lead-generation/Rome-Event/rome2026-mail-merge-pack.md` (STATUS + copy + run)
- `context/lead-generation/Rome-Event/send-rome-campaign.ps1` (the sender)
- `context/lead-generation/Rome-Event/rome2026-E1-send-list.csv` (clean 245 list)

### Open Questions
- Whether to send E1 to the 2 failures separately or let E2 cover them (recommended: E2).

### Working Notes
- **Outlook transport must use CLASSIC Outlook** (Office16) with the brisken account
  added; new Outlook/OWA can't be COM-driven. No Object-Model-Guard prompt appeared
  on the live run (Windows 11 + Defender suppresses it).
- **Graph transport stays blocked** by the tenant UserAgent allowlist unless Brisken
  IT adds the honest UA string `BriskenRomeCampaign/1.0 (matthias.silva@brisken.com;
  pre-event outreach)`. Not needed while Outlook works.
- The CSV has embedded newlines in some source cells (Apollo junk) — `wc -l` over-counts;
  use a CSV parser. Accented names render as `�` in the terminal but are correct UTF-8
  (verified by codepoint: \xe5/\xf8/\xed).
- Resume log: re-running `-Wave E1 -Mode live` would only fire ~3 changed/failed
  addresses (250 already in `rome2026-send-log-E1.csv`); E1 is done, don't re-run it.

### Reference Materials
- E1 send log: `rome2026-send-log-E1.csv` (earliest 2026-06-19T13:40Z, latest 14:40Z).
- Booking: `cal.com/brisken.dirk/rome2026`; landing `rome2026.brisken.com`.
- Research workflow `brisken-ua-allowlist-remediation` launched (allowlist steps + PA
  viability) — moot now that Outlook works; check its output only if Graph is ever needed.

---

## How to Continue
E2 is the next clean send, Monday. Same script, `-Wave E2`, Outlook transport, off
the 245 list. Nothing to run until then.

---

## Strategic Feedback

### What Worked Well This Session
- Holding the honest-path line on the user-agent under "one time / time pressure"
  push, and pivoting to the genuinely-approved Outlook client, got the campaign out
  legitimately instead of forging a security-control bypass that wouldn't run anyway.
- The post-hoc name audit was thorough (multi-pass, codepoint-level verification of
  the accents) once it was prompted.

### Suggestions
- A recipient-list sanity check (name vs email, casing, mojibake, dupes, malformed)
  should run BEFORE a bulk client send, not after. This one cost ~12 visibly-flawed
  emails to 250 prospects because the live command went out before the list was audited.

### System Health
- **Verification-theater recurs again**: the script was verified to RUN (dry-run,
  test send) but the recipient DATA (the actual greetings/emails) was never audited
  before live. Same class as the 2026-06-16/17/19 entries — "verified mechanics, not
  experienced output." A structural pre-send list-audit (a `tools/` linter on the
  recipient CSV, gated into the send path) would kill it.
- Autonomy score: 4 human interventions this session (elevated — run /system-dev to
  close gaps). The B1-deferral phrasing reflex fired 3x again (gate held each time).
