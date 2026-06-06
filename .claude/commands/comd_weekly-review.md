---
description: Unattended weekly synthesis. Scheduled counterpart of /comd_review + /comd_system-digest — turns the week's logs into an emailed review. Never asks questions.
argument-hint: [recipient-email]
---

This is the **exec-assistant weekly-review agent** (adapted from
chrisbru1/exec-assistant's weekly-narrative). It runs unattended on a Friday
schedule. It is the automated, email-delivering subset of `/comd_review` plus
`/comd_system-digest`: it synthesizes the week so the human edits a strong
draft instead of building the review from scratch.

## Operating contract (read first)

- **Autonomous.** No human present. NEVER ask a question. Flag, do not ask.
- **B6 commit boundary (hard).** Write the digest file, then STOP. Do NOT
  commit / push / PR. See `rule_no_auto_commit.md`.
  *Exception:* the unattended `.github/workflows/weekly-review.yml` run is granted
  explicit commit+push authority by owner authorization (2026-06-06); that grant
  lives in the workflow prompt, not here. Interactive runs still stop.
- **No file bloat.** One digest file per week under `docs/digests/`. Reuse, do
  not scatter. See `rule_no_file_bloat.md`.
- **Voice.** Human-facing prose inherits `rule_human_communication.md`: no
  em-dashes, no corporate-thesaurus, opinionated and plain. Frame data with
  context, never fabricate a number (B4) — if a metric has no queryable source,
  write "TBD".

## 1. Precondition check (fail loud)

`git status` resolves; `RESEND_API_KEY` + recipient present. If delivery is
impossible, still write the digest file and note "DELIVERY DEGRADED: {reason}".

## 2. Gather the week's material (read-only)

- `git log --since='7 days ago' --stat` — what shipped.
- `docs/sessions/*.md` for the last 7 days — session focus, friction, autonomy.
- **Friction signals (authoritative — do NOT re-derive by hand):** run
  `uv run tools/friction-watch.py --format json` (the script is stdlib-only, so
  `python3 tools/friction-watch.py --format json` works if uv is not on the
  runner). This is the canonical recurrence / regression / fragile-memory-sprawl
  / staleness detector. Parse its `signals` object — `concentration`
  (`[type, count, [dates]]` for N+ same-type rows), `recurrence`
  (`[type, snippet, count]` for a Resolved=Yes pattern that came back),
  `memory_sprawl` (Fix=memory entries accumulating), `stale`
  (`{date, client, type, age_days, desc}` for unresolved >7d) — plus
  `unresolved_rows` / `total_rows`. Then open `docs/friction-register.md` only
  to read the prose of the specific rows the signals point at.
- `docs/*/Checkpoint.md` dated this week.
- Each active client's `comms-log.md` — open loops, staleness.
- Run the existing surfacing logic from `/comd_review` (patterns from logs) and
  `skil_system-digest` (system state) rather than re-deriving it here.

## 3. Produce three outputs (in one digest file)

Write `docs/digests/{YYYY}-W{WW}-review.md` containing:

**A. Week in review** — headline; what moved; what stuck; open loops; by the
numbers (only queryable numbers, else TBD).

**B. System health** — built FROM the friction-watch `signals` gathered in
step 2, not re-derived: counts by type from `concentration`; every
`recurrence` entry called out by name (a pattern that returned after
Resolved=Yes is the highest-severity signal); the `memory_sprawl` count; the
oldest 2-3 `stale` items by `age_days`; and the `unresolved_rows` total.
Autonomy trend across the week's sessions. Then name the single
highest-leverage `/comd_system-dev` candidate, chosen by this heuristic:
prefer a `recurrence`, else the highest-count `concentration` whose register
Fix column is `memory` (fragile recall, ripe for promotion to a structural
rule or hook). Frame it as a candidate for the human to action by running
`/comd_system-dev` — this agent surfaces the candidate; it never edits rules
itself (rule budget, dedup, and B6 keep rule promotion human-gated). When
quoting any register `desc` into the email, rewrite it in clean prose: the
raw register text contains em-dashes and the digest must not, per
`rule_human_communication.md`.

**C. Client roundup** — per active client: status, staleness, the single next
step. No drafted messages (see `feedback_no_unrequested_client_drafts`).

## 4. Deliver

Email a trimmed version (subject `Weekly Review - {YYYY}-W{WW}`); the full
three-part text lives in the digest file. Also print to stdout.
```bash
printf '%s' "$DIGEST" | python3 tools/send_email.py "Weekly Review - $(date +%G-W%V)" "$RECIPIENT"
```

## 5. Done

Output one line: `Weekly review complete - digest at docs/digests/{YYYY}-W{WW}-review.md. Not committed (B6).`
If the week's friction shows a regression or autonomy dropped, append:
`Recommend running /comd_system-dev.`
