---
description: Generate the daily morning todo briefing across all active clients + projects and deliver it by email
argument-hint: "[--no-email] [--email <address>]"
---

# Morning Briefing

Produce a single prioritized todo list spanning every ongoing client and
project, then deliver it by email. Designed to run unattended at 06:00
Europe/Berlin (remote routine) or on demand locally.

Default recipient: **neumath4@icloud.com**. Override with `--email <addr>`.
`--no-email` prints to terminal only (no send).

This command is **read-only** over the repo. It writes nothing except the
optional archived briefing file. It must never modify specs, comms, or
proposals.

## Context

- Working directory: !`pwd`
- Today: !`date +%Y-%m-%d`
- Arguments: $ARGUMENTS

## Step 1 — Scan client specs

Enumerate `workspace/clients/*/specs/{1-spec,2-build,3-test}/*.md` plus any
`4-live/*.md` with `needs_fixes: true`. Ignore `_archive`, `README.md`,
`_checklists`, `_data`.

For each, read the YAML frontmatter and capture: `id`, `name`, client,
`stage`, `next_steps[]`, `needs_fixes`, `updated`.

Bucket:
- **needs_fixes: true** → BLOCKED/NEEDS-FIX bucket.
- Specs with non-empty `next_steps` → NEXT STEPS bucket (one line per
  client = the single most actionable next_step, not the whole list).
- A spec untouched (`updated`) for >21 days while still in `1-spec` or
  `2-build` → STALLED note.

## Step 2 — Scan comms staleness

For each `workspace/clients/*/context/comms-log.md`, find the last contact
date and last speaker. Apply the `/comd_comms` staleness tiers:
OK 0-3d · NOTICE 4-7d · STALE 8-14d · URGENT 15+d.

Surface only NOTICE and worse in the STALE COMMS bucket, newest action
first. Include the open item if the log records one.

## Step 3 — Upcoming calls / dated items

Scan `workspace/clients/*/context/drafts/*.md` and
`workspace/clients/*/context/*.md` for a date in the filename or
frontmatter that falls between today and today+2 days (inclusive). These
are TODAY / IMMINENT items (e.g. a call talking-notes file). Include the
client, the date, and a one-line "what to do before it".

## Step 4 — Project status (non-client)

For each dir in `workspace/projects/*` (e.g. `local-web`, `platform`),
read its `infrastructure.yaml` / `README.md` / latest session note for an
open `next_steps` or in-flight item. One line per project, only if it has
an open item. Skip dirs with no open work.

## Step 5 — Proposal pipeline + the daily 2-proposal directive

Read `platform/src/content/proposals/*.md` frontmatter (skip the `p000`
sample). Count by `status` (draft|sent|viewed|won|lost). Action items:
- `draft` older than 3 days → send or archive
- `sent` older than 7 days → follow-up
- `won` with no `workspace/clients/{slug}/` → run `/comd_convert-proposal`

Then append the **standing directive**: the user commits to **2 new
proposals every day**. Surface it as an explicit, unmissable todo with two
concrete starting points pulled from the freshest unworked leads or
`/comd_new-proposal` candidates (name them if identifiable; otherwise state
"pick 2 from the Upwork queue").

## Step 6 — Render the briefing

Plain text, one screen, prioritized top-down. Use this exact skeleton;
omit a section entirely if it has no items (never print empty headers):

```
Morning Briefing — {Weekday} {YYYY-MM-DD}

TODAY / IMMINENT
  • {client/project} — {what + when}

DAILY COMMITMENT
  • 2 new proposals — start: {candidate 1}, {candidate 2}

BLOCKED / NEEDS DECISION
  • {client} {spec-id} — {why blocked / needs_fixes}

NEXT STEPS (by client)
  • {client}  → {single most actionable next step}

PROJECTS
  • {project} → {open item}

STALE COMMS
  • {client} ({tier}, {N}d) — {open item}

PIPELINE
  • Proposals: {draft} draft · {sent} sent · {viewed} viewed
  • {action items, if any}
```

Rules:
- No emoji. No em-dash and no `--` substitute (rule_deliverables): use a
  plain hyphen, a comma, or split the sentence. Bullets are `•`.
- One line per item. The list is for a human waking up: terse, scannable,
  verb-first ("Review", "Send", "Decide", "Follow up").
- Top 3 most urgent items first under TODAY / IMMINENT even if they also
  appear in another bucket.
- Every data value must trace to a scanned file (B4). No invented dates,
  counts, or names. If a source can't be read, write the line as
  `{client} — UNVERIFIED: {reason}` rather than guessing.

## Step 7 — Deliver

Unless `--no-email`:

1. Send the rendered briefing as a plain-text email.
   - Subject: `Morning Briefing — {YYYY-MM-DD}`
   - To: `neumath4@icloud.com` (or `--email` override)
   - Body: the rendered briefing exactly as built in Step 6.
   - Use whatever email tool is available in the running environment:
     the Gmail MCP tool locally, or the email connector attached to the
     remote routine. If no email tool is available, do NOT fail silently:
     fall back to step 2 and clearly state in the output that email could
     not be sent and why.
2. Always also write the briefing to
   `docs/briefings/{YYYY-MM-DD}.md` (create `docs/briefings/` if absent)
   so there is a searchable archive and a delivery fallback. This is the
   one file this command is allowed to write.
3. Print the briefing to the terminal too, with a final line stating the
   delivery result: `Sent to {addr}` or `Email unavailable — archived to
   docs/briefings/{date}.md`.

## Notes

- Read-only over client/project/proposal data. The only write is the
  archived briefing file.
- Safe to run multiple times a day; it just regenerates and overwrites
  that day's archive file.
- Run locally any time with `/comd_morning-briefing` to preview what the
  06:00 routine will send.
