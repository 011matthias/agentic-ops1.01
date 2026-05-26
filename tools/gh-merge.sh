#!/usr/bin/env bash
# gh-merge.sh — safe `gh pr merge` wrapper that ASSERTS `state == MERGED`.
#
# Why this exists
# ---------------
# Register 2026-05-20 #107: a `gh pr merge 39 --squash --delete-branch -q`
# call silently failed (the `-q` flag is for `gh pr view`, not `gh pr merge`),
# the error was swallowed by `2>&1 | tail -1`, and the agent declared the PR
# merged. The PR stayed OPEN; the working-tree change that depended on the
# merge was attributed to a phantom revert. A recurring class — published
# state was asserted, not verified.
#
# This wrapper:
#   1) Runs `gh pr merge $PR --squash --delete-branch` (no `-q`).
#   2) Captures exit code AND stderr cleanly (no `tail` pipeline).
#   3) Polls `gh pr view $PR --json state` until state == MERGED, with a
#      bounded timeout. A flaky merge that returns 0 but doesn't actually
#      flip the state (race with GH's status updater) is caught.
#   4) On failure: prints stderr + final state, exits 1. NO masking.
#
# Usage
# -----
#   tools/gh-merge.sh <PR_NUMBER> [--rebase|--squash|--merge]
#   default merge mode: --squash
#
# Exit codes
# ----------
#   0 = merged AND verified
#   1 = merge failed OR final state != MERGED
#   2 = usage error

set -u  # NOT -e: we want to capture exit codes and continue

PR="${1:-}"
MODE="${2:---squash}"

if [[ -z "$PR" || ! "$PR" =~ ^[0-9]+$ ]]; then
  echo "usage: $0 <PR_NUMBER> [--squash|--rebase|--merge]" >&2
  exit 2
fi

# Step 1: pre-flight — confirm the PR is OPEN before attempting merge.
pre_state=$(gh pr view "$PR" --json state -q .state 2>&1)
pre_rc=$?
if [[ $pre_rc -ne 0 ]]; then
  echo "[gh-merge] FAIL: cannot read PR #$PR state (gh exit $pre_rc):" >&2
  echo "$pre_state" >&2
  exit 1
fi
if [[ "$pre_state" == "MERGED" ]]; then
  echo "[gh-merge] NOOP: PR #$PR already MERGED."
  exit 0
fi
if [[ "$pre_state" != "OPEN" ]]; then
  echo "[gh-merge] FAIL: PR #$PR state is '$pre_state' (not OPEN). Refusing merge." >&2
  exit 1
fi

# Step 2: merge — capture stderr separately so nothing is swallowed.
echo "[gh-merge] merging PR #$PR ($MODE)..."
merge_stderr=$(mktemp)
gh pr merge "$PR" "$MODE" --delete-branch 2>"$merge_stderr"
merge_rc=$?
merge_err=$(cat "$merge_stderr")
rm -f "$merge_stderr"

if [[ $merge_rc -ne 0 ]]; then
  echo "[gh-merge] FAIL: gh pr merge exit $merge_rc" >&2
  [[ -n "$merge_err" ]] && echo "[gh-merge] stderr: $merge_err" >&2
  exit 1
fi

# Step 3: verify — poll until state flips to MERGED. Bound at 6 tries x 5s.
for i in 1 2 3 4 5 6; do
  state=$(gh pr view "$PR" --json state -q .state 2>/dev/null)
  if [[ "$state" == "MERGED" ]]; then
    echo "[gh-merge] OK: PR #$PR is MERGED (verified, attempt $i)."
    exit 0
  fi
  sleep 5
done

# Final state wasn't MERGED — surface the truth, don't hide it.
final=$(gh pr view "$PR" --json state -q .state 2>/dev/null || echo "?")
echo "[gh-merge] FAIL: merge command returned 0 but PR #$PR final state is '$final', not MERGED." >&2
[[ -n "$merge_err" ]] && echo "[gh-merge] merge stderr was: $merge_err" >&2
exit 1
