# Checkpoint: Meji September Prep + Copy Approval

**Date:** 2026-07-29
**Status:** September prep delivered; corporate copy APPROVED by Gurmej; send stays B5-gated for the September go.

---

## Summary
Delivered the four September-prep deliverables (reply-SLA monitor, list sizing, deliverability, copy pack), then ran the copy pack through Gurmej to a conditional approval, applied his three edits, and shipped the approved PDF. Also self-served a DNS fix over the client's Porkbun API and fixed a false-positive in the just-built reply monitor.

---

## What Was Done This Session

### September-prep deliverables (the 4)
1. **RAD-22 reply-SLA monitor built + live.** `meji_reply_sla_daily.py`, scheduled task `MejiReplySLA` (daily 08:05, 4h repeats to 20:05, LastTaskResult=0 verified). Answered-detection uses the live-verified `GET /emails?lead=` filter after a recon agent proved `?thread_id=` is silently ignored by the Instantly API (would have marked everything answered).
2. **September list sized** via free Apollo search (0 credits): ~41,093 UK-wide universe (14.5k deciders + 26.8k organisers), ~17-18k loadable after the pipeline. Load-ready sourcing spec written.
3. **Deliverability audit** (read-only): 6 senders healthy (warmup 100); mejixmas DMARC report-blind and mejievent p=none identified. Placement-test preflight harness + seed template built.
4. **Copy pack finalized** (`piece2-cold-copy-FINAL-2026-07-29.md`): resolved the 3 review questions (30% line out, city-level personalisation, awards-only wave).

### Client loop (copy approval)
5. Drafted the September-prep message; two comms-critic rounds caught (a) Jas already closed-won, (b) DNS ask jumped my own ladder, (c) King & Moffatt severity understated (a live refund dispute, not a chase). Fixed all before send.
6. Gurmej approved conditional on 3 edits; applied all: removed "off your plate" (B), added the "someone else within the firm" redirect to A+B Email 1, shortened A Email 1. Version C untouched. Regenerated + verified the client PDF; drafted + sent the confirmation.

### Self-served + fixes
7. **mejixmas DMARC rua fixed via the client's Porkbun API** (creds already in `context/.env`): report address moved off the dead cross-domain target; verified against the authoritative NS. mejievent needs a dashboard API opt-in first (deferred to ~Aug 10 ladder step).
8. **Monitor false-positive fixed structurally:** internal-domain in-thread replies now count as answers (Jas auto-resolved); added `suppress_domains` (kingmoffatt.com) so the owner-managed dispute never ages.
9. Re-ran the missed 07-27 weekly review (task had died writing nothing); spine chain intact.

---

## Key Decisions Made

### Copy pack: outcome angle over the 30% savings line
- **Choice:** Decider arm leads on "the night lands well, zero load on your team"; 30% line removed.
- **Rationale:** Evidence says seniors answer to the outcome; a percentage reads as a mass-mailer tell. Gurmej raised no objection; it stands approved.

### DNS handled on our side, not asked of the client
- **Choice:** Execute the mejixmas fix ourselves via the Porkbun API rather than send paste instructions.
- **Rationale:** Gurmej shared API access in May (creds in `context/.env`); asking him to do it was a B1/B7 miss he caught. Self-serve is the standing path for meji DNS now.

### King & Moffatt left with the owner
- **Choice:** Suppress the thread in the monitor; do not nudge.
- **Rationale:** Gurmej confirmed it is a payment dispute they own ("getting back to all else").

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `context/analysis-scripts/meji_reply_sla_daily.py` | created | Daily reply-SLA monitor (RAD-22) |
| `context/analysis-scripts/meji_placement_test.py` | created | Seed inbox-placement preflight (send half B5-gated) |
| `context/analysis-scripts/meji_campaign_health_check.py` | edited | Added "confirm safe receipt" auto-marker |
| `context/p2/piece2-cold-copy-FINAL-2026-07-29.md` | created→approved | Internal approved P2 copy (+3 Gurmej edits) |
| `context/p2/piece2-cold-copy-FINAL-2026-07-29-CLIENT.md` | created | Client PDF source |
| `deliverables/meji-september-copy-pack-2026-07-29.pdf` | created→regenerated | Approved copy pack (PRs #484, #495) |
| `context/p2/september-prep-2026-07-29.md` | created | The 4-deliverable prep tracker |
| `context/placement-seeds.csv` | created | Seed-list template (owner to fill) |
| `context/reply-sla-state.json` | created | Monitor state + suppress_domains |
| `context/comms-log.md` | edited | Block 30 + confirmation (verbatim), entries →66 |
| `context/opportunity-radar.md` | edited | RAD-22 promoted (built, live) |

---

## Current Status
Meji: soft-active. Contract back up (Upwork investigation cleared 07-29). P2 corporate copy APPROVED, held for the September go. Warm P1 running; corporate P2A/P2B paused until reactivation. Comms current (last contact today). ops status: no `platform` section in infrastructure.yaml (meji is Make.com + Instantly + Apollo, no platform surface) — no ops-audit needed.

---

## Next Steps
1. **Second sending-domain decision** (owner) by early August, or September runs at reduced volume (3 mejievent mailboxes = ~1,980/mo before follow-ups).
2. **Settle the $589.60 bonus** for the 16 back-hours (billing functional again).
3. **~Aug 10:** mejievent DMARC ladder step 1 (self-serve: Porkbun dashboard API opt-in, then `_dmarc` edit per september-prep §3).
4. **Fill `placement-seeds.csv`** (3-5 inboxes we control) before the placement test.
5. **At the September go:** fresh sourcing run + pipeline chain + placement test + B5 readiness, per pilot-routing checklist 1-4.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/p2/september-prep-2026-07-29.md` (the 4-deliverable tracker)
- `workspace/clients/meji-media/context/p2/piece2-cold-copy-FINAL-2026-07-29.md` (approved copy + Gurmej's edits)
- `workspace/clients/meji-media/context/comms-log.md` Block 30 (full approval exchange)

### Open Questions
- Second sending domain: purchase + warm, or run September on current capacity?
- Placement seed inboxes: which addresses do we control across Gmail/Outlook?

### Working Notes
- Instantly `/emails` API: unknown query params return HTTP 200 and are SILENTLY IGNORED; `?thread_id=` looks like it filters but returns workspace-wide mail. Only `?lead=<email>` genuinely filters (returns both directions for answered-detection). Cloudflare 403s the default urllib UA; a custom User-Agent is required.
- PowerShell tool was unusable all session (exit 1, no output, even on a trivial `"hello"`); Git Bash + `schtasks` (German-locale field labels) was the working path for the scheduled task.
- PDF verification: extract-text over an Edge-rendered PDF wraps lines, so a tight regex gives false FAILs; verify with whitespace-normalized text.
- The monitor's `suppress_domains`/`suppress_leads` in `reply-sla-state.json` is the durable owner-managed-thread mechanism.

### Reference Materials
- Approved copy PDF: `workspace/clients/meji-media/deliverables/meji-september-copy-pack-2026-07-29.pdf`
- RAD-22 in `context/opportunity-radar.md`

---

## How to Continue
`/resume meji-media`. The September relaunch is prep-complete and copy-approved; the next real work is at the September go (all send actions B5-gated). Between now and then: the owner-side items (domain decision, bonus, seed list) and the ~Aug 10 DMARC step.

---

## Strategic Feedback

### What Worked Well This Session
- The recon workflow (3 parallel read-only agents) surfaced the `?thread_id=` silent-ignore trap BEFORE it shipped into the monitor, which is exactly the failure the reply-SLA tool exists to prevent.
- The comms-critic caught three real client-facing errors (closed-won lead, mis-sequenced ask, understated dispute) pre-send across two rounds.

### Suggestions
- When a newly-built monitor surfaces flags destined for a client message, cross-check each flag against comms-log / the full thread before drafting, not after the critic. The digest's single preview is not the whole thread.

### System Health
- Autonomy: 2 human interventions (July-version framing, Porkbun access), both client-comms corrections, not build failures. Not elevated.
- The Porkbun miss is the highest-value lesson: enumerate our own access (B1/B7) before proposing any client-side action; the credential was in `context/.env` the whole time.
