"""Guard pins: the anti-overfit floor gets the same reviewed-hash treatment
as the metric.

Scorers were hash-pinned from day one because the agent that optimizes against
a metric must not be able to move it. Guards were not - yet a guard carries the
whole RECIPES rule-3 anti-overfit floor, and `cmd_start` hashed guards straight
from the live tree. During a run the file ACL plus per-round hash re-verify
cover them; the open window was BETWEEN runs, where a weakened guard would be
locked in at the next `start` with nothing to compare against.

test_scorer_pins.py is the model for this suite. CI running it is what makes a
drifted guard un-mergeable.
"""
import importlib.util
import json
import os
import subprocess
import sys

from hooklib import REPO

_spec = importlib.util.spec_from_file_location(
    "pin_scorer", REPO / "tools" / "pin_scorer.py")
_pin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pin)

REGISTRY = REPO / "tools" / "guard-pins.json"


def test_registry_exists_and_is_a_dict():
    assert REGISTRY.is_file(), "tools/guard-pins.json is missing"
    assert isinstance(json.loads(REGISTRY.read_text(encoding="utf-8")), dict)


def test_every_pinned_guard_matches_its_hash():
    """The CI clause: a guard edited without re-pinning cannot merge."""
    failures = _pin.guard_failures()
    assert not failures, "\n".join(failures)


def declared_guard_scripts(manifest_text: str) -> set:
    """The guard scripts a manifest DECLARES, read from its frontmatter only.

    `guards:` / `guard_files:` in the YAML frontmatter are the authoritative
    declaration; `optimize_run.validate_manifest` derives the locked guard set
    from exactly those two keys. The prose body is not a declaration: it
    routinely cites tool paths, and comd_optimize Step 2.0 MANDATES naming
    `tools/optimize_overview.py --prior-art` before the manifest is written, so
    a manifest that documents following the required step necessarily mentions
    a tool it does not guard with. Scanning the whole file turned every such
    citation into a false "unpinned guard".

    A manifest with no frontmatter declares nothing; the engine refuses it at
    `start`, so returning an empty set loses no coverage.
    """
    import re
    fm = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", manifest_text, re.DOTALL)
    if not fm:
        return set()
    found = set()
    for m in re.finditer(r"(tools/[A-Za-z0-9._-]+\.py)", fm.group(1)):
        rel = m.group(1)
        # Scorers have their own registry; shared validators are guards
        # only incidentally and are covered by the advisory at lock-on.
        if rel.startswith("tools/scorers/") or "validate-html" in rel:
            continue
        found.add(rel)
    return found


def test_every_guard_named_by_a_shipped_manifest_is_pinned():
    """Coverage, derived from the journals rather than a hand-kept list.

    A guard that a real run depends on but nobody pinned is the gap this
    change exists to close, so it is asserted against the manifests on disk -
    a new run that introduces an unpinned guard fails here.
    """
    pins = _pin.load_guard_pins()
    missing = set()
    for run_md in (REPO / "docs" / "optimize").glob("*/RUN.md"):
        text = run_md.read_text(encoding="utf-8", errors="replace")
        for rel in declared_guard_scripts(text):
            if rel not in pins and (REPO / rel).is_file():
                missing.add(f"{run_md.parent.name} -> {rel}")
    assert not missing, "guard(s) used by a shipped run but unpinned:\n" + \
        "\n".join(sorted(missing))


_MANIFEST = """---
tag: t
guards:
  - uv run tools/gtm-plan-validate.py some/asset.json
guard_files:
  - tools/gtm-plan-validate.py
scorer: tools/scorers/gtm-roi-v2.py
---

Read the prior art first: `uv run tools/optimize_overview.py --prior-art x`.
"""


def test_declared_guards_come_from_the_frontmatter():
    assert declared_guard_scripts(_MANIFEST) == {"tools/gtm-plan-validate.py"}


def test_prose_citation_of_a_tool_is_not_a_declared_guard():
    """The regression: `tools/optimize_overview.py` is cited in the body of
    every manifest that follows comd_optimize Step 2.0, and is not a guard."""
    assert "tools/optimize_overview.py" not in declared_guard_scripts(_MANIFEST)


def test_a_real_unpinned_guard_still_fails():
    """The fix must not become a hole: a guard in the frontmatter is caught."""
    text = _MANIFEST.replace("tools/gtm-plan-validate.py",
                             "tools/not-pinned-guard.py")
    assert declared_guard_scripts(text) == {"tools/not-pinned-guard.py"}


def test_manifest_without_frontmatter_declares_nothing():
    assert declared_guard_scripts("no frontmatter tools/x.py here\n") == set()


def test_pin_guard_refuses_without_the_seam(tmp_path):
    env = dict(os.environ)
    env.pop("SCORER_LOCK_ALLOW", None)
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / "pin_scorer.py"),
         "pin-guard", "tools/gtm-stress-guard.py"],
        capture_output=True, text=True, env=env)
    assert proc.returncode == 1
    assert "SCORER_LOCK_ALLOW" in proc.stderr


def test_pin_guard_refuses_a_scorer():
    """Scorers must keep going through `pin`, so PINS.json stays the one
    place a metric change shows up in review."""
    env = dict(os.environ, SCORER_LOCK_ALLOW="1")
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / "pin_scorer.py"),
         "pin-guard", "tools/scorers/page-weight.py"],
        capture_output=True, text=True, env=env)
    assert proc.returncode == 1
    assert "is a SCORER" in proc.stderr


def test_check_reports_drift(tmp_path, monkeypatch):
    """guard_failures must actually notice a changed byte."""
    target = tmp_path / "fake-guard.py"
    target.write_text("print(1)\n", encoding="utf-8")
    reg = tmp_path / "guard-pins.json"
    reg.write_text(json.dumps({"fake-guard.py": {"sha": "deadbeef"}}),
                   encoding="utf-8")
    monkeypatch.setattr(_pin, "GUARD_PINS_PATH", str(reg))
    monkeypatch.setattr(_pin, "REPO", str(tmp_path))
    failures = _pin.guard_failures()
    assert any("GUARD DRIFT" in f for f in failures), failures


def test_check_reports_orphan(tmp_path, monkeypatch):
    reg = tmp_path / "guard-pins.json"
    reg.write_text(json.dumps({"gone.py": {"sha": "deadbeef"}}),
                   encoding="utf-8")
    monkeypatch.setattr(_pin, "GUARD_PINS_PATH", str(reg))
    monkeypatch.setattr(_pin, "REPO", str(tmp_path))
    assert any("ORPHAN GUARD PIN" in f for f in _pin.guard_failures())
