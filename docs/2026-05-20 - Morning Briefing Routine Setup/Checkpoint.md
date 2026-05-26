# Checkpoint: Morning Briefing Routine Setup

**Date:** 2026-05-20
**Status:** Live — committed script + remote routine; tomorrow's 06:05 Berlin cron is the final unattended proof.

---

## Summary
Built the daily 06:00 morning-briefing system end to end: a `/comd_morning-briefing` command, a deterministic `tools/morning_briefing.py` script, and a remote scheduled routine (`trig_015ZoMm18Evyj3PGfUPe7tC3`) that emails the prioritized cross-client todo list via Resend. The first 06:00 firing silently failed; root cause was Cloudflare 403-blocking the default Python-urllib User-Agent at api.resend.com — fixed by setting a real UA and moving all logic into a committed, locally-testable script with a loud failure path.

---

## What Was Done This Session

### Capability built
1. New command `.claude/commands/comd_morning-briefing.md` (PR #28, merged). Read-only scan of client specs, comms staleness, upcoming dated items, projects, and proposal pipeline; renders one prioritized plain-text list.
2. New script `tools/morning_briefing.py` (PR #38, merged). Stdlib-only deterministic scan + render + Resend send. Reads `$RESEND_API_KEY` from env (repo is PUBLIC). Self-emails its own traceback on any failure so a broken run is never silent.
3. Remote routine `trig_015ZoMm18Evyj3PGfUPe7tC3` ("Morning Briefing (06:00 Berlin)"), cron `0 4 * * *` UTC, sonnet-4-6, enabled. Prompt: clone public repo + run the script with key in env and recipient as argv.

### Debug + fix arc (the long part)
1. Initial routine design depended on Gmail connector to send — turned out the claude.ai Gmail connector has NO send tool (only read/draft/label).
2. Pivoted to Resend HTTP API. Direct `curl` test from local: HTTP 200 + message id. Declared "works."
3. Scheduled 06:05 Berlin firing executed (confirmed by `last_fired_at`) but no email arrived. Diagnosed via `RemoteTrigger get` and re-running the exact code path locally: Python urllib gets `403 Forbidden code 1010` from Cloudflare. The curl-vs-urllib gap was the failure I shipped past.
4. Added explicit `User-Agent: agentic-ops-morning-briefing/1.0` header in the script; re-tested the urllib path locally → `RESEND_OK` + id. Real briefing email delivered to matneumann07@gmail.com.
5. Re-architected the routine to be trivial: clone + run script. No more LLM-rendered prose or embedded heredocs in the prompt; deterministic Python is the source of truth.

### Infra adjustments
1. Discovered the platform runs a GitHub-access check on any routine that declares a `git_repository` source — EVEN for public repos — and `/web-setup` is unavailable in this CLI. Workaround: `sources: []` + put `git clone <public url>` as STEP 0 in the prompt.
2. Discovered Resend free tier (no verified domain) only delivers to the account-owner address. Recipient pragmatically switched from `neumath4@icloud.com` to `matneumann07@gmail.com`. Documented the icloud-via-domain path for later.

---

## Key Decisions Made

### Channel: Resend HTTP API, not Gmail connector
- **Choice:** Send via Resend with the key in the private routine config; remove the Gmail connector.
- **Rationale:** The claude.ai Gmail connector has no send primitive. Resend gives true inbox delivery with a single curl, free tier covers daily volume, and the key in the routine config stays out of the public repo.

### Logic lives in a committed script, not the routine prompt
- **Choice:** All scan/render/send logic in `tools/morning_briefing.py`; the routine prompt is two lines (clone + run).
- **Rationale:** A natural-language prompt asking an LLM to faithfully execute a multi-step shell heredoc, scan dozens of files, escape JSON, and curl an API is brittle and unobservable. A committed script is deterministic, locally testable, and the failure path (`emails its own traceback`) makes silence impossible.

### Pragmatic recipient: gmail now, icloud later
- **Choice:** Ship to matneumann07@gmail.com (account-owner address allowed on Resend free tier).
- **Rationale:** Switching to icloud needs a verified domain + DNS records. The user's gmail is their inbox too; getting daily delivery working today beats blocking on domain setup.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.claude/commands/comd_morning-briefing.md` | Created (PR #28) | The on-demand command form of the briefing logic |
| `tools/morning_briefing.py` | Created (PR #38) | Deterministic stdlib scan/render/Resend-send with loud failure |
| `docs/briefings/2026-05-19.md` | Created (local preview) | First manual briefing render, uncommitted preview artifact |
| Remote routine `trig_015ZoMm18Evyj3PGfUPe7tC3` | Created + multiple updates | Daily 06:00 Berlin scheduled run |
| `memory/project_morning_briefing.md` | Created + updated | Cross-session project state + 4 hard-won gotchas |
| `memory/MEMORY.md` | Updated | Index entry pointing at the project memory |

---

## Current Status
Live: cron `0 4 * * *` UTC = 06:00-ish Berlin, enabled, pointing at the committed script. Local urllib path verified end to end (RESEND_OK + id). Remote test run triggered after the fix; tomorrow's 06:05 firing is the real proof of the scheduled path in the actual sandbox.

---

## Next Steps
1. **Confirm tomorrow's 06:05 Berlin email lands** in matneumann07@gmail.com. If it does, the system is done. If it doesn't, the script's loud-failure design means an error email arrives instead; if even that is silent, suspect remote sandbox egress to api.resend.com and inspect the routine run page at https://claude.ai/code/routines/trig_015ZoMm18Evyj3PGfUPe7tC3.
2. **Brisken / Dirk call today (2026-05-20)** — Expense Reconciliation Platform; review `workspace/clients/brisken/context/drafts/2026-05-20-dirk-call-brief.md` + talking notes before the call.
3. **Optional: verify a domain on Resend** if the user prefers neumath4@icloud.com delivery over Gmail. DNS records on a domain they own; I wire the rest.
4. **Optional: add a small marker convention** so the briefing can detect paused projects beyond `PROJECT-BOUNDARIES.md` (e.g. a `paused: true` frontmatter flag).

---

## Context for Next Session

### Files to Read First
- `memory/project_morning_briefing.md` — full state + the four gotchas
- `tools/morning_briefing.py` — the deterministic generator (locally runnable: `RESEND_API_KEY=... uv run python tools/morning_briefing.py <recipient>`)
- `.claude/commands/comd_morning-briefing.md` — the on-demand command form
- `workspace/clients/brisken/context/drafts/2026-05-20-dirk-call-brief.md` — today's call

### Open Questions
- Will the remote sandbox at 06:05 Berlin reach api.resend.com with the User-Agent fix? Local urllib path is proven; remote test run was triggered but its execution was not directly observable. Tomorrow's cron answers this.
- Switch delivery to neumath4@icloud.com via verified Resend domain? Parked.

### Working Notes
Failed approaches and why, kept here so the lesson sticks:
- **Gmail connector for sending:** the claude.ai Gmail MCP has no send_message tool — only drafts/labels/read. Cannot be used for delivery, only for draft-as-inbox-substitute.
- **Declaring `git_repository` source on a routine:** triggers the platform's GitHub access check pre-flight even for public repos, returning `github_repo_access_denied` when GitHub isn't connected. Workaround proven: `sources: []` + self-clone in the prompt.
- **Verifying delivery via curl while shipping urllib:** Cloudflare in front of api.resend.com 403s the default `Python-urllib/3.x` UA (error code 1010). Curl's UA is allowed. Always verify via the exact mechanism shipped.
- **Embedded heredoc in routine prompt:** the agent may not transcribe the heredoc faithfully, and a remote sandbox failure leaves no observable trace. Committed scripts win for unattended jobs.

### Reference Materials
- Routine page: https://claude.ai/code/routines/trig_015ZoMm18Evyj3PGfUPe7tC3
- PR #28 (command): https://github.com/011matthias/agentic-ops1.01/pull/28
- PR #38 (script + UA fix): https://github.com/011matthias/agentic-ops1.01/pull/38
- Resend API: https://resend.com/docs
- Cloudflare error 1010: blocks based on request signature (UA, TLS fingerprint); a real `User-Agent` header is sufficient here.

---

## How to Continue
If tomorrow's 06:05 email arrives correctly, this is shipped — no action. If it doesn't:
1. Check the routine page for run output.
2. Run the script locally with the same key (`RESEND_API_KEY='re_...' uv run python tools/morning_briefing.py 'matneumann07@gmail.com'`) to isolate script vs sandbox.
3. If local works, sandbox egress is the likely culprit; fallback options are (a) deliver via the Google Drive connector (already connected), or (b) verify a domain on Resend and target icloud directly.

---

## Strategic Feedback

### What Worked Well This Session
- The user pushed back twice ("it didn't work", "it wasn't sent at 6AM") instead of accepting plausible-but-wrong status. Both pushbacks were the only reason the Cloudflare/UA root cause got found; without them I would have left a silently broken cron in place. That kind of direct correction is high-signal and worth more than long status reports.

### Suggestions
- For any future scheduled remote agent, default to: **committed script + minimal prompt + loud failure** (script emails its own traceback). The "self-contained prompt with multi-step instructions for the LLM to perform unattended" pattern is fragile and unobservable; a stdlib script you can run locally is night-and-day more reliable. Worth promoting to a system rule next time `/system-dev` runs.

### System Health
- Three gotchas that hit during this session are now permanent platform footguns for any future remote-routine work: (1) GitHub source-gate on declared `git_repository` even for public repos, (2) claude.ai Gmail connector has no send primitive, (3) Cloudflare 1010 on default urllib UA at Resend. All three are documented in `memory/project_morning_briefing.md`; consider extracting them into a general "remote routine pitfalls" reference if a second scheduled routine is built.
- Autonomy score: 4 human interventions this session (elevated — run `/system-dev` to close the verification-theater gap if it recurs).
