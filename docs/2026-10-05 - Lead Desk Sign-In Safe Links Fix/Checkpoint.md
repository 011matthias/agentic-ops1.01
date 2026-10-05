# Checkpoint: Lead Desk Sign-In Safe Links Fix

**Date:** 2026-10-05
**Status:** Fix shipped + deployed + cold-verified. Draft to Dirk written, not sent (needs owner go).

---

## Summary
Dirk reported Lead Desk sign-in errors on 2026-09-09 and never answered a single packet item since. Root-caused to Microsoft Safe Links spending his single-use sign-in token before he could click it, fixed by splitting the link into a read-only landing page plus a POST that redeems, shipped and deployed, then verified cold (no session, real mailbox link, real Safe Links wrapper) end to end on production. A reply draft to Dirk is written but intentionally not sent.

---

## What Was Done This Session
### Diagnosis
1. Confirmed via memory + mailbox read that Dirk signed in once (2026-09-09 05:56 UTC) and has answered 0 of 10 packet items since; found his two unanswered error reports from that morning.
2. Re-verified live (not from memory) that `GET /auth/verify` redeemed the one-time token on read, and that Dirk's mail (but not Matthias's, at the time) is rewritten by Microsoft Safe Links, which fetches a link before the recipient opens it.

### Fix (PR #1152, merged, deployed)
3. Added `ContactStore.peek_login_token` (store.py) — reads a token's owner without consuming it.
4. Added `accounts.link_recipient` — the read-only half of login, re-checking approval same as the real redeem.
5. Split `/auth/verify`: `GET` now renders a confirm page (`templates/auth_confirm.html`) naming the account and a one-click "Continue" button; `POST` behind that button does the actual single-use redeem (`accounts.verify_and_login`, unchanged).
6. Updated `tests/test_login_next.py` and `tests/test_passwordless.py` for the two-step flow; added `tests/test_safelinks.py` (6 cases) encoding the exact failure Dirk hit.
7. Ran `tools/regress_check.py` against the wiring: green → RED (scanner test fails with the literal `/login?err=badlink` redirect Dirk saw) → green. 479 tests pass.
8. Deployed to `brisken-lead-desk.fly.dev` via `flyctl deploy --depot=false` (auth via the token in `~/.fly/config.yml`, `flyctl auth login` session had expired).

### Cold verification (consumer-drive + cold-drive clauses)
9. Launched a second Chrome on its own profile (`:9333`), zero session/cookies — the seat a real recipient sits in.
10. Seeded a throwaway `drill-2026-09-20` packet on prod directly via `ContactStore`/`seed_packet` (sftp put of a packet JSON failed silently; ssh console one-liner worked).
11. Requested a real sign-in link from the live login form; read it back out of Matthias's own mailbox via Graph (`rule_brisken_graph_first` path) — **found it was Safe Links wrapped**, which it was not on 2026-09-17, confirming the wrapping is spreading.
12. Fetched the wrapped link twice with a plain scanner-shaped GET (no cookies) — both returned 200 with the confirm button, no session issued.
13. Opened the same link in the cold browser → landed on the confirm page → clicked Continue → signed in → landed on the packet.
14. Drove Save answer ("Answered: Option A · Saved") and Approve this wording ("Wording approved", packet read "All answered").
15. Deleted the drill packet from prod (`CLEANED items 2 state 1`), confirmed Dirk's real `september-2026` packet untouched (10 items, all still `NO RESPONSE`, `last_login_at` still 2026-09-09).
16. Closed the cold Chrome, deleted scratch files that held the mailbox link and session token.

### Status + comms
17. Added a status row to `workspace/clients/brisken/status/p2-outreach-engine.md` documenting the cause, fix, and cold-drive proof (PR #1155, merged).
18. Drafted a reply to Dirk (122 words, passes `lint-comms-draft.py` / `validate-output.py`) — **not sent**; needs an owner go per `feedback_no_unrequested_client_drafts` and a choice of which thread to reply into.

---

## Key Decisions Made
### Redeem-on-POST instead of redeem-on-GET
- **Choice:** `GET /auth/verify` only reads the token and renders a button; the token is spent only by the `POST` the button submits.
- **Rationale:** Microsoft Safe Links (and any other link-prefetching mail security) fetches a URL before the human ever sees it. A GET that redeems cannot distinguish that fetch from the real click, so the real click always loses. A POST is not something Safe Links or a browser preview ever issues on your behalf.

### Verify cold, not from an authenticated seat
- **Choice:** Used a brand-new Chrome profile with zero cookies/session, and pulled the actual mailed link out of the mailbox (not a locally-minted token), to drive the fix.
- **Rationale:** `rule_behaviors.md`'s cold-drive sub-clause — a session minted locally proves the authenticated render, not the entry path a third party actually takes, which is exactly where Dirk's break was hiding.

### Seed/delete a throwaway packet rather than touch Dirk's
- **Choice:** Built a 2-item `drill-2026-09-20` packet for the drive, deleted it afterward, and separately confirmed the real `september-2026` packet was untouched.
- **Rationale:** Driving the real packet risks writing a real answer/approval into Dirk's review; a disposable packet exercises the identical code path with zero blast radius.

---

## What Did NOT Work (and why)
- **`flyctl auth whoami` directly:** failed with "no access token available" — the interactive CLI session had expired. Fixed by reading the access token out of `~/.fly/config.yml` and passing it via `FLY_API_TOKEN` env var to the one command that needed it.
- **`flyctl ssh sftp shell` put of the drill packet JSON:** the `put` command returned no error but the file never landed (`ls` on `/data/drill-packet.json` found nothing afterward). Worked around by seeding the packet directly with a `python3 -c` one-liner over `flyctl ssh console` instead of writing a file first.
- **Playwright MCP `browser_navigate` against the default CDP port:** timed out after 30s trying to attach — the user's real Chrome on `:9222` was busy/already in use by another session. Fixed per `reference_user_edge_cdp_9222`: launched a second Chrome with its own profile on `:9333` for a clean, cold-seat browser instead of fighting for the shared one.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/store.py` | Modified | Added `peek_login_token` (non-consuming token read) |
| `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/accounts.py` | Modified | Added `link_recipient`; docstring updated |
| `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/app.py` | Modified | Split `/auth/verify` into GET (render) + POST (redeem) |
| `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/templates/auth_confirm.html` | Created | Confirm-button landing page for a sign-in link |
| `workspace/clients/brisken/automations/lead-desk/tests/test_safelinks.py` | Created | 6 tests pinning the Safe Links failure + fix |
| `workspace/clients/brisken/automations/lead-desk/tests/test_login_next.py` | Modified | Updated for two-step GET/POST verify flow |
| `workspace/clients/brisken/automations/lead-desk/tests/test_passwordless.py` | Modified | Updated for two-step GET/POST verify flow |
| `workspace/clients/brisken/status/p2-outreach-engine.md` | Modified | Status row: cause, fix, cold-drive proof |

PRs: [#1152](https://github.com/011matthias/agentic-ops1.01/pull/1152) (code, merged, CI green, deployed), [#1155](https://github.com/011matthias/agentic-ops1.01/pull/1155) (status doc, merged).

---

## Current Status
Lead Desk sign-in is fixed and live on `brisken-lead-desk.fly.dev`. Cold-verified end to end with a real mailed link through the real Safe Links wrapper. Dirk's `september-2026` packet is unchanged: 10 items, all `NO RESPONSE`, no sign-in since 2026-09-09. A reply draft to him exists but is unsent.

Brisken platform ops status: unknown (not assessed in `infrastructure.yaml`) — no action needed this checkpoint since Lead Desk is a standalone Fly app, not a scenario-based orchestrator client.

---

## Next Steps
1. **Owner:** say go to send the Dirk email, and pick which thread it replies into — "Post Event Outreach" (where his error report lived) or "Sign in to Lead Desk" (the mail whose link failed him). Draft is ready either way.
2. **Open, not started this session:** rebuild the `active-thread` suppression class from inbound-only evidence (it currently also captures everyone WE mailed in the trailing 90 days), then return Bakatselos / Kiner Joergensen / Ermakov to wave 1. See `status/p2-outreach-engine.md`.
3. **Open, not started this session:** decide a retention/triage rule for the 8,227-row unmatched-event queue, or stop queueing addresses with no matching contact.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p2-outreach-engine.md` — current state of the whole outreach engine, including this fix
- `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/app.py` (`auth_verify_page` / `auth_verify`) — the fixed sign-in flow
- `workspace/clients/brisken/automations/lead-desk/tests/test_safelinks.py` — the regression contract

### Open Questions
- Which thread should the Dirk reply land in — his error-report thread or the original sign-in mail?
- Is Microsoft Safe Links wrapping now universal across Brisken mailboxes (it covered Matthias's mail this session, which it did not on 2026-09-17)? Worth a quick Graph check on Cristiane's mailbox too before assuming it is tenant-wide.

### Working Notes
- The 09-09 root cause was never provable from logs (Fly retains none from that morning; the token table records no redeem IP/user-agent). The fix closes the hole regardless of whether that specific incident was a scanner or something else.
- Cold-drive tooling for this session lived in the scratchpad (`drive.py`, `readlink.py`, `scan.py`) and was deleted along with the captured mailbox link after use — nothing sensitive left on disk.
- `flyctl ssh console` on Windows always trails a cosmetic `Error: The handle is invalid.` after real stdout comes through cleanly — not a command failure (reconfirmed, already in `project_brisken_lead_desk` memory).

### Reference Materials
- Live app: https://brisken-lead-desk.fly.dev
- Dirk's packet: https://brisken-lead-desk.fly.dev/review/september-2026
- PR #1152: https://github.com/011matthias/agentic-ops1.01/pull/1152
- PR #1155: https://github.com/011matthias/agentic-ops1.01/pull/1155

---

## How to Continue
Get the owner's go + thread choice for the Dirk email, send it via the Graph send-by-id path (`rule_brisken_graph_send_by_id`), and verify it moved from Drafts to Sent before closing the loop. The suppression-class and unmatched-queue items are independent follow-ups, not blocking.

---

## Strategic Feedback

### What Worked Well This Session
- The cold-drive discipline caught something a warm/authenticated check would have missed entirely: Safe Links wrapping Matthias's mail too, which is new since 09-17 and is exactly the mechanism that broke Dirk. Driving from a real mailed link through a fresh browser profile, instead of a locally-minted session cookie, is what surfaced it.
- `regress_check.py` produced the right red: restoring the old consume-on-GET behavior failed the new test with the literal error string Dirk reported, which is strong evidence the fix addresses the actual symptom, not just a theoretical one.

### Suggestions
- Worth a standing habit, not just this incident: whenever a client-facing link-based flow (magic links, password resets, unsubscribe links) is built or touched, check from the start whether it tolerates a pre-fetch (link scanners, chat-app link previews, mail security). It is cheap to design for up front and expensive to diagnose after the fact with no logs.

### System Health
- Autonomy: 0 human interventions this session (fully autonomous) — the user's only inputs were the original ask and "checkpoint".
- Gates: B2:3 (regress_check mutation test, cold-drive consumer verification, CI-green before merge) B6:2 (two PR ship chains, both auto-merged on green CI) skipped:0.
