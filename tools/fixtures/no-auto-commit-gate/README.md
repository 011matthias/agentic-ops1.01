# Test fixtures for .claude/hooks/no-auto-commit-gate.py

Persistent fixtures for re-running the no-auto-commit hook's smoke tests across sessions and devices.

## Files

- **no-auth.jsonl** — single-turn synthetic transcript where the user message contains no ship-class authorization keyword. Used to exercise the ASK path.
- **auth.jsonl** — single-turn synthetic transcript where the user message contains "ship it" + "merge" (two authorization keywords). Used to exercise the allow path.

Both files are JSONL format: one event per line, schema `{"type":"user","message":{"role":"user","content":"..."}}` — the same shape `recent_user_messages()` parses out of the real Claude Code transcript.

## The automatic three-band model (2026-06-06)

The hook (see `rule_no_auto_commit.md`) sorts every ship-class command
into one of three bands:

- **Autonomous** — feature-branch `git commit`, feature-branch `git push`
  (no `main`/`master` refspec, no `--force`), and `gh pr create`. Allowed
  silently; no order needed.
- **Auto-merge (CI-gated)** — `gh pr merge` is allowed silently WHEN the
  target PR's CI is green (`gh pr checks` exit 0); a red / pending /
  undeterminable PR falls through to the floor.
- **Gated floor** — push-to-main, force push, commit-on-main, deploy, tag,
  release, subtree push, `gh pr close`, plus any non-green merge. Allowed
  only on an explicit user order in the transcript; otherwise ASK.

The classifier reads the **live current branch** (`git rev-parse`) and the
**live CI status** (`gh pr checks`). Two production-never env-var seams
force those inputs for deterministic, hermetic tests:

- `NO_AUTO_COMMIT_GATE_BRANCH` — forces the branch (`feature`, `main`, …)
- `NO_AUTO_COMMIT_GATE_CI` — forces the CI verdict (`green`, `red`, `pending`)

The B6-incident regression check: the 2026-05-26 harm was unverified work
landing on main. A red / pending PR does NOT auto-merge, and push-to-main /
force push stay on the gated floor; the autonomous band only covers
reversible feature-branch work.

## Source of truth: the pytest suite

The regression tests live in `tools/tests/test_no_auto_commit_gate.py` and
run in CI (the `hooks` job in `.github/workflows/ci.yml`). They are the
enforced source of truth for the band behavior; this README is the prose
companion. Run them locally exactly as CI does:

```bash
uv run --no-project --with pytest pytest tools/tests/test_no_auto_commit_gate.py -v
```

Each test drives the hook subprocess from a non-git tmp dir (so the
prototype carve-out is inert) with the two seams above forcing branch and
CI. To eyeball the live decision log after a real run:

```bash
tail -20 .claude/hooks/hook-log.txt   # allow:<tag> band=… / ASK:<tag> / fallthrough:<tag> ci=…
```

## Windows / path note

The fixture paths in this README are RELATIVE to the repo root (e.g., `tools/fixtures/no-auto-commit-gate/auth.jsonl`). This works because Claude Code launches hooks with the repo root as CWD. Do NOT use POSIX absolute paths like `/tmp/...` from PowerShell or Windows-native Python — `/tmp` maps to `C:\tmp\` on Windows-native Python (not Git Bash's mount), which usually doesn't exist. The hook's `os.path.isfile()` then returns False and the auth scan silently fails. Discovered during this hook's smoke test on 2026-05-26.
