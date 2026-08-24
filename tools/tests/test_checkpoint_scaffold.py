"""Tests for tools/checkpoint_scaffold.py (finalize + archive-register)."""

import datetime as dt
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "checkpoint_scaffold.py"
spec = importlib.util.spec_from_file_location("checkpoint_scaffold", TOOL)
cs = importlib.util.module_from_spec(spec)
sys.modules["checkpoint_scaffold"] = cs
spec.loader.exec_module(cs)


def run_finalize(root: Path, payload: dict) -> int:
    # Pin --context-root to root so the YAML target is deterministic regardless
    # of whether the pytest tmp dir happens to sit inside a git repo.
    p = root / "payload.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return cs.main(
        ["--root", str(root), "finalize", "--payload", str(p), "--context-root", str(root)]
    )


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

    def test_dry_run_writes_nothing(self, tmp_path: Path):
        docs = tmp_path / "docs"
        docs.mkdir()
        old = (dt.date.today() - dt.timedelta(days=120)).isoformat()
        reg = docs / "friction-register.md"
        reg.write_text(f"| {old} | a | t | old resolved | Yes | f | No |\n", encoding="utf-8")
        before = reg.read_text(encoding="utf-8")
        assert cs.main(["--root", str(tmp_path), "archive-register", "--dry-run"]) == 0
        assert reg.read_text(encoding="utf-8") == before
        assert not (docs / "friction-register-archive.md").exists()

    def test_default_noop_names_a_window_that_would_work(self, tmp_path, capsys):
        # The 2026-08-24 dead end: running the default on a big register and
        # being told only "nothing to archive".
        docs = tmp_path / "docs"
        docs.mkdir()
        d40 = (dt.date.today() - dt.timedelta(days=40)).isoformat()
        (docs / "friction-register.md").write_text(
            "\n".join(f"| {d40} | a | t | row {i} | Yes | f | No |" for i in range(5)) + "\n",
            encoding="utf-8",
        )
        assert cs.main(["--root", str(tmp_path), "archive-register", "--days", "60"]) == 0
        out = capsys.readouterr().out
        assert "nothing to archive" in out
        assert "--days 30" in out and "5 resolved rows" in out


class TestPlanArchive:
    """The size advisory must be actionable or absent. On 2026-08-24 it was
    neither: 361 KB register, `archive-register` reporting "nothing to archive
    (cutoff 2026-06-25)" because every resolved row was newer than the default
    60-day cutoff, and the advisory firing on every checkpoint regardless."""

    def _register(self, tmp_path: Path, spec: list[tuple[int, bool, int]]) -> Path:
        """spec: (age_in_days, resolved, how_many)."""
        docs = tmp_path / "docs"
        docs.mkdir(exist_ok=True)
        lines = ["# Friction Register", ""]
        for age, resolved, count in spec:
            day = (dt.date.today() - dt.timedelta(days=age)).isoformat()
            flag = "Yes (fixed)" if resolved else "No"
            pad = "x" * 600  # rows big enough to cross the 200 KB threshold
            lines += [f"| {day} | a | t | {pad} | {flag} | structural | No |"] * count
        reg = docs / "friction-register.md"
        reg.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return reg

    def test_none_when_the_archiver_would_be_a_noop(self, tmp_path: Path):
        # Everything resolved is inside the newest window -> nothing to say.
        reg = self._register(tmp_path, [(3, True, 400), (2, False, 50)])
        assert cs.plan_archive(reg, reg.stat().st_size, 200_000) is None

    def test_rolls_to_a_shorter_window_that_clears_the_threshold(self, tmp_path: Path):
        # The real 2026-08-24 shape: nothing movable at 60 days, plenty at 30.
        reg = self._register(tmp_path, [(40, True, 300), (2, False, 100)])
        size = reg.stat().st_size
        assert size > 200_000
        plan = cs.plan_archive(reg, size, 200_000)
        assert plan is not None
        assert plan["days"] == 30 and plan["clears"] is True
        assert plan["rows"] == 300 and plan["after"] <= 200_000

    def test_prefers_the_most_conservative_window_that_works(self, tmp_path: Path):
        # Movable at 60 already clears it: do not recommend a shorter cutoff.
        reg = self._register(tmp_path, [(200, True, 400), (2, False, 100)])
        plan = cs.plan_archive(reg, reg.stat().st_size, 200_000)
        assert plan["days"] == 60 and plan["clears"] is True

    def test_never_recommends_below_the_ladder_floor(self, tmp_path: Path):
        assert min(cs.ARCHIVE_LADDER) == 14
        reg = self._register(tmp_path, [(10, True, 600)])
        assert cs.plan_archive(reg, reg.stat().st_size, 200_000) is None

    def test_partial_help_is_labelled_as_not_clearing(self, tmp_path: Path):
        # Mostly UNRESOLVED rows: no cutoff can get under the threshold, so the
        # plan must say so rather than promise a fix it cannot deliver.
        reg = self._register(tmp_path, [(40, True, 20), (40, False, 500)])
        plan = cs.plan_archive(reg, reg.stat().st_size, 200_000)
        assert plan is not None and plan["clears"] is False
        assert plan["after"] > 200_000

    def test_advisory_is_suppressed_when_nothing_is_archivable(self, tmp_path, capsys):
        self._register(tmp_path, [(3, True, 400), (2, False, 50)])
        assert cs.main(["--root", str(tmp_path), "pre"]) == 0
        out = capsys.readouterr().out
        assert "ADVISORY" not in out
        assert "nothing to archive this checkpoint" in out

    def test_advisory_names_the_working_cutoff(self, tmp_path, capsys):
        self._register(tmp_path, [(40, True, 300), (2, False, 100)])
        assert cs.main(["--root", str(tmp_path), "pre"]) == 0
        out = capsys.readouterr().out
        assert "ADVISORY: register exceeds 200 KB" in out
        assert "archive-register --days 30" in out
        assert "300 resolved rows" in out


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
class TestContextRootWorktree:
    """When finalize runs in a linked worktree, the gitignored context YAML
    must land in the PRIMARY clone (where /resume reads it), not the throwaway
    worktree. The committed ledgers still land in the worktree."""

    def _git(self, *args: str, cwd: Path) -> None:
        subprocess.run(["git", *args], cwd=str(cwd), check=True,
                       capture_output=True, text=True)

    def test_context_yaml_lands_in_primary_not_worktree(self, tmp_path: Path):
        primary = tmp_path / "primary"
        primary.mkdir()
        self._git("init", "-q", cwd=primary)
        self._git("config", "user.email", "t@t.t", cwd=primary)
        self._git("config", "user.name", "t", cwd=primary)
        (primary / "docs" / "sessions").mkdir(parents=True)
        (primary / "seed.txt").write_text("seed", encoding="utf-8")
        self._git("add", "-A", cwd=primary)
        self._git("commit", "-qm", "seed", cwd=primary)

        wt = tmp_path / "wt"
        self._git("worktree", "add", "-q", str(wt), "HEAD", cwd=primary)

        payload = base_payload(work_type="client-dev", projects=["brisken"], section="brisken")
        pfile = wt / "payload.json"
        pfile.write_text(json.dumps(payload), encoding="utf-8")
        # No --context-root: it must auto-detect the primary clone.
        assert cs.main(["--root", str(wt), "finalize", "--payload", str(pfile)]) == 0

        # Committed ledgers land in the worktree...
        assert (wt / "docs" / "INDEX.md").exists()
        assert (wt / "docs" / "sessions" / "2026-07-23.md").exists()
        # ...but the gitignored context YAML lands in the PRIMARY clone.
        assert (primary / "docs" / "sessions" / "2026-07-23-context.yaml").exists()
        assert not (wt / "docs" / "sessions" / "2026-07-23-context.yaml").exists()

    def test_explicit_context_root_overrides_autodetect(self, tmp_path: Path):
        primary = tmp_path / "primary"
        primary.mkdir()
        self._git("init", "-q", cwd=primary)
        self._git("config", "user.email", "t@t.t", cwd=primary)
        self._git("config", "user.name", "t", cwd=primary)
        (primary / "docs" / "sessions").mkdir(parents=True)
        self._git("commit", "-q", "--allow-empty", "-m", "seed", cwd=primary)
        wt = tmp_path / "wt"
        self._git("worktree", "add", "-q", str(wt), "HEAD", cwd=primary)
        forced = tmp_path / "forced"
        (forced / "docs" / "sessions").mkdir(parents=True)

        pfile = wt / "payload.json"
        pfile.write_text(json.dumps(base_payload()), encoding="utf-8")
        assert cs.main(
            ["--root", str(wt), "finalize", "--payload", str(pfile),
             "--context-root", str(forced)]
        ) == 0
        assert (forced / "docs" / "sessions" / "2026-07-23-context.yaml").exists()
        assert not (primary / "docs" / "sessions" / "2026-07-23-context.yaml").exists()
