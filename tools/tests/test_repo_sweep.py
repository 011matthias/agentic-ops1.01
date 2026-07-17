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
