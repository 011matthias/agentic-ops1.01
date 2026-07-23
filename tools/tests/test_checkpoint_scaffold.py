"""Tests for tools/checkpoint_scaffold.py (finalize + archive-register)."""

import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "checkpoint_scaffold.py"
spec = importlib.util.spec_from_file_location("checkpoint_scaffold", TOOL)
cs = importlib.util.module_from_spec(spec)
sys.modules["checkpoint_scaffold"] = cs
spec.loader.exec_module(cs)


def run_finalize(root: Path, payload: dict) -> int:
    p = root / "payload.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return cs.main(["--root", str(root), "finalize", "--payload", str(p)])


def base_payload(**over) -> dict:
    payload = {
        "topic": "Test Topic",
        "date": "2026-07-23",
        "work_type": "system-infra",
        "projects": ["sys"],
        "entry": {
            "focus": "Did the thing.",
            "built": "A tool",
            "friction": "None",
            "outcome": "Shipped",
        },
    }
    payload.update(over)
    return payload


class TestFinalizeFresh:
    @pytest.fixture()
    def root(self, tmp_path: Path) -> Path:
        (tmp_path / "docs" / "sessions").mkdir(parents=True)
        return tmp_path

    def test_creates_all_artifacts(self, root: Path):
        assert run_finalize(root, base_payload()) == 0
        folder = root / "docs" / "2026-07-23 - Test Topic"
        assert folder.is_dir()
        log = (root / "docs" / "sessions" / "2026-07-23.md").read_text(encoding="utf-8")
        assert "sessions: 1" in log
        assert "### Session 1 — Test Topic" in log
        assert "**Focus:** Did the thing." in log
        assert "projects_touched: [sys]" in log
        index = (root / "docs" / "INDEX.md").read_text(encoding="utf-8")
        assert "## system" in index
        assert "| 2026-07-23 | Test Topic | system-infra |" in index
        assert "%20-%20Test%20Topic/Checkpoint.md" in index
        ctx = cs.load_context_text(
            (root / "docs" / "sessions" / "2026-07-23-context.yaml").read_text(encoding="utf-8")
        )
        assert ctx["checkpoint_topic"] == "Test Topic"
        assert ctx["work_type"] == "system-infra"

    def test_second_session_merges(self, root: Path):
        run_finalize(root, base_payload())
        run_finalize(
            root,
            base_payload(
                topic="Second Topic",
                work_type="client-dev",
                projects=["brisken"],
                section="brisken",
                friction_rows=[
                    {"client": "brisken", "type": "slow-path", "desc": "a | b", "fix": "documented"}
                ],
                yaml_clients={"brisken": {"orchestrator": "fastapi"}},
            ),
        )
        log = (root / "docs" / "sessions" / "2026-07-23.md").read_text(encoding="utf-8")
        assert "sessions: 2" in log
        assert "friction_events: 1" in log
        assert "projects_touched: [sys, brisken]" in log
        assert "work_types: [system-infra, client-dev]" in log
        assert "### Session 2 — Second Topic" in log
        index = (root / "docs" / "INDEX.md").read_text(encoding="utf-8")
        assert "## brisken" in index
        reg = (root / "docs" / "friction-register.md").read_text(encoding="utf-8")
        assert "| 2026-07-23 | brisken | slow-path | a \\| b | No | documented | No |" in reg
        ctx = cs.load_context_text(
            (root / "docs" / "sessions" / "2026-07-23-context.yaml").read_text(encoding="utf-8")
        )
        assert ctx["clients"]["brisken"]["orchestrator"] == "fastapi"
        assert ctx["checkpoint_topic"] == "Second Topic"

    def test_index_row_inserted_at_section_top(self, root: Path):
        run_finalize(root, base_payload(topic="Older"))
        run_finalize(root, base_payload(topic="Newer"))
        index = (root / "docs" / "INDEX.md").read_text(encoding="utf-8")
        assert index.index("| 2026-07-23 | Newer |") < index.index("| 2026-07-23 | Older |")
        assert index.count("## system") == 1

    def test_mini_naming_increments(self, root: Path):
        run_finalize(root, base_payload(mini=True))
        folder = root / "docs" / "2026-07-23 - Test Topic"
        (folder / "Mini-Checkpoint-1.md").write_text("x", encoding="utf-8")
        run_finalize(root, base_payload(mini=True))
        index = (root / "docs" / "INDEX.md").read_text(encoding="utf-8")
        assert "[Mini-Checkpoint-1]" in index
        assert "[Mini-Checkpoint-2]" in index
        log = (root / "docs" / "sessions" / "2026-07-23.md").read_text(encoding="utf-8")
        assert "Test Topic (mini)" in log

    def test_missing_required_field(self, root: Path):
        assert run_finalize(root, {"topic": "X"}) == 2


class TestArchiveRegister:
    def test_moves_only_old_resolved_rows(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        old = (dt.date.today() - dt.timedelta(days=120)).isoformat()
        recent = (dt.date.today() - dt.timedelta(days=5)).isoformat()
        rows = [
            "# Friction Register",
            "",
            "| Date | Client | Type | Description | Resolved? | Fix |",
            "|------|--------|------|-------------|-----------|-----|",
            f"| {old} | a | slow-path | old resolved | Yes (fixed) | structural | No |",
            f"| {old} | a | slow-path | old open | No | memory | No |",
            f"| {recent} | b | missed-tool | recent resolved | Yes (fixed) | structural | No |",
        ]
        (docs / "friction-register.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
        assert cs.main(["--root", str(tmp_path), "archive-register", "--days", "60"]) == 0
        reg = (docs / "friction-register.md").read_text(encoding="utf-8")
        arc = (docs / "friction-register-archive.md").read_text(encoding="utf-8")
        assert "old resolved" in arc and "old resolved" not in reg
        assert "old open" in reg and "old open" not in arc
        assert "recent resolved" in reg and "recent resolved" not in arc

    def test_noop_when_nothing_old(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        recent = dt.date.today().isoformat()
        (docs / "friction-register.md").write_text(
            f"| {recent} | a | t | d | Yes | f |\n", encoding="utf-8"
        )
        assert cs.main(["--root", str(tmp_path), "archive-register"]) == 0
        assert not (docs / "friction-register-archive.md").exists()
