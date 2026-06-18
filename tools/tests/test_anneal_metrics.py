"""anneal-metrics.py: convergence + toolkit-drift measurement for /comd_system-dev.

Drives the pure functions against synthetic temp repos (so asset counts / drift /
delta arithmetic are pinned), plus a --format json contract check via subprocess
and a live-tree smoke that the real repo computes without error. Loaded via
importlib (the script is hyphenated, not importable by name) — mirrors
test_check_index.py / hooklib.load_wire_hooks.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "anneal-metrics.py"


def _load():
    spec = importlib.util.spec_from_file_location("anneal_metrics", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AM = _load()


def _make_repo(tmp: Path, *, cmds=2, skil=2, vendored=1, agents=1, tools=2,
               rules=1, rule_lines=10, claude_md=None, register_rows=None,
               ledger_rows=None) -> Path:
    """Build a minimal repo tree the metrics functions can census."""
    (tmp / ".claude" / "commands").mkdir(parents=True)
    for i in range(cmds):
        (tmp / ".claude" / "commands" / f"comd_c{i}.md").write_text("x", encoding="utf-8")
    sk = tmp / ".claude" / "skills"
    sk.mkdir(parents=True)
    for i in range(skil):
        (sk / f"skil_s{i}").mkdir()
        (sk / f"skil_s{i}" / "SKILL.md").write_text("x", encoding="utf-8")
    for i in range(vendored):
        (sk / f"vendored{i}").mkdir()
        (sk / f"vendored{i}" / "SKILL.md").write_text("x", encoding="utf-8")
    (tmp / ".claude" / "agents").mkdir(parents=True)
    for i in range(agents):
        (tmp / ".claude" / "agents" / f"a{i}.md").write_text("x", encoding="utf-8")
    (tmp / "tools").mkdir(parents=True)
    for i in range(tools):
        (tmp / "tools" / f"t{i}.py").write_text("x", encoding="utf-8")
    (tmp / ".claude" / "rules").mkdir(parents=True)
    for i in range(rules):
        (tmp / ".claude" / "rules" / f"rule_r{i}.md").write_text(
            "\n".join(["line"] * rule_lines), encoding="utf-8")
    if claude_md is not None:
        (tmp / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    (tmp / "docs").mkdir(parents=True)
    if register_rows is not None:
        header = ("# Friction Register\n\n| Date | Client | Type | Description | Resolved? | Fix |\n"
                  "|---|---|---|---|---|---|\n")
        (tmp / "docs" / "friction-register.md").write_text(header + register_rows, encoding="utf-8")
    if ledger_rows is not None:
        head = ("# Anneal Ledger\n\n| " + " | ".join(AM.LEDGER_COLUMNS) + " |\n"
                "|" + "|".join(["---"] * len(AM.LEDGER_COLUMNS)) + "|\n")
        (tmp / "docs" / "anneal-ledger.md").write_text(head + ledger_rows, encoding="utf-8")
    return tmp


def test_asset_counts_on_temp_tree(tmp_path):
    _make_repo(tmp_path, cmds=3, skil=2, vendored=2, agents=1, tools=4, rules=2, rule_lines=7)
    a = AM.count_assets(tmp_path)
    assert a["cmds"] == 3
    assert a["skills_skil"] == 2 and a["skills_total"] == 4   # 2 skil_ + 2 vendored
    assert a["agents"] == 1 and a["tools"] == 4 and a["rules"] == 2
    assert a["rules_loc"] == 14   # 2 files x 7 lines
    assert a["rules_oversized"] == []   # 7 lines each, under the per-file ceiling


def test_parse_reuses_friction_watch(tmp_path):
    rows = ("| 2026-06-01 | meji | agent-deferred | did a thing | No | memory |\n"
            "| 2026-06-02 | brisken | slow-path | another thing | Yes | structural |\n"
            "| 2026-06-03 | system | agent-deferred | did a thing | Partially |  |\n")
    _make_repo(tmp_path, register_rows=rows, claude_md="x")
    m = AM.build_metrics(tmp_path, "2026-06-18")
    # totals match the canonical friction-watch parser
    fw = AM._load_friction_watch()
    parsed = fw.parse_register((tmp_path / "docs" / "friction-register.md").read_text(encoding="utf-8"))
    assert m["register"]["total_rows"] == len(parsed) == 3
    assert m["register"]["unresolved"] == 2          # No + Partially
    assert m["memory_fix_pct"] == round(100 * 1 / 3, 1)


def test_drift_detection(tmp_path):
    # CLAUDE.md advertises counts that don't match the tree -> drift.
    claude = ("# Repo\n## Primitives\n"
              "- **Commands** (99) wrong\n- **Skills** (5) wrong\n"
              "- **Agents** (1) right\n- **Rules** (1) right\n")
    _make_repo(tmp_path, cmds=2, skil=2, vendored=0, agents=1, tools=1,
               rules=1, rule_lines=5, claude_md=claude)
    a = AM.count_assets(tmp_path)
    drift = AM.compute_drift(tmp_path, a)
    blob = " ".join(drift)
    assert "Commands" in blob and "advertises 99" in blob
    assert "Skills" in blob and "advertises 5" in blob
    assert "Agents" not in blob and "Rules" not in blob   # those matched
    # small rules-LOC -> no budget drift
    assert not any("budget" in d for d in drift)


def test_oversized_rule_is_advisory_not_drift(tmp_path):
    # A rule file over the per-file ceiling is surfaced as an advisory in the
    # assets census, NOT as documented-vs-actual drift (the repo-wide LOC budget
    # was retired 2026-06-18).
    _make_repo(tmp_path, rules=1, rule_lines=AM.PER_FILE_RULE_CEILING + 50, claude_md="x")
    a = AM.count_assets(tmp_path)
    assert any(loc > AM.PER_FILE_RULE_CEILING for _, loc in a["rules_oversized"])
    drift = AM.compute_drift(tmp_path, a)
    assert not any("budget" in d.lower() or "ceiling" in d.lower() for d in drift)


def test_net_delta_against_prior_ledger_row(tmp_path):
    # current tree total = 2 cmds + 2 skil + 1 agent + 2 tools + 1 rule = 8
    prior = "| 2026-06-01 | 1 | 1/1 | 1 | 1 | 1/10 | 5 | 1 | 0 | 0 | 0 | - | 9 | - | x |\n"
    _make_repo(tmp_path, cmds=2, skil=2, vendored=0, agents=1, tools=2, rules=1,
               claude_md="x", register_rows="", ledger_rows=prior)
    m = AM.build_metrics(tmp_path, "2026-06-18")
    assert m["asset_total"] == 8
    assert m["net_asset_delta"] == 8 - 5   # prior total 1+1+1+1+1
    assert m["prior_cycle_date"] == "2026-06-01"
    # no git in the temp dir -> changeset/smaller are unknown, not fabricated
    assert m["changeset_size"] is None and m["smaller_than_last"] is None


def test_json_contract(tmp_path):
    _make_repo(tmp_path, claude_md="x", register_rows="")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--format", "json", "--repo", str(tmp_path)],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    m = json.loads(proc.stdout)
    for k in ("date", "assets", "asset_total", "register", "recurrence_pct",
              "memory_fix_pct", "drift", "changeset_size", "net_asset_delta",
              "smaller_than_last"):
        assert k in m, f"missing key {k}"


def test_to_row_shape(tmp_path):
    _make_repo(tmp_path, claude_md="x", register_rows="")
    m = AM.build_metrics(tmp_path, "2026-06-18")
    row = AM.to_row(m)
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    assert len(cells) == len(AM.LEDGER_COLUMNS)
    assert cells[0] == "2026-06-18"
    assert cells[-1] == "?"   # Top Finding placeholder


def test_live_tree_runs():
    # The real repo must compute cleanly. Does NOT assert drift>0: drift SHOULD
    # fall to zero as the toolkit is annealed — locking it positive would break
    # at the moment the system actually converges.
    m = AM.build_metrics(REPO, "2026-06-18")
    assert m["asset_total"] > 0
    assert m["register"]["total_rows"] > 0
    assert isinstance(m["drift"], list)
