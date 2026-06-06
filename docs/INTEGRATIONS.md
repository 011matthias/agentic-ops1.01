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

**USER ACTION (required - I cannot set these; the repo is public and I do not
hold the key value):**
```bash
gh secret set RESEND_API_KEY -R 011matthias/agentic-ops1.01      # paste the re_... key
gh variable set BRIEFING_TO  -R 011matthias/agentic-ops1.01 --body 'matneumann07@gmail.com'
gh workflow run morning-briefing.yml -R 011matthias/agentic-ops1.01   # smoke test
```
Then retire the dead Claude routine (`trig_015ZoMm18Evyj3PGfUPe7tC3`) via the
`/schedule` skill so the two mechanisms do not double-fire.

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
  emails a trimmed version.
- `tools/send_email.py` - reusable stdlib Resend sender for both (kept separate
  from `morning_briefing.py`, which stays self-contained for the bare CI sandbox).

**Both are autonomous: they NEVER ask a question; they flag in the digest.**

**SCHEDULING (B6-gated routine creation - needs an explicit owner order before I
create it).** These need Claude reasoning, so they run via the `/schedule`
skill (remote routines), not GitHub Actions. Proposed:
- EOD capture: weekday ~21:30 local, prompt `/comd_eod-capture`
- Weekly review: Friday ~16:30 local, prompt `/comd_weekly-review`
The routine environment must carry `RESEND_API_KEY` + `BRIEFING_TO` for the
email step; the file writes happen regardless.

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

- [ ] Set `RESEND_API_KEY` secret + `BRIEFING_TO` var on the repo, smoke-test the workflow (stream 1)
- [ ] Retire the dead Claude briefing routine (stream 1)
- [ ] Authorize creating the two `/schedule` routines for EOD + weekly (stream 2)
- [ ] Restart Claude Code to load the two new plugin marketplaces (streams 3, 4)
- [ ] Ship: review the staged diff and give the commit order (B6)
