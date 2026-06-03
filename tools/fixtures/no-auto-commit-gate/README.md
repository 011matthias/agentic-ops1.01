# Test fixtures for .claude/hooks/no-auto-commit-gate.py

Persistent fixtures for re-running the no-auto-commit hook's smoke tests across sessions and devices.

## Files

- **no-auth.jsonl** — single-turn synthetic transcript where the user message contains no ship-class authorization keyword. Used to exercise the ASK path.
- **auth.jsonl** — single-turn synthetic transcript where the user message contains "ship it" + "merge" (two authorization keywords). Used to exercise the allow path.

Both files are JSONL format: one event per line, schema `{"type":"user","message":{"role":"user","content":"..."}}` — the same shape `recent_user_messages()` parses out of the real Claude Code transcript.

## The 5-test matrix

| Test | Command | Transcript | Expected | What it proves |
|------|---------|-----------|----------|----------------|
| A | `ls -la` | (empty path) | exit 0, no output | Non-ship-class commands pass through silently |
| B | `git commit -m test` | no-auth.jsonl | `permissionDecision: ask` JSON | Ship-class + missing authorization → ASK |
| C | `git push origin main` | auth.jsonl | exit 0, no output | Ship-class + present authorization → allow |
| D | `gh pr merge 99 --squash` | (empty path) | `permissionDecision: ask` JSON | Missing transcript defaults to ASK |
| E | `git log --oneline -5` | (any) | exit 0, no output | Read-class git commands do NOT false-fire |

## How to re-run

From the repo root, in Git Bash:

```bash
# Test A
echo '{"tool_input":{"command":"ls -la"},"transcript_path":""}' | \
  uv run python .claude/hooks/no-auto-commit-gate.py && echo "exit=$?"

# Test B
echo '{"tool_input":{"command":"git commit -m test"},"transcript_path":"tools/fixtures/no-auto-commit-gate/no-auth.jsonl"}' | \
  uv run python .claude/hooks/no-auto-commit-gate.py

# Test C
echo '{"tool_input":{"command":"git push origin main"},"transcript_path":"tools/fixtures/no-auto-commit-gate/auth.jsonl"}' | \
  uv run python .claude/hooks/no-auto-commit-gate.py && echo "exit=$?"

# Test D
echo '{"tool_input":{"command":"gh pr merge 99 --squash"},"transcript_path":""}' | \
  uv run python .claude/hooks/no-auto-commit-gate.py

# Test E
echo '{"tool_input":{"command":"git log --oneline -5"},"transcript_path":""}' | \
  uv run python .claude/hooks/no-auto-commit-gate.py && echo "exit=$?"
```

Tail the hook log after each test to confirm the logged decision:

```bash
tail -10 .claude/hooks/hook-log.txt
```

## What "PASS" means

- Test A: no stdout, exit 0. Log entry: nothing from `no-auto-commit-gate` (the hook short-circuits on non-ship-class).
- Test B: stdout contains valid JSON with `permissionDecision: ask`, `permissionDecisionReason` cites `rule_no_auto_commit.md (B6)`. Log entry: `ASK:git-commit ...`.
- Test C: no stdout, exit 0. Log entry: `allow:git-push auth='ship it to PR and merge'` (or similar — depending on which regex pattern matched first).
- Test D: same shape as Test B but with `gh-pr-merge` tag.
- Test E: no stdout, exit 0. Log entry: nothing from `no-auto-commit-gate`. (This is the critical negative test — a busted regex could false-fire on `git log`.)

## What "FAIL" means

- Test A FAIL: hook emits any JSON when given a non-ship-class command. The regex is too greedy.
- Test B FAIL: hook is silent OR emits "allow" log. The detection or ASK-path is broken.
- Test C FAIL: hook emits ASK JSON despite the transcript containing "ship it" / "merge". Either `recent_user_messages` is not parsing the JSONL correctly, OR the `AUTHORIZATION_PATTERNS` regex is too narrow.
- Test D FAIL: same as B.
- Test E FAIL: hook emits ASK JSON for a `git log` read command. The `SHIP_CLASS_PATTERNS` is wrongly matching read-class git commands.

## Windows / path note

The fixture paths in this README are RELATIVE to the repo root (e.g., `tools/fixtures/no-auto-commit-gate/auth.jsonl`). This works because Claude Code launches hooks with the repo root as CWD. Do NOT use POSIX absolute paths like `/tmp/...` from PowerShell or Windows-native Python — `/tmp` maps to `C:\tmp\` on Windows-native Python (not Git Bash's mount), which usually doesn't exist. The hook's `os.path.isfile()` then returns False and the auth scan silently fails. Discovered during this hook's smoke test on 2026-05-26.
