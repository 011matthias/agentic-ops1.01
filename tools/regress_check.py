# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Prove a fix's test suite actually bites: disable the fix, watch it go red.

WHY THIS EXISTS
---------------
A green suite proves the helper works. It does not prove the helper is WIRED.

  2026-08-22 friction row: verification-theater. Fix logged as `documented`.
  2026-08-24 friction row: recurred. The first draft of
    tests/test_card_from_receipt.py had 9 of 10 tests calling `_payment_mode` /
    `_card_last4` directly. Disabling the ingest's call to the merge left all
    ten GREEN -- the suite could not tell a shipped fix from an unwired one.
    Caught only by hand-regressing the real source (1 of 10 went red).

"Regress the real source and watch it go red" is the acceptance criterion for a
fix, not a nice-to-have (rule_behaviors B2, fix-bites-the-caller sub-clause).
Doing it by hand is easy to skip and easy to botch (a half-restored source file
is worse than no check). This runs the whole loop and always restores.

WHAT IT DOES
------------
  1. BASELINE   run the test command  -> must PASS (a red baseline is not a
                                         starting point, it is a broken tree)
  2. REGRESS    apply the mutation(s) -> each must match exactly once
  3. BITE       run the test command  -> must FAIL, or the suite does not bite
  4. RESTORE    put the original bytes back (always, even on Ctrl-C/crash)
  5. CONFIRM    run the test command  -> must PASS again (clean restore)

Exit 0 only when all five hold.

USAGE
-----
  uv run tools/regress_check.py \
      --test "uv run --no-project --with pytest pytest tools/tests/test_x.py" \
      --file app/ingest.py \
      --replace "rec = _merge_card(rec, scan)" --with "pass"

`--replace/--with` may repeat (pairs are zipped in order). `--regex` switches
both to regular expressions. `--cwd` runs the test command elsewhere.

EXIT CODES
----------
  0  the suite bites: green -> red under mutation -> green again
  1  TEST DOES NOT BITE: the suite stayed green with the fix disabled
  2  baseline is not green: fix the tree before checking the guard
  3  mutation did not apply (no match, or more than one match)
  4  restore failed / post-restore run is red  (the tree needs attention)
"""
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

FAIL_SUMMARY = re.compile(r"(\d+) failed", re.IGNORECASE)
PASS_SUMMARY = re.compile(r"(\d+) passed", re.IGNORECASE)


def run_test(cmd: str, cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        cmd if sys.platform == "win32" else shlex.split(cmd),
        shell=sys.platform == "win32",
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def summarize(output: str) -> str:
    failed = FAIL_SUMMARY.search(output)
    passed = PASS_SUMMARY.search(output)
    if failed or passed:
        return (
            f"{failed.group(1) if failed else 0} failed, "
            f"{passed.group(1) if passed else 0} passed"
        )
    # This repo's pytest.ini suppresses the count line, and a non-pytest runner
    # never had one. Fall back to the FAILED roster so the report still says
    # something about scale.
    n = sum(1 for ln in output.splitlines() if ln.startswith("FAILED"))
    if n:
        return f"{n} FAILED line(s)"
    return "(no pytest summary line)"


def apply_mutations(
    text: str, pairs: list[tuple[str, str]], use_regex: bool
) -> tuple[str, list[str]]:
    """Apply each replacement, requiring EXACTLY ONE match. Returns
    (new_text, errors); a non-empty errors list means nothing should be
    written."""
    errors: list[str] = []
    for old, new in pairs:
        if use_regex:
            hits = len(re.findall(old, text))
        else:
            hits = text.count(old)
        if hits != 1:
            errors.append(
                f"{'regex' if use_regex else 'literal'} {old!r} matched {hits} "
                "time(s); a mutation must match exactly once so the check is "
                "unambiguous about what it disabled"
            )
            continue
        text = re.sub(old, new, text, count=1) if use_regex else text.replace(old, new, 1)
    return text, errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Prove a fix's tests go red when the fix is disabled."
    )
    ap.add_argument("--test", required=True, help="the test command to run")
    ap.add_argument("--file", required=True, help="the real source file to regress")
    ap.add_argument("--replace", action="append", default=[], metavar="OLD")
    ap.add_argument("--with", action="append", default=[], dest="withs", metavar="NEW")
    ap.add_argument("--regex", action="store_true", help="treat OLD/NEW as regexes")
    ap.add_argument("--cwd", default=".", help="working directory for the test command")
    args = ap.parse_args(argv)

    if len(args.replace) != len(args.withs):
        print("ERROR: --replace and --with must appear in pairs", file=sys.stderr)
        return 3
    if not args.replace:
        print("ERROR: at least one --replace/--with pair is required", file=sys.stderr)
        return 3

    cwd = Path(args.cwd).resolve()
    src = Path(args.file)
    if not src.is_absolute():
        src = (cwd / src).resolve()
    if not src.is_file():
        print(f"ERROR: no such file: {src}", file=sys.stderr)
        return 3

    pairs = list(zip(args.replace, args.withs))
    original = src.read_bytes()

    print(f"=== 1/4 BASELINE ===\n  $ {args.test}", flush=True)
    rc, out = run_test(args.test, cwd)
    if rc != 0:
        print(f"  BASELINE IS RED ({summarize(out)}). Fix the tree first.")
        print(out[-4000:])
        return 2
    print(f"  green ({summarize(out)})")

    mutated, errors = apply_mutations(
        original.decode("utf-8"), pairs, args.regex
    )
    if errors:
        print("=== 2/4 REGRESS ===")
        for e in errors:
            print(f"  ERROR: {e}")
        return 3

    try:
        print(f"=== 2/4 REGRESS ===\n  disabled the fix in {src}", flush=True)
        src.write_text(mutated, encoding="utf-8")

        print(f"=== 3/4 BITE ===\n  $ {args.test}", flush=True)
        rc, out = run_test(args.test, cwd)
        bites = rc != 0
        print(f"  {'RED' if bites else 'still green'} ({summarize(out)})")
        if bites:
            for line in out.splitlines():
                if line.startswith("FAILED") or " FAILED" in line:
                    print(f"    {line.strip()[:200]}")
    finally:
        src.write_bytes(original)

    if src.read_bytes() != original:
        print("=== 4/4 RESTORE ===\n  RESTORE FAILED -- inspect the file now.")
        return 4
    print(f"=== 4/4 RESTORE ===\n  {src} restored; re-running", flush=True)
    rc, out = run_test(args.test, cwd)
    if rc != 0:
        print(f"  POST-RESTORE RUN IS RED ({summarize(out)}) -- the tree needs "
              "attention before you trust any of this.")
        return 4
    print(f"  green ({summarize(out)})")

    if not bites:
        print(
            "\nTEST DOES NOT BITE: the suite stayed green with the fix "
            "disabled, so it cannot tell a shipped fix from an unwired one. "
            "Add an assertion that runs THROUGH the caller the fix changed, "
            "not only through the helper it added (rule_behaviors B2, "
            "fix-bites-the-caller)."
        )
        return 1

    print("\nTEST BITES: green -> red under mutation -> green again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
