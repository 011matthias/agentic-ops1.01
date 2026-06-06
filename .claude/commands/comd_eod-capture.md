---
description: Unattended end-of-day capture. Scheduled counterpart of /comd_checkpoint — scans the day, updates state files, emails a digest, and STOPS at the commit boundary. Never asks questions.
argument-hint: [recipient-email]
---

This is the **exec-assistant EOD-capture agent** (adapted from
chrisbru1/exec-assistant). It runs unattended on a nightly schedule. It is the
automated, email-delivering subset of `/comd_checkpoint`: it does the
mechanical capture so the human reviews a digest instead of driving the
checkpoint by hand.

## Operating contract (read first)

- **Autonomous.** This runs with no human present. NEVER ask a question.
  Anything that `/comd_checkpoint` would ask (stale-comms logging, ambiguous
  classification) is **flagged in the digest**, not asked.
- **B6 commit boundary (hard).** Write state files freely (memory/state writes
  are not ship-class), then **STOP at the staging boundary**. Do NOT
  `git commit`, push, or PR. The digest reports what changed and is staged for
  the human's morning review. See `rule_no_auto_commit.md`.
  *Exception:* the unattended `.github/workflows/eod-capture.yml` run is granted
  explicit commit+push authority by owner authorization (2026-06-06); that grant
  lives in the workflow prompt, not here. Interactive runs of this command still
  stop at the boundary.
- **No file bloat.** Update existing canonical files. Do not create new
  per-investigation files. See `rule_no_file_bloat.md`.
- **Voice.** Any human-facing prose (the digest) inherits
  `rule_human_communication.md`: no em-dashes, no corporate-thesaurus, plain.

## 1. Connectivity / precondition check (fail loud)

Before doing work, confirm the run can deliver:
1. `git status` resolves (we are in the repo).
2. `RESEND_API_KEY` and a recipient are present (env `BRIEFING_TO` or
   `$ARGUMENTS`). If delivery is impossible, STILL do the writes (they are the
   primary value) and note "DELIVERY DEGRADED: {reason}" at the top of the
   digest, then print the digest to stdout so the scheduler log captures it.

## 2. Scan today's activity (read-only)

Time-bound to today only. Do not re-read history.
- `git log --since=midnight --stat` and `git diff --stat` — what changed.
- `docs/sessions/{TODAY}.md` — today's session log (may be empty).
- Each active client `workspace/clients/*/context/comms-log.md` — tail for
  items going stale (>3 days since last contact).
- Open specs in `1-spec` / `2-build` / `3-test` with `needs_fixes: true` or a
  `next_steps` entry.
- Drain the instrumented friction candidate buffer:
  `uv run tools/session_state.py --list-candidates`.

## 3. Extract and classify

- **Unlogged friction.** For each candidate from the buffer, make the judgment
  the hook cannot (promote real friction / discard correct-gate-fires), exactly
  per `/comd_checkpoint` step "Drain the candidate buffer". Then
  `uv run tools/session_state.py --clear-candidates`.
- **Stale comms.** Clients crossing 4 / 8 / 15-day tiers (NOTICE / STALE /
  URGENT). Flag only; never draft a message (see
  `feedback_no_unrequested_client_drafts`).
- **Open commitments.** Things "we" promised in a comms-log today.
- **Spec drift.** `needs_fixes` specs, dangling `next_steps`.

## 4. Write state (then STOP at commit boundary)

- Append today's capture to `docs/sessions/{TODAY}.md` (create with the
  frontmatter from `/comd_checkpoint` if missing). Surgical append only.
- Append any promoted friction rows to `docs/friction-register.md`.
- Do NOT create new files. Do NOT commit. Leave changes staged-but-uncommitted.

## 5. Deliver the digest

Build a short plain-text digest (subject `EOD Capture - {TODAY}`):

```
EOD Capture - {TODAY}

CHANGED TODAY
  - {N} files, {commits} commits. Staged for your review (not committed).

FRICTION (promoted)
  - {type}: {one-line}        [or "None"]

STALE COMMS
  - {client} ({TIER}, {N}d)   [or "None"]

OPEN COMMITMENTS / SPEC DRIFT
  - {item}                    [or "None"]

TOMORROW
  - {top next_step per active client}
```

Send it:
```bash
printf '%s' "$DIGEST" | python3 tools/send_email.py "EOD Capture - $(date +%F)" "$RECIPIENT"
```
Also print the digest to stdout (scheduler log of record). If the send fails,
that is a loud non-zero exit, not a silent pass.

## 6. Done

Output one line: `EOD capture complete - {N} files staged, {F} friction rows, {S} stale clients. Not committed (B6).`
