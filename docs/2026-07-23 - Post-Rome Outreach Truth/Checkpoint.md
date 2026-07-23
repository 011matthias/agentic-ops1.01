# Checkpoint: Post-Rome Outreach Truth

**Date:** 2026-07-23
**Status:** Shipped — outreach truth verified, Lead Desk backfilled, two PRs merged; one invasive sheet write held for owner.

---

## Summary
Answered "what's the status of the post-Rome (TA Cook 2026) outreach" from the mailboxes themselves, found that the per-contact truth tool was false-negativing real sends, fixed it, reconciled the master sheet and the Lead Desk against the mailbox truth, and shipped the tool fix + a shared-CI fix as two separate merged PRs.

---

## What Was Done This Session
### Outreach status (the question)
1. Verified the T3 cold-reconnect wave: **24/24 sent 2026-07-21 21:34–21:40Z from `dirk.neumann@brisken.com`** (subjects de-tagged: "Following up after Rome", etc.). `nedhal.abdulaal@aramco.com` correctly dropped (no-show). 3 OOO auto-replies, 0 substantive replies (2 days out).

### Reconciliation (three sources vs mailbox truth)
2. **Master sheet:** 24/24 show `email outreach_status = "Contacted - awaiting reply"` ✓; `nedhal` = `draft ready` ✓. Gap: `last_outreach` date + `post_event_outreach` note blank for the 24; `christian.forst` keyed under alt-email.
3. **Lead Desk:** found 3 sends missing from the board (`ana.matos`, `miguel.carvalho`, `line.ehlers`) — the exact 3 filed OUT of Sent Items into `22 - SALES / Adidas` + `.../DSV` after an OOO. Backfilled via `POST /events` (idempotent by internetMessageId); verified live: all 24 now `stage=sent`.

### Tool + CI fixes (shipped)
4. **#413** — `brisken-outreach-truth.py`: replaced the unreliable `/users/{mbx}/messages` aggregate (missed Sent-Items/filed sends) with an **all-folders sweep filtered `from==owner`** per folder. Live: detection **3/25 → 24/25**, 0 folder-query failures. Inbound stays on the aggregate.
5. **#422** — one-line `ci.yml` fix (`--with requests`) so the enforcement suite can collect `test_brisken_outreach_reconcile.py` (was red on every PR). Kept separate from #413 per owner direction ("the lead desk tool has nothing to do with the [reconcile] tool").
6. Corrected the `feedback_brisken_outreach_truth_is_mailbox` memory (its "the messages collection spans ALL folders" premise was wrong for outbound).

---

## Key Decisions Made
### Trust the direct folder probe over the truth tool
- **Choice:** When the tool reported "no trace" for 21 provably-sent T3 emails, probed Dirk's Sent Items + folders directly (B3) rather than believing the tool.
- **Rationale:** 3 OOO replies proved delivery; the tool's aggregate query was the suspect, and the probe confirmed all 24 sends exist.

### Two separate PRs, not one bundle
- **Choice:** Lead-desk tool fix (#413) and the shared-CI fix (#422) shipped as separate PRs.
- **Rationale:** Owner directive — different tools, different concerns. Main already carried the comprehensive `OOO_RE`, so the CI fix collapsed to a single `ci.yml` line touching no tool code.

### Backfill, don't re-capture
- **Choice:** Posted the 3 missing sends to `/events` with real metadata instead of re-running the capture worker.
- **Rationale:** The capture worker reads `/mailFolders/sentitems` only; those 3 were filed OUT of Sent Items, so capture can't self-heal them.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `tools/brisken-outreach-truth.py` | Modified (#413) | All-folders `from==owner` outbound sweep; carries `internetMessageId` |
| `.github/workflows/ci.yml` | Modified (#422) | `--with requests` on the enforcement suite step |
| `feedback_brisken_outreach_truth_is_mailbox.md` (memory) | Modified | Corrected the aggregate-spans-all-folders premise |
| Lead Desk prod DB (Fly volume) | Data (via `/events`) | 3 backfilled `sent` events for ana.matos / miguel.carvalho / line.ehlers |

---

## Current Status
- Both PRs **merged** to `main`; worktrees removed. Not platform paths → no Vercel deploy.
- Mailbox = source of truth verified; Lead Desk now matches it (24/24 sent).
- Master sheet status correct; date/log fields still blank (held write).

---

## Next Steps
1. **(Held for owner) Master-sheet write** — `last_outreach = 2026-07-21` + `post_event_outreach` note on the 24, fix `christian.forst` email/alt-email key. Invasive SharePoint write; needs explicit go on the exact cells.
2. **T3 touch-2** to non-responders ~2026-08-02, then stop (no third email).
3. **Port the all-folders sweep into `brisken-outreach-reconcile.py`** — it shares the same aggregate blind spot for the send corpus (flagged in the memory).
4. GA wave still to prepare/send; Ashok/Accenture reply still awaited.

---

## Context for Next Session
### Files to Read First
- `tools/brisken-outreach-truth.py` (the fixed sweep)
- `workspace/clients/brisken/status/p2-rome.md`
- memory `feedback_brisken_outreach_truth_is_mailbox` (corrected)
- `workspace/clients/brisken/context/lead-generation/rome-t3-wave-rebuilt.md`

### Open Questions
- Should `brisken-outreach-reconcile.py`'s send corpus move to the per-folder sweep now, or stay on the aggregate (it dedups against the sheet)?

### Working Notes
- The aggregate `/users/{mbx}/messages` returns INBOUND reliably (caught the OOO) but NOT the mailbox's own Sent-Items/filed OUTBOUND — the root of the 21/24 false negatives. The per-folder `from==owner` filter is complete AND cheap (tiny responses).
- Dirk files sent client mail into per-company folders (`22 - SALES / <Company>`); both the old tool AND the Lead Desk capture (Sent-Items-only) are blind to those. The sweep is the general fix.
- The Lead Desk `/events` sink: `{email,type:"sent",direction,channel,occurred_at,subject,detail,source,internet_message_id}`, bearer = `LEAD_DESK_INGEST_SECRET`, idempotent by internetMessageId, matches contact by email.

### Reference Materials
- PRs: #413 (tool), #422 (CI fix)
- Lead Desk: `brisken-lead-desk.fly.dev`; DB on the Fly volume `/data/lead-desk.sqlite`

---

## How to Continue
The outreach truth question is closed. To resume: run `uv run tools/brisken-outreach-truth.py --contacts <emails>` (now reliable). The only open action on this thread is the held master-sheet write — surface the exact cells and get the owner's go before writing.

---

## Strategic Feedback

### What Worked Well This Session
- The owner's "make sure both coincide with the truth" framing forced a three-source reconciliation that surfaced a real tool bug the single-source view would have hidden.

### Suggestions
- When a tool that a rule + memory depend on gives a surprising answer, probe the underlying API directly before trusting it — this session's near-miss (almost reporting 21 contacted leads as un-contacted) came from the tool, not the data.

### System Health
- `brisken-outreach-reconcile.py` (PR #374) and the memory's "PROVEN METHOD" both still pull the send corpus from the aggregate — same blind spot. The recurrence-kill is porting the per-folder sweep, not more memory.
- Autonomy score: 3 human interventions this session (elevated — 2 B1 closing-offer deferrals caught by the stop-gate, 1 scope nudge to separate the PRs). The B1 deferrals are a continuing streak; the structural stop-gate keeps catching them.
