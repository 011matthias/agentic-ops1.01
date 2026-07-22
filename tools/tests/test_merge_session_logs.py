"""Tests for tools/merge-session-logs.py (session-log fan-out fold).

Pins the load-bearing behaviors: shard discovery never swallows the plain
daily file or the *-context.yaml sibling, folds are delimited + mtime-ordered
+ hash-idempotent, shards are deleted only on apply, and dry-run touches
nothing.
"""
import importlib.util
import os
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "merge_session_logs", TOOLS / "merge-session-logs.py")
msl = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = msl  # dataclass field resolution needs the registry
spec.loader.exec_module(msl)


SHARD_A = """---
date: 2020-01-01
sessions: 1
projects_touched: [brisken]
friction_events: 2
work_types: [client-dev]
---

### Session 1 — Alpha Work
**Type:** client-dev
**Friction:** 2 — things
**Outcome:** shipped
"""

SHARD_B = """---
date: 2020-01-01
sessions: 1
projects_touched: [upwork-independence]
friction_events: 0
work_types: [misc]
---

### Session 1 — Beta Work
**Type:** misc
**Friction:** None
**Outcome:** wrapped
"""


def _write(dirpath: Path, name: str, text: str, mtime: float | None = None) -> Path:
    p = dirpath / name
    p.write_text(text, encoding="utf-8", newline="\n")
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


def test_discovery_excludes_plain_daily_context_and_nondates(tmp_path):
    _write(tmp_path, "2020-01-01.md", "canonical")
    _write(tmp_path, "2020-01-01-abc12345.md", SHARD_A)
    _write(tmp_path, "2020-01-01-context.yaml", "yaml: true")
    _write(tmp_path, "2020-01-01-context.md", "reserved suffix")
    _write(tmp_path, "2020-01-01-2020-01-02.md", "date-shaped suffix")
    _write(tmp_path, "2020-01-02-fix.md", SHARD_B)
    _write(tmp_path, "README.md", "not a shard")
    by_date = msl.discover_shards(tmp_path)
    assert set(by_date) == {"2020-01-01", "2020-01-02"}
    assert [p.name for p in by_date["2020-01-01"]] == ["2020-01-01-abc12345.md"]
    assert [p.name for p in by_date["2020-01-02"]] == ["2020-01-02-fix.md"]


def test_fold_appends_delimited_blocks_in_mtime_order(tmp_path):
    # B written FIRST (older mtime) so mtime order beats name order
    _write(tmp_path, "2020-01-01-zzz99999.md", SHARD_B, mtime=1_000_000)
    _write(tmp_path, "2020-01-01-abc12345.md", SHARD_A, mtime=2_000_000)
    results = msl.run_fold(tmp_path, apply=True)
    assert len(results) == 1 and results[0].error is None
    assert results[0].folded == ["2020-01-01-zzz99999.md", "2020-01-01-abc12345.md"]
    text = (tmp_path / "2020-01-01.md").read_text(encoding="utf-8")
    assert "<!-- folded: 2020-01-01-zzz99999.md sha256:" in text
    assert "<!-- folded: 2020-01-01-abc12345.md sha256:" in text
    assert text.index("Beta Work") < text.index("Alpha Work")  # mtime order
    # shard bodies verbatim, shard frontmatter NOT copied into the body
    assert text.count("---") == 2  # only the canonical frontmatter fences
    assert "**Outcome:** shipped" in text and "**Outcome:** wrapped" in text


def test_fold_creates_canonical_with_frontmatter_and_counters(tmp_path):
    _write(tmp_path, "2020-01-01-abc12345.md", SHARD_A, mtime=1_000_000)
    _write(tmp_path, "2020-01-01-def67890.md", SHARD_B, mtime=2_000_000)
    msl.run_fold(tmp_path, apply=True)
    text = (tmp_path / "2020-01-01.md").read_text(encoding="utf-8")
    assert text.startswith("---\ndate: 2020-01-01\n")
    assert "sessions: 2" in text          # counted from ### Session headings
    assert "friction_events: 2" in text   # 2 + None
    assert "projects_touched: [brisken, upwork-independence]" in text
    assert "work_types: [client-dev, misc]" in text


def test_idempotent_second_apply_changes_nothing(tmp_path):
    _write(tmp_path, "2020-01-01-abc12345.md", SHARD_A)
    msl.run_fold(tmp_path, apply=True)
    first = (tmp_path / "2020-01-01.md").read_text(encoding="utf-8")
    # same content re-appearing as a shard (crashed delete, resurrected file)
    _write(tmp_path, "2020-01-01-abc12345.md", SHARD_A)
    results = msl.run_fold(tmp_path, apply=True)
    assert results[0].folded == []
    assert results[0].redundant == ["2020-01-01-abc12345.md"]
    assert (tmp_path / "2020-01-01.md").read_text(encoding="utf-8") == first
    assert not (tmp_path / "2020-01-01-abc12345.md").exists()  # still cleaned up


def test_same_name_new_content_folds_again(tmp_path):
    _write(tmp_path, "2020-01-01-abc12345.md", SHARD_A)
    msl.run_fold(tmp_path, apply=True)
    # the same session checkpoints again after the fold: same name, new content
    _write(tmp_path, "2020-01-01-abc12345.md", SHARD_B)
    results = msl.run_fold(tmp_path, apply=True)
    assert results[0].folded == ["2020-01-01-abc12345.md"]
    text = (tmp_path / "2020-01-01.md").read_text(encoding="utf-8")
    assert "Alpha Work" in text and "Beta Work" in text


def test_shards_deleted_on_apply(tmp_path):
    _write(tmp_path, "2020-01-01-abc12345.md", SHARD_A)
    results = msl.run_fold(tmp_path, apply=True)
    assert results[0].deleted == ["2020-01-01-abc12345.md"]
    assert not (tmp_path / "2020-01-01-abc12345.md").exists()
    assert (tmp_path / "2020-01-01.md").exists()


def test_dry_run_touches_nothing(tmp_path):
    shard = _write(tmp_path, "2020-01-01-abc12345.md", SHARD_A)
    results = msl.run_fold(tmp_path, apply=False)
    assert results[0].folded == ["2020-01-01-abc12345.md"]  # reported
    assert results[0].deleted == []
    assert shard.exists()
    assert not (tmp_path / "2020-01-01.md").exists()


def test_fold_appends_to_existing_canonical(tmp_path):
    existing = ("---\ndate: 2020-01-01\nsessions: 1\n"
                "projects_touched: [meji-media]\nfriction_events: 1\n"
                "work_types: [comms]\n---\n\n"
                "### Session 1 — Pre-existing\n**Friction:** 1 — thing\n")
    _write(tmp_path, "2020-01-01.md", existing)
    _write(tmp_path, "2020-01-01-abc12345.md", SHARD_A)
    msl.run_fold(tmp_path, apply=True)
    text = (tmp_path / "2020-01-01.md").read_text(encoding="utf-8")
    assert "Pre-existing" in text and "Alpha Work" in text
    assert "sessions: 2" in text
    assert "friction_events: 3" in text  # 1 existing + 2 shard
    assert "projects_touched: [meji-media, brisken]" in text


def test_date_filter_folds_only_that_date(tmp_path):
    _write(tmp_path, "2020-01-01-abc12345.md", SHARD_A)
    _write(tmp_path, "2020-01-02-def67890.md", SHARD_B)
    results = msl.run_fold(tmp_path, date="2020-01-01", apply=True)
    assert [r.date for r in results] == ["2020-01-01"]
    assert (tmp_path / "2020-01-02-def67890.md").exists()  # untouched


def test_empty_shard_is_redundant_and_deleted_on_apply(tmp_path):
    _write(tmp_path, "2020-01-01-abc12345.md", "---\ndate: 2020-01-01\n---\n\n\n")
    results = msl.run_fold(tmp_path, apply=True)
    assert results[0].folded == []
    assert results[0].redundant == ["2020-01-01-abc12345.md"]
    assert not (tmp_path / "2020-01-01-abc12345.md").exists()
    assert not (tmp_path / "2020-01-01.md").exists()  # nothing to write


def test_missing_sessions_dir_is_noop(tmp_path):
    assert msl.run_fold(tmp_path / "nope", apply=True) == []
