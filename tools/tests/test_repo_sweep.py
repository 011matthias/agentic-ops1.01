"""Safety-gate tests for tools/repo-sweep.py (the nightly unattended sweeper).

The dangerous failure modes are committing credentials, committing huge
binaries, and misrouting client work into the wrong thematic commit; these
tests pin the pure gate/grouping logic that prevents each.
"""
import importlib.util
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("repo_sweep", TOOLS / "repo-sweep.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)


def test_credential_names_denied():
    for name in (".env", ".env.local", "graph_token.txt", "ld_secrets.env",
                 "id_rsa", "service.key", "api-credentials.json", ".npmrc"):
        assert rs.is_credential_name(name), name


def test_credential_templates_allowed():
    for name in (".env.example", ".env.sample", ".env.template"):
        assert not rs.is_credential_name(name), name


def test_ordinary_files_allowed():
    for name in ("README.md", "app.py", "index.html", "uv.lock", "keyed-list.md"):
        assert not rs.is_credential_name(name), name


def test_grouping_routes_by_area():
    assert rs.group_for_path("docs/sessions/2026-07-17.md") == "docs"
    assert rs.group_for_path(".claude/rules/rule_x.md") == "system"
    assert rs.group_for_path("tools/repo-sweep.py") == "system"
    assert rs.group_for_path("platform/src/proxy.ts") == "platform"
    assert rs.group_for_path("workspace/clients/brisken/specs/a.md") == "client:brisken"
    assert rs.group_for_path("workspace/clients/meji-media/x.md") == "client:meji-media"
    assert rs.group_for_path("workspace/templates/x.md") == "workspace"
    assert rs.group_for_path("stray.txt") == "misc"


def test_plan_excludes_credentials_and_oversize(tmp_path):
    (tmp_path / "notes.md").write_text("ok")
    (tmp_path / ".env").write_text("SECRET=1")
    big = tmp_path / "big.bin"
    big.write_bytes(b"\0" * (rs.MAX_FILE_BYTES + 1))
    entries = [("??", "notes.md"), ("??", ".env"), ("??", "big.bin")]
    groups, skipped = rs.plan(str(tmp_path), entries)
    committed = [p for paths in groups.values() for p in paths]
    assert committed == ["notes.md"]
    assert any(".env" in s for s in skipped)
    assert any("big.bin" in s for s in skipped)


def test_plan_keeps_deletions(tmp_path):
    entries = [(" D", "docs/old-note.md")]
    groups, _ = rs.plan(str(tmp_path), entries)
    assert groups == {"docs": ["docs/old-note.md"]}


def _check(conclusion="SUCCESS", status="COMPLETED", name="ci"):
    return {"__typename": "CheckRun", "name": name,
            "status": status, "conclusion": conclusion}


def _status(state="SUCCESS", context="legacy"):
    return {"__typename": "StatusContext", "state": state, "context": context}


def test_classify_rollup_states():
    assert rs.classify_rollup([]) == "none"
    assert rs.classify_rollup([_check(), _check("SKIPPED"), _check("NEUTRAL"),
                               _status()]) == "green"
    assert rs.classify_rollup([_check(), _check("FAILURE")]) == "red"
    assert rs.classify_rollup([_check(), _status("ERROR")]) == "red"
    assert rs.classify_rollup([_check(), _check("", "IN_PROGRESS")]) == "pending"
    assert rs.classify_rollup([_check(), _status("PENDING")]) == "pending"
    # red beats pending
    assert rs.classify_rollup([_check("FAILURE"), _check("", "QUEUED")]) == "red"


def test_decide_pr_action_table():
    d = rs.decide_pr_action
    assert d("red", "MERGEABLE", False, False) == "leave_red"
    assert d("red", "CONFLICTING", False, True) == "leave_red"  # red beats conflict
    assert d("green", "CONFLICTING", False, False) == "heal"
    assert d("pending", "CONFLICTING", False, False) == "heal"
    assert d("green", "CONFLICTING", True, False) == "leave_conflict"
    assert d("green", "MERGEABLE", False, False) == "merge"
    assert d("green", "MERGEABLE", True, False) == "merge"
    assert d("green", "UNKNOWN", False, False) == "wait"
    assert d("pending", "MERGEABLE", False, False) == "wait"
    assert d("none", "MERGEABLE", False, False) == "wait"
    assert d("none", "MERGEABLE", False, True) == "leave_nochecks"


def test_sweep_branch_name_format():
    import datetime
    import re
    name = rs.sweep_branch_name(datetime.datetime(2026, 7, 17, 3, 30))
    assert re.fullmatch(r"sys/sweep-\d{8}-\d{4}", name)
    assert name == "sys/sweep-20260717-0330"


def test_newest_mtime_deletion_only_uses_ancestor_dir(tmp_path):
    sub = tmp_path / "docs"
    sub.mkdir()
    (sub / "x.md").write_text("gone soon")
    (sub / "x.md").unlink()
    age = rs.newest_mtime(str(tmp_path), [(" D", "docs/x.md")])
    assert age > 0  # ancestor dir mtime, never epoch-0
    # whole-subtree deletion walks up to an existing ancestor
    age2 = rs.newest_mtime(str(tmp_path), [(" D", "docs/deep/nested/y.md")])
    assert age2 > 0


UNION_ARTIFACT = """---
date: 2026-07-17
sessions: 6
projects_touched: [brisken, jochen-projekt]
friction_events: 4
work_types: [client-dev, comms]
sessions: 7
projects_touched: [brisken, system]
friction_events: 5
work_types: [client-dev, system-infra]
---

### Session 1 — Alpha
**Friction:** 2 — things
### Session 2 — Beta
**Friction:** None
### Session 2 — Gamma
**Friction:** 3 — more things
"""


def test_normalize_session_frontmatter_repairs_union_artifact():
    fixed = rs.normalize_session_frontmatter(UNION_ARTIFACT)
    assert fixed.count("sessions:") == 1
    assert "sessions: 3" in fixed  # three headings
    assert fixed.count("friction_events:") == 1
    assert "friction_events: 5" in fixed  # 2 + 0 + 3
    assert "projects_touched: [brisken, jochen-projekt, system]" in fixed
    assert "work_types: [client-dev, comms, system-infra]" in fixed
    assert "### Session 3 — Gamma" in fixed  # renumbered
    assert fixed.count("date: 2026-07-17") == 1
    # idempotent
    assert rs.normalize_session_frontmatter(fixed) == fixed


def test_plan_expands_untracked_dirs_and_gates_each_file(tmp_path):
    bundle = tmp_path / "docs" / "bundle"
    bundle.mkdir(parents=True)
    (bundle / "notes.md").write_text("small and fine")
    big = bundle / "huge.bin"
    big.write_bytes(b"\0" * (rs.MAX_FILE_BYTES + 1))
    (bundle / "graph_token.txt").write_text("nope")
    groups, skipped = rs.plan(str(tmp_path), [("??", "docs/bundle/")])
    committed = [p for paths in groups.values() for p in paths]
    assert committed == ["docs/bundle/notes.md"]
    assert any("huge.bin" in s and ">50MB" in s for s in skipped)
    assert any("graph_token.txt" in s and "credential" in s for s in skipped)


def test_plan_denies_junk_dirs_at_any_depth(tmp_path):
    rem = tmp_path / ".remotion" / "win64"
    rem.mkdir(parents=True)
    (rem / "shell.exe").write_bytes(b"x")
    groups, skipped = rs.plan(str(tmp_path), [
        ("??", ".remotion/"),
        ("??", "app/node_modules/pkg/index.js"),
        (" M", "docs/real-note.md"),
    ])
    committed = [p for paths in groups.values() for p in paths]
    assert committed == ["docs/real-note.md"]
    assert sum("cache/tooling" in s for s in skipped) == 2


def test_normalize_session_frontmatter_fail_open():
    assert rs.normalize_session_frontmatter("no frontmatter at all") == \
        "no frontmatter at all"
    assert rs.normalize_session_frontmatter("---\nunclosed") == "---\nunclosed"
    assert rs.normalize_session_frontmatter("") == ""


SHARD = """---
date: 2020-01-01
sessions: 1
projects_touched: [brisken]
friction_events: 1
work_types: [client-dev]
---

### Session 1 — Shard Work
**Friction:** 1 — thing
"""


def test_fold_session_shards_noop_without_sessions_dir(tmp_path):
    lines: list[str] = []
    rs.fold_session_shards(str(tmp_path), True, lines)
    assert lines == []


def test_fold_session_shards_folds_and_normalizes(tmp_path):
    sessions = tmp_path / "docs" / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "2020-01-01-abc12345.md").write_text(SHARD, encoding="utf-8")
    lines: list[str] = []
    rs.fold_session_shards(str(tmp_path), True, lines)
    assert any("session-fold: folded 1 shard(s)" in ln for ln in lines)
    assert not (sessions / "2020-01-01-abc12345.md").exists()
    text = (sessions / "2020-01-01.md").read_text(encoding="utf-8")
    assert "Shard Work" in text and "<!-- folded:" in text


def test_fold_session_shards_dry_run_writes_nothing(tmp_path):
    sessions = tmp_path / "docs" / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "2020-01-01-abc12345.md").write_text(SHARD, encoding="utf-8")
    lines: list[str] = []
    rs.fold_session_shards(str(tmp_path), False, lines)
    assert any("would fold" in ln for ln in lines)
    assert (sessions / "2020-01-01-abc12345.md").exists()
    assert not (sessions / "2020-01-01.md").exists()


def test_fold_session_shards_fail_open(tmp_path, monkeypatch):
    """A broken merge tool must log and continue, never raise (the sweep
    still commits raw shards under the union rules)."""
    sessions = tmp_path / "docs" / "sessions"
    sessions.mkdir(parents=True)
    import importlib.util as ilu

    def boom(*a, **k):
        raise RuntimeError("merge tool unloadable")

    monkeypatch.setattr(ilu, "spec_from_file_location", boom)
    lines: list[str] = []
    rs.fold_session_shards(str(tmp_path), True, lines)  # must not raise
    assert any("session-fold: skipped" in ln and "shards left as-is" in ln
               for ln in lines)
