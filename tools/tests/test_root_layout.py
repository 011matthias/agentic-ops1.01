"""The committed repo root matches the placement gate's home map (W2).

file-placement-gate.py denies a NEW root file at write time; this pins what is
already committed, so anything that reached the root without passing the gate
(the nightly sweep, a merge, a hand-made commit) goes red in CI.
"""
import subprocess

from hooklib import REPO, load_hook

GATE = load_hook("file-placement-gate.py")

# Two screenshots the sweep committed at the root; layout plan D3(f) removes
# them. Delete this exemption in the same change.
TEMPORARY = {"--full-page", "--fullpage"}


def _root_entries():
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-tree", "HEAD", "--format=%(objecttype) %(path)"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    ).stdout
    return [line.split(" ", 1) for line in out.splitlines() if line]


def test_root_files_are_in_the_allowlist():
    stray = [p for kind, p in _root_entries()
             if kind == "blob" and p.lower() not in GATE.ROOT_ALLOWLIST and p not in TEMPORARY]
    assert stray == [], f"root files outside ROOT_ALLOWLIST: {stray}"


def test_root_dirs_are_known_homes():
    stray = [p for kind, p in _root_entries()
             if kind == "tree" and p.lower() not in GATE.KNOWN_TOP_DIRS]
    assert stray == [], f"top-level dirs outside KNOWN_TOP_DIRS: {stray}"
