# Checkpoint: Brisken September Campaign Review Packet

**Date:** 2026-09-07
**Status:** Engine ready and drilled; the September go/no-go now sits with Dirk on an in-app sign-off page. Zero real campaign sends.

---

## Summary

The paused post-Rome outreach was assessed against the live event log rather than the sheet, which reset the picture: the engine is finished and drilled, nothing has ever been sent, and every remaining gate is a human one. The session ended with those gates turned into a page Dirk can answer, `/review/september-2026` on the Lead Desk, seeded with four decisions and three wave sequences he can edit verbatim.

---

## What Was Done This Session

### Reset the campaign picture

1. Rebuilt who has actually been contacted from the Lead Desk event log (mailbox-grounded), not from the tracking sheet: 124 people across three states, 34 in live conversation, 71 reachable in September, 19 suppressed.
2. Refreshed the wave terminology into names a non-operator can hold: booth emails (E1/E2/E3, Jun 19-24), follow-up wave (Jul 8), reconnect wave (T3, Jul 21), ecosystem wave (Jul 27), personal touches. The Jul-21 wave was isolated by exact subject match so Dirk's own `Re:` threads did not inflate it.
3. Recovered the tier taxonomy from its owner-grounded source (2026-07-09): H5 11, T1 20, T2 24, T3 31, GA 40, plus ANON 123 and STOP 70 that are never contacted, and mapped touch counts per tier.
4. Corrected the wave sizes twice before they were right. The doc first carried "roughly 73 mails" against its own table summing to 96; building the real cohorts then produced 21 warm (three supposed non-responders have booked meetings), 23 cold close-out, 18 ecosystem. **83 mails maximum**, the number now in the packet, the roster and the status file.

### Built the sign-off surface (PR #700)

5. `/review/september-2026`: store migration v13 (`review_items`), `web/review.py`, the template, routes, a `seed-review` CLI subcommand, 10 HTTP-level tests. Four decisions render as multiple choice with our recommendation pre-selected; three wave sequences render with per-step editable subject and body, the recipient list behind a disclosure, and approve / save-edits / request-changes per wave. No send path exists on the page.
6. Seeded prod from the live roster (8 items) and verified the logged-in render in a browser.

### Closed the gap the user's screenshot exposed (PR #702)

7. The link opened the login gate correctly, but signing in dropped the person on the lead board with no route back to the packet. `?next=` now rides the gate redirect, the login form and the emailed magic link; `auth.safe_next_path` refuses foreign origins, protocol-relative and backslash forms. 6 tests, suite 432.
8. Proved the whole chain on production rather than in the suite: 303 carrying the encoded destination, hidden field rendered, a real single-use token minted and redeemed against the live app landing on the packet with a session cookie, and the packet rendering its 4 decision plus 3 sequence cards for that session.
9. Drilled the delivery leg self-addressed to matthias.silva and confirmed arrival over Graph. Prod carries `LEAD_DESK_AUTH_EMAILS=1`, a live GraphMailer, the pinned base URL, and Dirk approved as admin.

### Comms

10. The mail to Dirk went through six revisions under comms-critic audit, ending as a four-line link mail (the long report versions are superseded). Staged, not sent.

---

## Key Decisions Made

### Put the campaign gates in the app, not in the email

- **Choice:** Ask Dirk for his four decisions and his wording feedback on a page, not in prose he has to reply to.
- **Rationale:** The prior long-report drafts asked him to answer structure in free text, which is the shape that has historically gone unanswered for weeks. Multiple choice with a stated recommendation plus an editable copy box makes the reply a click, and it lands the answers where the engine already lives.

### Verify against the live app, not the test suite

- **Choice:** After the browser tooling hung, prove the deep-link flow with real HTTP against prod, including minting and redeeming an actual single-use token in the Fly machine.
- **Rationale:** The Lead Desk is server-rendered Jinja, so an HTTP fetch is exactly what a browser would render; there is no client-side layer hiding a difference. Green tests would not have shown that prod has auth email switched on and the base URL pinned.

### Three waves, 83 mails, and the sizes come from the cohorts

- **Choice:** Warm 21 people x2 touches, cold close-out 23 x1, ecosystem 18 x1.
- **Rationale:** Derived by building the real recipient lists rather than by tier arithmetic. Tier counts overstate reach because booked meetings, replies and suppressions cut across tiers.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../lead-desk/src/lead_desk/web/store.py` | edit | Migration v13: `review_items` + accessors |
| `.../lead-desk/src/lead_desk/web/review.py` | new | Packet seed, view build, decision/sequence submission |
| `.../lead-desk/src/lead_desk/web/app.py` | edit | Review routes; gate redirect carries `?next=`; login/verify thread it |
| `.../lead-desk/src/lead_desk/web/auth.py` | edit | `safe_next_path` open-redirect guard |
| `.../lead-desk/src/lead_desk/web/accounts.py` | edit | Magic link carries the destination |
| `.../lead-desk/src/lead_desk/web/templates/review.html` | new | The sign-off page |
| `.../lead-desk/src/lead_desk/web/templates/login.html` | edit | Hidden `next` field |
| `.../lead-desk/src/lead_desk/maintenance.py` | edit | `seed-review` subcommand |
| `.../lead-desk/tests/test_review.py` | new | 10 tests over HTTP |
| `.../lead-desk/tests/test_login_next.py` | new | 6 tests, safe-path matrix through to the email |
| `workspace/clients/brisken/status/p2-outreach-engine.md` | edit | Packet live; deep-link sign-in prod-verified |
| `context/lead-generation/outreach-reached-list-2026-09-06.md` | new | Roster, terminology, tier coverage (gitignored, PII) |
| `context/lead-generation/review-packet-september-2026.json` | new | Packet seed (gitignored, PII) |
| `context/drafts/outreach-engine-plan-to-dirk.md` | edit | Link mail v6 |
| `.claude/rules/rule_behaviors.md` | edit | Consumer-drive sub-clause: drive it cold, as the recipient |

---

## Current Status

Prod is at store v13 on `brisken-lead-desk.fly.dev`, suite 432 passing, PRs #700 / #701 / #702 / #703 merged and deployed. The packet is seeded and answers nothing yet.

The sender remains dormant: `kill_switch=1`, two send attempts in the engine's whole history, both self-tests. Campaign `rome-2026` is done, the drill campaign paused, solo arming drill steps 1-5 passed 2026-08-15.

brisken platform: unknown plan, ops usage unassessed (`infrastructure.yaml` has no platform section for the fastapi orchestrator). comms-log touched today.

The link mail to Dirk is staged and unsent; per the standing directive the user shapes and sends it.

---

## Next Steps

1. **User:** send the link mail (`context/drafts/outreach-engine-plan-to-dirk.md` v6).
2. Read Dirk's answers off `/review/september-2026` once they land; the four decisions gate wave shape, the three sequence verdicts gate copy.
3. Build the waves from his approved wording, then run the arming session (steps 6-7) before anything can send.
4. Decide the `owner@maintainiq.com` pending access request; it has sat unapproved on a client lead system since 2026-08-03.
5. `p2-outreach.md` (78d stale) looks superseded by `p2-outreach-engine.md`; verify and delete rather than let both claim the workstream.
6. Assess brisken's platform/ops section in `infrastructure.yaml`, which currently reports unknown plan and unknown usage.

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/status/p2-outreach-engine.md`
- `workspace/clients/brisken/context/lead-generation/outreach-reached-list-2026-09-06.md`
- `workspace/clients/brisken/context/lead-generation/review-packet-september-2026.json`
- `workspace/clients/brisken/context/drafts/outreach-engine-plan-to-dirk.md`

### Open Questions

- Release mode, wave-1 week, the SAP hold and the dropped six are all Dirk's to answer on the page; every wave build waits on them.
- Does Dirk want the Outlook-drafts variant (staged in his Drafts, he clicks send) or the per-wave release variant (~1.5d build)? It is decision one on the page.

### Working Notes

- **The reached counts moved twice and the third answer is the real one.** Tier arithmetic overstates reach: booked meetings, replies and suppression cut across tiers. Three T1/T2 contacts counted as non-responders have meetings booked without ever sending a reply event, which is why warm is 21 and not 24. Any recount starts from the cohort build, not the tier table.
- **The Jul-21 reconnect wave must be isolated by exact subject match** (five known subjects). Matching on `Re:` or on recipient pulls in Dirk's personal threads and inflates the wave.
- **agent-browser could not boot on this machine today** (two hangs at 180s and 240s, both background tasks exited empty). `close --all` cleared four stale sessions and it still hung. Playwright MCP is also unavailable here; it is configured against the user's Edge on CDP :9222 and refuses the connection. For server-rendered surfaces, curl plus a token minted inside the Fly machine is the faster and equally faithful path.
- **To mint a login token on prod without sending mail:** `flyctl ssh console -a brisken-lead-desk -C` running `auth.new_magic_token()` then `store.create_login_token(...)` against `/data/lead-desk.sqlite`. Single-use, 15-minute TTL. Use it for verification instead of triggering a real email.
- **Register-consumable facts about prod auth:** `LEAD_DESK_AUTH_EMAILS=1`, GraphMailer live, `LEAD_DESK_BASE_URL` pinned to the prod origin (so the emailed link cannot be spoofed via Host), users = dirk (admin, approved), matthias (admin, approved), owner@maintainiq.com (member, pending).

### Reference Materials

- https://brisken-lead-desk.fly.dev/review/september-2026
- PRs 011matthias/agentic-ops1.01 #700, #701, #702, #703

---

## How to Continue

`/comd_resume brisken`, then check whether the packet has answers: fetch `/review/september-2026` with a session (mint a token per the working note) and look at the progress line. If it still reads "4 decisions open / 3 wording reviews open", Dirk has not answered and the wave build cannot start. If answers are in, read them per item out of `review_items.response` and build the waves from his approved text, not from the seeded suggestion.

---

## Strategic Feedback

### What Worked Well This Session

- Replacing a prose ask with a surface. Six drafts of an email were spent trying to make structural questions answerable in free text; moving them into multiple choice with a stated recommendation solved in one build what the sixth draft still could not.
- Cohort-building instead of tier arithmetic caught two wrong mail counts before either reached the client.
- When the browser tooling died, the pivot to HTTP plus an in-machine token mint produced a stronger proof than the original plan: the redeem leg and the delivery leg were both exercised for real, which a snapshot assertion would not have covered.

### Suggestions

- The verification gap this session was not a missing check, it was a check run from the wrong seat. Every drive used a session I already held. The generalization worth carrying: for anything a third party will open, the first drive is cold, from their entry point, before it is called done. That is now in `rule_behaviors.md`, but it is worth watching whether it holds on the next client-facing link.

### System Health

- The friction register is at 207 KB with nothing archivable inside the sanctioned window, so it will keep growing until older resolved rows age past it. Worth a look at whether the window is the right shape.
- Seven of ten brisken status files are stale past the 21-day threshold, two at 78 days. The sweep flags them every session and nothing acts on them, which trains the flag into noise.
- Autonomy: 8 human interventions. Two were corrections to the email (drop the time ask; expand the plan detail), one was a direction change to build the page instead, one caught a real gap by screenshot, the rest set scope. Elevated, but the corrections were about taste and direction rather than about the agent failing to work autonomously.
