"""deploy.py: the only sanctioned deploy path for brisken-expense-recon.

The refusals are the contract. On 2026-09-25 the live machine was resized to
shared-cpu-4x after a CPU-throttle outage, and any deploy from a tree cut
before that merge would have shrunk it back through its stale fly.toml. The
tree checks run against real git repositories (a bare "origin" plus a clone),
so "behind" and "ahead" are the git states the script actually sees.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

MODULE_DIR = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("recon_deploy", MODULE_DIR / "deploy.py")
deploy = importlib.util.module_from_spec(_spec)
sys.modules["recon_deploy"] = deploy
_spec.loader.exec_module(deploy)

VM = {"cpu_kind": "shared", "cpus": 4, "memory_mb": 1024}


# ── size ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,mb", [("1024mb", 1024), ("1gb", 1024), ("2GB", 2048), (512, 512)])
def test_memory_mb_reads_fly_spellings(raw, mb):
    assert deploy.memory_mb(raw) == mb


def test_desired_vm_reads_the_tracked_fly_toml():
    import tomllib
    with open(MODULE_DIR / "fly.toml", "rb") as fh:
        vm = deploy.desired_vm(tomllib.load(fh))
    assert set(vm) == {"cpu_kind", "cpus", "memory_mb"}
    assert vm["cpus"] >= 1 and vm["memory_mb"] >= 256


def test_fly_toml_without_vm_block_is_refused():
    with pytest.raises(deploy.Refused):
        deploy.desired_vm({"app": "x"})


def test_live_machine_bigger_than_fly_toml_is_a_shrink():
    live = [{"id": "m1", "cpu_kind": "shared", "cpus": 4, "memory_mb": 1024}]
    problem = deploy.shrink_problem({**VM, "cpus": 1}, live)
    assert problem and "cpus 4 -> 1" in problem


def test_live_memory_or_performance_kind_bigger_is_a_shrink():
    assert deploy.shrink_problem(VM, [{"id": "m", "cpu_kind": "shared", "cpus": 4, "memory_mb": 2048}])
    assert deploy.shrink_problem(VM, [{"id": "m", "cpu_kind": "performance", "cpus": 1, "memory_mb": 1024}])


def test_equal_or_growing_is_not_a_shrink():
    assert deploy.shrink_problem(VM, [{"id": "m", **VM}]) is None
    assert deploy.shrink_problem(VM, [{"id": "m", "cpu_kind": "shared", "cpus": 1, "memory_mb": 512}]) is None


# ── tree freshness, on real repositories ───────────────────────────────────

def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        capture_output=True, text=True, check=True,
    ).stdout


def _commit(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    _git(repo, "add", rel)
    _git(repo, "commit", "-q", "-m", f"edit {rel}")


@pytest.fixture
def repos(tmp_path):
    """(origin working copy, deploy clone, module dir inside the clone)."""
    bare = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    up = tmp_path / "upstream"
    _git(tmp_path, "clone", "-q", str(bare), str(up))
    _git(up, "checkout", "-q", "-b", "main")
    _commit(up, "mod/fly.toml", "[[vm]]\ncpus = 1\n")
    _commit(up, "docs/readme.md", "x")
    _git(up, "push", "-q", "origin", "main")
    tree = tmp_path / "deploy-tree"
    _git(tmp_path, "clone", "-q", str(bare), str(tree))
    return up, tree, tree / "mod"


def test_clean_tree_at_origin_main_passes(repos):
    up, tree, mod = repos
    assert deploy.check_tree(mod) == _git(tree, "rev-parse", "HEAD").strip()


def test_tree_behind_a_module_merge_is_refused(repos):
    # The 2026-09-25 shape: origin/main raised cpus after this tree was cut.
    up, tree, mod = repos
    _commit(up, "mod/fly.toml", "[[vm]]\ncpus = 4\n")
    _git(up, "push", "-q", "origin", "main")
    with pytest.raises(deploy.Refused, match=r"1 commit\(s\) behind origin/main.*fly\.toml"):
        deploy.check_tree(mod)


def test_tree_behind_only_outside_the_module_passes(repos):
    up, tree, mod = repos
    _commit(up, "docs/readme.md", "y")
    _git(up, "push", "-q", "origin", "main")
    assert deploy.check_tree(mod)


def test_unmerged_local_commit_in_module_is_refused(repos):
    up, tree, mod = repos
    _commit(tree, "mod/app.py", "print(1)")
    with pytest.raises(deploy.Refused, match=r"not on origin/main"):
        deploy.check_tree(mod)


def test_untracked_file_in_module_is_refused(repos):
    up, tree, mod = repos
    (mod / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(deploy.Refused, match="uncommitted or untracked"):
        deploy.check_tree(mod)


def test_unreachable_origin_is_refused(repos):
    up, tree, mod = repos
    _git(tree, "remote", "set-url", "origin", str(tree.parent / "gone.git"))
    with pytest.raises(deploy.Refused, match="freshness cannot be proven"):
        deploy.check_tree(mod)


# ── the command and the wiring ─────────────────────────────────────────────

def test_build_deploy_is_stamped_and_image_deploy_is_not_rebuilt(monkeypatch):
    monkeypatch.setattr(deploy, "flyctl", lambda: "flyctl")
    build = deploy.deploy_command("abc123", None)
    assert "--remote-only" in build and "GIT_COMMIT=abc123" in build
    assert build[build.index("--config") + 1].endswith("fly.toml")
    image = deploy.deploy_command("abc123", "registry.fly.io/x:1")
    assert image[-2:] == ["--image", "registry.fly.io/x:1"]
    assert not any(a.startswith("GIT_COMMIT") for a in image)


def test_a_refused_preflight_never_reaches_flyctl(monkeypatch, capsys):
    def refuse():
        raise deploy.Refused("tree is 3 commit(s) behind origin/main")
    ran = []
    monkeypatch.setattr(deploy, "preflight", refuse)
    monkeypatch.setattr(deploy.subprocess, "run", lambda *a, **k: ran.append(a))
    assert deploy.main([]) == 2
    assert ran == []
    assert "REFUSED, nothing deployed" in capsys.readouterr().err


@pytest.fixture
def wired(repos, monkeypatch, tmp_path):
    """main() against a real tree; the 'flyctl deploy' writes a marker file,
    so whether a deploy fired is observable. Live machine = fly.toml size."""
    up, tree, mod = repos
    marker = tmp_path / "DEPLOYED"
    live = [{"id": "m1", "cpu_kind": "shared", "cpus": 1, "memory_mb": 256}]
    monkeypatch.setattr(deploy, "MODULE", mod)
    monkeypatch.setattr(deploy, "live_guests", lambda: live)
    monkeypatch.setattr(deploy, "deploy_command", lambda head, image: [
        sys.executable, "-c", f"open({str(marker)!r}, 'w').write({head!r})"])
    monkeypatch.setattr(deploy, "verify", lambda *a: [])
    return up, live, marker


def test_main_ships_a_current_tree(wired):
    up, live, marker = wired
    assert deploy.main([]) == 0
    assert marker.exists()


def test_main_refuses_a_tree_behind_origin_before_any_deploy(wired, capsys):
    up, live, marker = wired
    _commit(up, "mod/fly.toml", "[[vm]]\ncpus = 4\n")
    _git(up, "push", "-q", "origin", "main")
    assert deploy.main([]) == 2
    assert not marker.exists()
    assert "behind origin/main" in capsys.readouterr().err


def test_main_refuses_to_shrink_a_bigger_live_machine(wired, capsys):
    up, live, marker = wired
    live[0]["cpus"] = 4
    assert deploy.main([]) == 2
    assert not marker.exists()
    assert "cpus 4 -> 1" in capsys.readouterr().err


def test_dry_run_checks_but_does_not_deploy(monkeypatch, capsys):
    ran = []
    monkeypatch.setattr(deploy, "preflight", lambda: ("abc123", VM))
    monkeypatch.setattr(deploy, "flyctl", lambda: "flyctl")
    monkeypatch.setattr(deploy.subprocess, "run", lambda *a, **k: ran.append(a))
    assert deploy.main(["--dry-run"]) == 0
    assert ran == []
    assert "dry run: nothing deployed" in capsys.readouterr().out
