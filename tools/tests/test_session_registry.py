"""Sibling-session guard: registry unit tests + the SessionStart gate's
behavior end-to-end.

Covers the load-bearing rule the whole feature rests on: two sessions in the
SAME working tree are siblings (warn); two sessions in SEPARATE worktrees
(distinct roots, isolated indexes) are NOT (silent) -- which is exactly why
"use a git worktree" is the fix the advisory recommends.
"""
import json
import sys
import time

import pytest

from hooklib import TOOLS, run_hook

sys.path.insert(0, str(TOOLS))
import session_registry as sr  # noqa: E402


def _mktree(base, branch="main"):
    """A minimal fake working tree: a dir with a `.git` DIR + HEAD (a primary
    clone). Returns the resolved root path str, matching find_worktree_root."""
    base.mkdir(parents=True, exist_ok=True)
    g = base / ".git"
    g.mkdir(exist_ok=True)
    (g / "HEAD").write_text(f"ref: refs/heads/{branch}\n", encoding="utf-8")
    return str(base.resolve())


def _seed(hb_dir, session_id, root, branch="x", ts=None):
    hb_dir.mkdir(parents=True, exist_ok=True)
    (hb_dir / f"{session_id}.json").write_text(json.dumps({
        "session_id": session_id, "root": root, "branch": branch,
        "pid": 4242, "ts": ts if ts is not None else time.time(),
    }), encoding="utf-8")


@pytest.fixture
def hb(tmp_path, monkeypatch):
    d = tmp_path / "hb"
    monkeypatch.setattr(sr, "HEARTBEAT_DIR", str(d))
    monkeypatch.setenv("AGENTIC_OPS_SESSION_TTL", "1200")
    sr._ROOT_CACHE.clear()
    return d


# --- find_worktree_root / read_branch -------------------------------------
def test_find_root_walks_up(tmp_path, hb):
    root = _mktree(tmp_path / "repo")
    sub = tmp_path / "repo" / "a" / "b"
    sub.mkdir(parents=True)
    assert sr.find_worktree_root(str(sub)) == root


def test_find_root_none_outside_git(tmp_path, hb):
    d = tmp_path / "not-a-repo"
    d.mkdir()
    assert sr.find_worktree_root(str(d)) is None


def test_read_branch_dir(tmp_path, hb):
    root = _mktree(tmp_path / "repo", branch="client/brisken/x")
    assert sr.read_branch(root) == "client/brisken/x"


def test_read_branch_worktree_pointer(tmp_path, hb):
    # A worktree's `.git` is a FILE pointing at the gitdir that holds HEAD.
    common = tmp_path / "common" / ".git" / "worktrees" / "wt"
    common.mkdir(parents=True)
    (common / "HEAD").write_text("ref: refs/heads/sys/feature\n", encoding="utf-8")
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {common}\n", encoding="utf-8")
    assert sr.find_worktree_root(str(wt)) == str(wt.resolve())
    assert sr.read_branch(str(wt.resolve())) == "sys/feature"


# --- heartbeat + live_siblings --------------------------------------------
def test_heartbeat_writes_record(tmp_path, hb):
    root = _mktree(tmp_path / "repo")
    rec = sr.heartbeat("s1", cwd=root)
    assert rec and rec["root"] == root and rec["branch"] == "main"
    assert (hb / "s1.json").is_file()


def test_heartbeat_none_outside_git(tmp_path, hb):
    d = tmp_path / "plain"
    d.mkdir()
    assert sr.heartbeat("s1", cwd=str(d)) is None


def test_sibling_same_tree_detected(tmp_path, hb):
    root = _mktree(tmp_path / "repo")
    _seed(hb, "other", root, branch="client/y")
    sibs = sr.live_siblings("me", cwd=root)
    assert [s["session_id"] for s in sibs] == ["other"]
    assert sibs[0]["age_seconds"] >= 0


def test_self_excluded(tmp_path, hb):
    root = _mktree(tmp_path / "repo")
    _seed(hb, "me", root)
    assert sr.live_siblings("me", cwd=root) == []


def test_separate_worktree_not_sibling(tmp_path, hb):
    root_a = _mktree(tmp_path / "repoA")
    root_b = _mktree(tmp_path / "repoB")
    _seed(hb, "inA", root_a)
    # A session in tree B must NOT see the session in tree A: isolated indexes.
    assert sr.live_siblings("inB", cwd=root_b) == []


def test_stale_heartbeat_ignored(tmp_path, hb):
    root = _mktree(tmp_path / "repo")
    _seed(hb, "ghost", root, ts=time.time() - 9999)  # past the 1200s TTL
    assert sr.live_siblings("me", cwd=root) == []


def test_prune_removes_orphans(tmp_path, hb, monkeypatch):
    root = _mktree(tmp_path / "repo")
    _seed(hb, "ghost", root, ts=time.time() - 9999)
    import os
    # backdate mtime past 2x TTL so the mtime-keyed prune collects it
    old = time.time() - 9999
    os.utime(hb / "ghost.json", (old, old))
    sr._prune_opportunistic()
    assert not (hb / "ghost.json").exists()


# --- the SessionStart gate, end to end (subprocess, real hook) -------------
def test_gate_warns_on_live_sibling(tmp_path):
    hb_dir = tmp_path / "hb"
    root = _mktree(tmp_path / "repo")
    _seed(hb_dir, "sibA", root, branch="client/brisken/lead")
    env = {"AGENTIC_OPS_SESSION_DIR": str(hb_dir), "AGENTIC_OPS_SESSION_TTL": "1200"}
    r = run_hook("sibling-session-gate.py",
                 {"session_id": "me", "cwd": root}, env=env)
    assert r.returncode == 0
    assert "SIBLING-SESSION" in r.stdout
    assert "worktree" in r.stdout.lower()
    assert "client/brisken/lead" in r.stdout


def test_gate_silent_when_isolated(tmp_path):
    hb_dir = tmp_path / "hb"
    root = _mktree(tmp_path / "repo")
    env = {"AGENTIC_OPS_SESSION_DIR": str(hb_dir), "AGENTIC_OPS_SESSION_TTL": "1200"}
    r = run_hook("sibling-session-gate.py",
                 {"session_id": "me", "cwd": root}, env=env)
    assert r.returncode == 0
    assert r.stdout.strip() == ""
