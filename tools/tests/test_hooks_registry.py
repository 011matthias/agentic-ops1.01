"""The enforcement layer's existence + consistency gate.

Cheapest, highest-value test in the suite. It would have caught the
2026-05-18->19 incident where the ENTIRE hook layer was silently dead (friction
register, root-cause entry), and it catches the recurring "hook added but never
registered" class (the hook-layer analogue of the tools/INDEX.md drift).

All assertions read tools/wire-hooks.py as the single source of truth, so the
canonical set and the suite can never disagree.
"""
import py_compile

import pytest

from hooklib import HOOKS, load_wire_hooks

wh = load_wire_hooks()


def test_all_registered_hooks_exist_on_disk():
    missing = sorted(s for s in wh.EXPECTED_HOOK_SCRIPTS if not (HOOKS / s).is_file())
    assert not missing, f"registered hooks missing from {HOOKS}: {missing}"


def test_no_unregistered_hooks_on_disk():
    on_disk = {p.name for p in HOOKS.glob("*.py")}
    expected = set(wh.EXPECTED_HOOK_SCRIPTS)
    orphan = sorted(on_disk - expected)  # file present, not registered
    ghost = sorted(expected - on_disk)   # registered, file absent
    assert not orphan and not ghost, (
        f"hook-registry drift -> orphan (on disk, unregistered): {orphan}; "
        f"ghost (registered, file missing): {ghost}. "
        "Reconcile tools/wire-hooks.py EXPECTED_HOOK_SCRIPTS + CANONICAL_HOOKS "
        "with .claude/hooks/."
    )


def test_canonical_block_wires_every_expected_script():
    wired = wh._scripts_in(wh.CANONICAL_HOOKS)
    assert wired == set(wh.EXPECTED_HOOK_SCRIPTS), (
        f"CANONICAL_HOOKS wires {sorted(wired)} but EXPECTED_HOOK_SCRIPTS is "
        f"{sorted(wh.EXPECTED_HOOK_SCRIPTS)} -- a hook is registered in one place "
        "but not the other."
    )


@pytest.mark.parametrize("script", sorted(wh.EXPECTED_HOOK_SCRIPTS))
def test_hook_compiles(script):
    py_compile.compile(str(HOOKS / script), doraise=True)
