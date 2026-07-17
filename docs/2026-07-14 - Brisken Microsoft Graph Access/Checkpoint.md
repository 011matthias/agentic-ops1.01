# Checkpoint: Brisken Microsoft Graph Access

**Date:** 2026-07-14
**Status:** App registration live and verified; delegated login prep staged; one Exchange-side control still open

---

## Summary
Replaced the ad-hoc Planner-token-sniffing and Outlook-COM approach with a real Entra app registration for Brisken's Microsoft 365 tenant, live-verified the credential end to end, and consolidated it (plus a compensating hard gate) into the canonical Brisken secrets store.

---

## What Was Done This Session

### App registration + permissions
1. Enumerated the actual state of Graph access before proposing anything: confirmed no standing app-only credential existed, only an ephemeral CDP-sniffed Planner bearer token and a dormant, never-sent Phase 2 mail/calendar read-only request (`PHASE2-IT-REQUEST.md`, exists on `origin/main`, not on this branch).
2. Verified current Graph API requirements via live docs search rather than training-data recall: Planner app-only (`Tasks.ReadWrite.All`, no per-plan scoping exists), SharePoint least-privilege (`Sites.Selected` + per-site grant), Exchange mailbox scoping (`New-ApplicationAccessPolicy`).
3. Resolved two scope decisions with the user via AskUserQuestion: (a) add `Mail.Send`/`Mail.ReadWrite` to fully replace Outlook COM sending, not stay read-only; (b) accept the tenant-wide `Tasks.ReadWrite.All` grant for Planner despite no scoping mechanism.
4. Wrote `MICROSOFT-GRAPH-IT-REQUEST.md` (client root) consolidating all 6 application permissions + the Exchange Application Access Policy PowerShell + honest disclosure of what each scope actually grants (including the unscopable Planner grant). Explicitly marked as superseding the old `PHASE2-IT-REQUEST.md`.
5. Live-walked Dirk through the Entra portal in real time (app registration, all 6 application permissions + admin consent, client secret, then a follow-up Web-platform redirect URI + delegated `User.Read` for a future Sign-in-with-Microsoft login) since he had tenant admin access and could do it himself rather than routing through Brisken IT.
6. Diagnosed a portal false alarm: `Sites.Selected` showed amber "Not granted" after an edit-and-re-consent cycle; correctly identified as a stale UI state rather than a real gap (confirmed by decoding a live token, see below), rather than escalating it as a blocker.

### Live verification (not just config)
7. Minted a real client-credentials token and decoded its `roles` claim — confirmed all 6 application permissions are actually active, including `Sites.Selected` despite the portal's amber display.
8. Made a real, read-only Graph call (`GET /users/dirk.neumann@brisken.com/mailFolders`) — HTTP 200, proving the credential works end to end against Dirk's real mailbox, not just that consent was granted.
9. Flagged as a genuine, unresolved limitation (not glossed over): the Exchange Application Access Policy locking `Mail.*`/`Calendars.*` to just the two intended mailboxes was never confirmed as actually run. No Graph call can check for it (it's an Exchange-side object); a real check would require an invasive test against an unrelated mailbox, which was correctly declined.

### Credential handling + hard gate
10. When the user pasted the live client secret directly into chat, immediately stored it in a gitignored file rather than leaving it only in transcript, then asked for the one missing piece (Application client ID) needed to actually use it.
11. When the user said the Exchange policy "doesn't matter" given a code-level allowlist, pushed back with the accurate distinction (application-layer gate restricts what our code does; it does not restrict what the leaked credential itself could do at the Microsoft layer) rather than silently agreeing, then implemented the hard gate as a durable, binding comment on the credential itself.
12. Consolidated everything into the existing canonical secrets file (`context/.env`, already holding Brisken's GoDaddy/Zoho/Vercel credentials) instead of leaving a second one-off file, and deleted the redundant standalone file in the same change (supersession discipline).
13. Handed the user (not executed directly, per standing preference) the exact `vault.py add "Microsoft Graph Brisken" ...` command, matching the existing `"<Service> Brisken"` naming convention already used for 7+ other Brisken vault entries.

---

## Key Decisions Made

### Application (app-only) permissions, not delegated, for the background Graph work
- **Choice:** Mail capture, cold-send automation, Calendar reads, Planner, and SharePoint all use application permissions on a dedicated app registration, not delegated user tokens.
- **Rationale:** The whole point of the migration is unattended, scheduled operation (mailbox polling every 15 min, cadence-driven cold sends with nobody watching) — delegated tokens need either a live interactive sign-in or a cached refresh token tied to one person's session, which reintroduces the exact fragility (tied to a logged-in human) that this migration is meant to remove from Outlook COM. `New-ApplicationAccessPolicy` (the mailbox-scoping mechanism) only exists for the application flow, not delegated.

### Sign-in-with-Microsoft is a separate, additive concern from the Graph data calls
- **Choice:** Added a Web-platform redirect URI + delegated `User.Read` to the same app registration, for a future login-flow upgrade to Lead Desk (replacing its shared-access-code cookie gate) — but did not build that code this session.
- **Rationale:** User auth (who's allowed into the Lead Desk board) and background data access (what the worker does with Brisken's mailboxes) are different surfaces. Conflating them would have meant either forcing every background operation through an interactive login (breaks unattended automation) or skipping the login upgrade entirely. Captured the cheap portal-side config now since Dirk was already in the right screen; deferred the actual code change to a dedicated session since it touches live auth/security on a system holding real PII.

### Full scope (Mail.Send + tenant-wide Planner) over a narrower ask
- **Choice:** User explicitly chose the maximal option on both open questions rather than the minimal read-only version originally drafted.
- **Rationale:** Stated goal was "do all of the work... via Graph," not incremental read access. Accepted knowingly disclosed trade-offs (Mail.Send is a bigger trust ask than read-only; Planner has no per-plan scoping) rather than silently defaulting to the safer, narrower posture.

### Application-layer hard gate as a compensating control, not a replacement for the Exchange policy
- **Choice:** Recorded a binding "never send/read as anyone but these two addresses" requirement directly on the credential file, while still recommending the Exchange Application Access Policy get completed.
- **Rationale:** The two controls protect against different failure modes — the code-level gate stops our own bugs from targeting the wrong mailbox; the Exchange policy is what stops a *leaked credential* from acting as any Brisken mailbox. User's "hard gate" instruction was taken at face value and implemented, but the distinction was surfaced rather than silently treating them as equivalent.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/MICROSOFT-GRAPH-IT-REQUEST.md` | Created | Consolidated, forwardable IT/portal-setup request (6 application permissions + Exchange scoping + honest scope disclosure); superseded `automations/lead-desk/PHASE2-IT-REQUEST.md`. Later updated with a live status note (app registered + verified; Exchange policy unconfirmed; hard gate in place). |
| `workspace/clients/brisken/context/.env` | Modified | Added the Graph app credential block (tenant/client ID, secret, secret ID) to the existing canonical Brisken secrets file, alongside GoDaddy/Zoho/Vercel. Carries the hard-gate requirement as a comment. |
| `workspace/clients/brisken/context/graph-app-credentials.env` | Created, then deleted same session | Interim standalone credential file, created before `context/.env` was identified as the existing canonical home; consolidated and removed to avoid two sources of truth. |

---

## Current Status
Brisken Marketing Ops Integration app registration (`79d33e4a-23a0-4e16-bee2-68396b8ee562`, tenant `aa3bd2bf-9c6e-4f49-9c4f-44f878ae9e74`) is live: all 6 application permissions consented and confirmed active in a minted token, `Mail.Read` verified end to end against Dirk's mailbox. A Web-platform redirect URI + delegated `User.Read` are staged for a future login upgrade, not yet wired into code. Credential is stored in `context/.env` with a hard-coded sender allowlist requirement; nothing has been built yet that actually calls Send/ReadWrite/Planner/SharePoint with it. Lead Desk itself is untouched this session — still on Outlook COM for sending, still on the shared access-code login.

No ops-budget line applies: Brisken's `infrastructure.yaml` `platform:` section tracks the unrelated p1 expense-reconciliation project on a custom FastAPI/Fly stack (`tier: unknown`, explicitly "operations budget TBD — not a workflow-engine op count"), not a Make/n8n metered plan, and this session's work (Lead Desk / Graph access) isn't governed by it. Brisken uses no Make.com scenarios, so the Infrastructure Reconciliation step doesn't apply. Comms log last entry 2026-07-13 (1 day stale) — under the staleness threshold, nothing to log.

---

## Next Steps
1. Confirm with Dirk whether the Exchange `New-ApplicationAccessPolicy` PowerShell block was actually run; if not, decide whether to close that gap now or continue relying solely on the code-level hard gate.
2. Grant the app `Sites.Selected` access to `/sites/MARKETING` via a Graph API call (our side, no further IT/Dirk step) — not yet done; needed before any SharePoint automation (Rome contact sheet, deck library) can use this credential.
3. Decide when to build the actual code that uses this credential: the Phase 2 mailbox-capture worker (`capture.py`, exists on `origin/main`, built but never run against real credentials) and/or a Graph-based sender to replace Outlook COM.
4. Build the Sign-in-with-Microsoft login swap for Lead Desk (replacing `LEAD_DESK_ACCESS_CODES`) as its own scoped session — portal config is ready, code is not started.
5. Delete the superseded `automations/lead-desk/PHASE2-IT-REQUEST.md` next time a branch that actually has it (this branch is 85 commits behind `origin/main` and doesn't carry that file) is checked out.
6. Rotate the client secret before its expiry (set at creation in the portal; exact date not captured this session — check the Certificates & secrets tab).
7. Carried over from the prior 2026-07-14 Brisken session (unchanged, still open): CrowdStrike note-brief staged in Dirk's Drafts; H5 hottest-five re-staging gated on explicit go; Lead Desk production sync question; guides.brisken.com fixes; resources-page Lovable migration decision.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/.env` — the credential itself + hard-gate requirement (gitignored, read directly, do not ask the user to resend it)
- `workspace/clients/brisken/MICROSOFT-GRAPH-IT-REQUEST.md` — full permission rationale + status
- `workspace/clients/brisken/automations/lead-desk/` (on `origin/main`, not this branch) — `capture.py` (Phase 2 worker) and `worker/` (current COM-based sender) for whoever builds the next piece

### Open Questions
- Was the Exchange Application Access Policy actually completed? (Section "Next Steps" #1 — cannot be checked via Graph, needs a direct answer.)
- Should the Phase 2 mailbox-capture worker and/or a Graph-based sender be built next, or should this credential sit staged until Lead Desk's login upgrade is also ready (so both ship together)?
- Client secret expiry date — not recorded; needs a portal check before it silently lapses.

### Working Notes
- The portal's "Not granted" amber status on `Sites.Selected` after an admin-consent re-run is a real, reproducible UI staleness issue in the Entra portal, not a functional gap — confirmed by decoding a live token's `roles` claim. Worth remembering if it recurs on a future permission edit: refresh the page and/or re-check via a minted token before treating it as broken.
- `New-ApplicationAccessPolicy` and its `Test-ApplicationAccessPolicy` companion are Exchange Online PowerShell only; there is no portal GUI for it and no Graph API to query whether one exists for a given AppId.
- Lead Desk is a server-rendered FastAPI + Jinja app, not a JS SPA — the Entra "platform" type for its future login flow is **Web**, not Single-page application. Caught and corrected in-session before it reached the portal.

### Reference Materials
- [Overview of Selected Permissions in OneDrive and SharePoint](https://learn.microsoft.com/en-us/graph/permissions-selected-overview)
- [Application Access Policies (legacy) — Exchange Online](https://learn.microsoft.com/en-us/exchange/permissions-exo/application-access-policies)
- [New-ApplicationAccessPolicy (ExchangePowerShell)](https://learn.microsoft.com/en-us/powershell/module/exchangepowershell/new-applicationaccesspolicy?view=exchange-ps)
- [Microsoft Graph permissions reference](https://learn.microsoft.com/en-us/graph/permissions-reference)

---

## How to Continue
Read `context/.env` for the live credential, confirm the Exchange policy status with Dirk first (Next Steps #1), then pick up either the SharePoint site grant (#2) or the mailbox-capture worker (#3) — both are small, bounded, and don't require another portal round-trip with Dirk.

---

## Strategic Feedback

### What Worked Well This Session
- Both B1 stop-hook catches this session were resolved by switching to the **AskUserQuestion tool** instead of prose-reframing the same offer, which forces an actual explicit choice rather than just changing the sentence shape. Nearly every other logged occurrence of this friction class (15+ entries in the register since 2026-05-26) was "reframed in prose, same turn" — a fix that visibly hasn't stopped the pattern from recurring. This session's variant is a genuinely different resolution, not just a different sentence.
- Verified the Graph credential's actual behavior (token roles decode + a real read-only API call) instead of trusting the portal's green checkmarks — directly caught that the amber `Sites.Selected` status was a UI artifact, not a real problem, before it could get escalated or misdiagnosed.
- Pushed back once, clearly, when the user's "it doesn't matter" claim about the Exchange policy was technically inaccurate, then still implemented exactly what was asked (the hard gate) — didn't just comply silently, didn't refuse either.

### Suggestions
- The `agent-deferred`/B1 closing-offer pattern has now recurred in essentially every Brisken (and several non-Brisken) session since 2026-05-26 — 15+ register entries, all "Yes" regression, hook holding every single time but never preventing the generation-time reflex. The memory-only fix (`feedback_no_closing_offers`) is confirmed not holding. Given this session's clean resolution via AskUserQuestion for genuine forks, consider making that the *default* structural response whenever the hook fires on a real decision point (as opposed to a bounded action that should just be executed) — i.e., codify "hook fires + it's a real fork → AskUserQuestion, not prose" as the standard recovery path, rather than leaving the recovery style to whatever the model generates in the moment.

### System Health
- `context/.env` is now the de facto single secrets file for Brisken (GoDaddy, Zoho CRM, Zoho Books, Vercel, and now the Graph app credential) — this consolidation is good, but the file has no structure enforcing "one canonical location" beyond convention; a future session could easily re-invent a `graph-app-credentials.env`-style one-off again without checking first. Worth a one-line note in `PROJECT-BOUNDARIES.md` or a `context/README.md` pointing explicitly at `context/.env` as the canonical secrets store, so the lookup doesn't depend on an agent thinking to search for existing `.env` files first.
