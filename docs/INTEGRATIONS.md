# Integrations (2026-06-06)

Five capability additions, all driven by the "self-prompting / autonomous
actions" thread. Source repos were chosen from a GitHub sweep; the exec-assistant
architecture (chrisbru1/exec-assistant) is the blueprint for the scheduled
agents and the briefing fix.

Nothing here was committed. Per `rule_no_auto_commit.md` (B6) all edits stop at
the staging boundary; the ship order is the owner's.

---

## 1. Morning briefing - FIXED (was: no email arriving)

**Root cause class.** The script itself was never broken (it generates a clean
briefing locally). The break was in the delivery/trigger layer: it ran off a
Claude scheduled routine, and recurring Claude routines auto-expire (7-day)
and/or their ephemeral environment had no `RESEND_API_KEY`. The old
`send()` path then silently no-op'd (printed `NO_SEND`, emailed nothing).

**Fix (exec-assistant "connectivity check, fail loud" blueprint element):**
- `tools/morning_briefing.py` gains a `--preflight` mode: verifies the key,
  the recipient, and Resend reachability, and exits non-zero with a loud
  reason. No more silent no-op.
- `.github/workflows/morning-briefing.yml`: a GitHub Actions cron (does NOT
  expire, proper secret store) runs preflight then the briefing daily. Manual
  run via `workflow_dispatch`.

**DONE 2026-06-06.** Key fetched from the old routine, `RESEND_API_KEY` secret +
`BRIEFING_TO` variable set, workflow merged to main and run:
`PREFLIGHT OK` -> `RESEND_OK {"id":"7523d32e-..."}`, real email sent. The old
routine `trig_015ZoMm18Evyj3PGfUPe7tC3` is DISABLED (not deleted; the skill
cannot delete) so the two do not double-fire.

Corrected diagnosis: the old routine was NOT expired. It fired daily with a
valid key; its remote sandbox just could not complete the send. Same key+script
deliver fine locally and from an Actions runner. (Key transited the session
transcript while wiring the secret; rotate at resend.com if needed.)

Note: the Resend sender is the sandbox `onboarding@resend.dev`, which only
delivers to the Resend account owner address. To send elsewhere, verify a
domain in Resend and change the `from:` in both `tools/morning_briefing.py` and
`tools/send_email.py`.

---

## 2. exec-assistant - BUILT (EOD capture + weekly review)

Adapted to agentic-ops: the agents reuse existing canonical state files
(`docs/sessions/`, `docs/friction-register.md`, client `comms-log.md`) instead
of a parallel `state/` store, and they respect B6 (write, then stop at the
commit boundary; never auto-commit).

- `.claude/commands/comd_eod-capture.md` - nightly, unattended counterpart of
  `/comd_checkpoint`. Scans the day, drains the friction candidate buffer,
  appends to the session log + register, emails a digest, stops at staging.
- `.claude/commands/comd_weekly-review.md` - Friday, unattended counterpart of
  `/comd_review` + `/comd_system-digest`. Writes `docs/digests/{YYYY}-W{WW}-review.md`,
  emails a trimmed version. Its System Health section sources friction from
  `tools/friction-watch.py --format json` (the canonical
  recurrence/regression/fragile-memory-sprawl/staleness detector) instead of
  re-deriving by hand, and names one `/comd_system-dev` candidate for the human.
  Rule promotion stays human-gated (rule budget, dedup, B6). Wired 2026-06-06.
- `tools/send_email.py` - reusable stdlib Resend sender for both (kept separate
  from `morning_briefing.py`, which stays self-contained for the bare CI sandbox).

**Both are autonomous: they NEVER ask a question; they flag in the digest.**

**SCHEDULING - decided 2026-06-06: GitHub Actions + claude-code-action** (not
remote routines; remote routines cannot push to this repo because GitHub is not
connected, so their captures could not persist). Built:
- `.github/workflows/eod-capture.yml` - weekdays 19:33 UTC (~21:33 Berlin)
- `.github/workflows/weekly-review.yml` - Friday 14:33 UTC (~16:33 Berlin)

Each checks out the repo, runs its command via `anthropics/claude-code-action`,
and (B6 relaxed for these unattended agents by owner authorization) commits +
pushes the capture to main via `GITHUB_TOKEN`. Interactive command runs still
stop at the boundary.

**USER ACTION:** `gh secret set ANTHROPIC_API_KEY -R 011matthias/agentic-ops1.01`
(paste an `sk-ant-...` key). RESEND + BRIEFING_TO are already set. Then smoke-test:
`gh workflow run eod-capture.yml -R 011matthias/agentic-ops1.01`. Confirm the
`anthropics/claude-code-action` version/inputs on first run (could not re-fetch
the live action spec at build time due to a transient network failure). If main
has branch protection that blocks the bot push, switch the push target to a
`automation/captures` branch.

---

## 3. planning-with-files - ADDED (plugin marketplace)

Manus-style persistent-markdown planning loop (OthmanAdi/planning-with-files).
Registered as a plugin marketplace (low-bloat; no files copied into the repo):
- marketplace cloned to `~/.claude/plugins/marketplaces/planning-with-files/`
  and registered in `known_marketplaces.json`
- enabled in `.claude/settings.json`: `planning-with-files@planning-with-files`

Activates on next Claude Code restart.

---

## 4. VoltAgent subagents - ADDED (plugin marketplace reference)

172 subagents in 10 categories (VoltAgent/awesome-claude-code-subagents),
packaged as installable plugins. Registered as a marketplace; no files copied.
- cloned to `~/.claude/plugins/marketplaces/voltagent-subagents/`, registered in
  `known_marketplaces.json`
- enabled by default (most on-theme): `voltagent-meta@voltagent-subagents`
  (multi-agent orchestration), `voltagent-research@voltagent-subagents`

The other 8 categories are available to enable one line at a time in
`enabledPlugins`: `voltagent-core-dev`, `voltagent-lang`, `voltagent-infra`,
`voltagent-qa-sec`, `voltagent-data-ai`, `voltagent-dev-exp`,
`voltagent-domains`, `voltagent-biz` (all `@voltagent-subagents`). Left disabled
to avoid loading 172 agent descriptions at every session start.

Activates on next Claude Code restart.

---

## 5. Mizoreww config - REFERENCE ONLY (vendored nothing)

Owner decision: reference only. See
`docs/references/awesome-claude-code-config-notes.md`. Short version: our
self-annealing + friction-register + verifier agents already match or exceed
their self-improvement loop and adversarial-review skill. The one idea kept in
view is their lightweight lessons-capture format for the EOD-capture agent.

---

## Files changed this session

| File | Action | Stream |
|------|--------|--------|
| `tools/morning_briefing.py` | preflight mode + entrypoint | 1 |
| `.github/workflows/morning-briefing.yml` | new scheduler | 1 |
| `tools/send_email.py` | new reusable sender | 2 |
| `.claude/commands/comd_eod-capture.md` | new command | 2 |
| `.claude/commands/comd_weekly-review.md` | new command | 2 |
| `.claude/settings.json` | enabledPlugins +3 | 3,4 |
| `~/.claude/plugins/known_marketplaces.json` | +2 marketplaces (global; .bak saved) | 3,4 |
| `docs/references/awesome-claude-code-config-notes.md` | new notes | 5 |
| `docs/INTEGRATIONS.md` | this file | all |

## Activation checklist (owner)

- [x] Briefing: secret + variable set, workflow merged + verified (RESEND_OK), old routine disabled (stream 1)
- [x] exec-assistant commands + send_email merged; EOD/weekly Actions workflows built (stream 2)
- [x] Plugin marketplaces registered + enabled in settings.json (streams 3, 4)
- [ ] **Set `ANTHROPIC_API_KEY` repo secret**, then smoke-test `eod-capture.yml` (stream 2)
- [ ] Restart Claude Code to load the two new plugin marketplaces (streams 3, 4)
- [ ] Optional: rotate the Resend key (it transited this session's transcript)
- [ ] Branch hygiene: you are on `system/exec-assistant-integrations`; stash the brisken changes and switch back to `system/no-auto-commit-prototype-carveout` when ready
