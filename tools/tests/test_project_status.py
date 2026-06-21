"""project_status.py: per-project status-file scaffold + staleness checks.

Drives the pure functions (parse_frontmatter, compute_age_days, evaluate_file)
on synthetic content with a pinned "today", and exercises scaffold/check against
a temp clients tree by repointing the module's CLIENTS_DIR. Loaded via importlib
to mirror test_check_index.py / test_anneal_metrics.py.
"""
import datetime as dt
import importlib.util

from hooklib import TOOLS

SCRIPT = TOOLS / "project_status.py"


def _load():
    spec = importlib.util.spec_from_file_location("project_status", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ps = _load()
TODAY = dt.date(2026, 6, 20)


# --- parse_frontmatter -----------------------------------------------------

def test_parse_frontmatter_valid():
    fm = ps.parse_frontmatter("---\nproject: brisken\nstate: active\n---\n\nbody")
    assert fm == {"project": "brisken", "state": "active"}


def test_parse_frontmatter_absent():
    assert ps.parse_frontmatter("# no frontmatter here") == {}


def test_parse_frontmatter_malformed_returns_empty():
    assert ps.parse_frontmatter("---\n: : bad: yaml: [\n---\n") == {}


# --- compute_age_days ------------------------------------------------------

def test_age_from_date_object():
    assert ps.compute_age_days(dt.date(2026, 6, 10), TODAY) == 10


def test_age_from_string():
    assert ps.compute_age_days("2026-06-13", TODAY) == 7


def test_age_from_datetime():
    assert ps.compute_age_days(dt.datetime(2026, 6, 18, 9, 0), TODAY) == 2


def test_age_unparseable_is_none():
    assert ps.compute_age_days("recently", TODAY) is None
    assert ps.compute_age_days(None, TODAY) is None


# --- evaluate_file ---------------------------------------------------------

def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_evaluate_fresh_active_clean(tmp_path):
    p = _write(tmp_path, "p2-rome.md",
               "---\nproject: brisken\nworkstream: rome\nstate: active\nupdated: 2026-06-18\n---\n")
    r = ps.evaluate_file(p, TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert r["problems"] == []
    assert r["stale"] is False
    assert r["state"] == "active"
    assert r["age_days"] == 2


def test_evaluate_stale_active_flags(tmp_path):
    p = _write(tmp_path, "p2-rome.md",
               "---\nproject: brisken\nworkstream: rome\nstate: active\nupdated: 2026-05-01\n---\n")
    r = ps.evaluate_file(p, TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert r["stale"] is True
    assert r["problems"] == []


def test_evaluate_done_old_not_stale(tmp_path):
    # done/paused/dormant don't need a heartbeat.
    p = _write(tmp_path, "p1.md",
               "---\nproject: brisken\nworkstream: x\nstate: done\nupdated: 2026-01-01\n---\n")
    r = ps.evaluate_file(p, TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert r["stale"] is False


def test_evaluate_missing_keys(tmp_path):
    p = _write(tmp_path, "bad.md", "---\nproject: brisken\n---\n")
    r = ps.evaluate_file(p, TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert any("missing keys" in pr for pr in r["problems"])


def test_evaluate_unknown_state(tmp_path):
    p = _write(tmp_path, "bad.md",
               "---\nproject: b\nworkstream: w\nstate: wibble\nupdated: 2026-06-19\n---\n")
    r = ps.evaluate_file(p, TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert any("unknown state" in pr for pr in r["problems"])


def test_evaluate_unparseable_date_is_problem(tmp_path):
    p = _write(tmp_path, "bad.md",
               "---\nproject: b\nworkstream: w\nstate: active\nupdated: soon\n---\n")
    r = ps.evaluate_file(p, TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert any("unparseable" in pr for pr in r["problems"])


# --- check (against a temp clients tree) -----------------------------------

def _client_tree(tmp_path, monkeypatch):
    clients = tmp_path / "workspace" / "clients"
    monkeypatch.setattr(ps, "CLIENTS_DIR", clients)
    return clients


def test_check_no_folder_exit3(tmp_path, monkeypatch):
    _client_tree(tmp_path, monkeypatch)
    rows, code = ps.check("ghost", TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert code == 3 and rows == []


def test_check_all_good_exit0(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    d = clients / "brisken" / "status"
    d.mkdir(parents=True)
    (d / "p2-rome.md").write_text(
        "---\nproject: brisken\nworkstream: rome\nstate: active\nupdated: 2026-06-19\n---\n",
        encoding="utf-8")
    (d / "README.md").write_text("ignored", encoding="utf-8")  # README excluded
    rows, code = ps.check("brisken", TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert code == 0
    assert [r["file"] for r in rows] == ["p2-rome.md"]


def test_check_stale_exit1(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    d = clients / "brisken" / "status"
    d.mkdir(parents=True)
    (d / "p2-rome.md").write_text(
        "---\nproject: brisken\nworkstream: rome\nstate: active\nupdated: 2026-04-01\n---\n",
        encoding="utf-8")
    _, code = ps.check("brisken", TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert code == 1


# --- scaffold --------------------------------------------------------------

def test_scaffold_writes_file(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    (clients / "brisken").mkdir(parents=True)
    dest = ps.scaffold("brisken", "p2-rome", group="lead-generation", spec="p2",
                       today=TODAY, general_ref="status/p2-lead-gen-general.md")
    assert dest.exists()
    text = dest.read_text(encoding="utf-8")
    fm = ps.parse_frontmatter(text)
    assert fm["workstream"] == "p2-rome"
    assert fm["group"] == "lead-generation"
    assert "general_ref: status/p2-lead-gen-general.md" in text
    # a freshly scaffolded file is clean and not stale
    r = ps.evaluate_file(dest, TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert r["problems"] == [] and r["stale"] is False


def test_scaffold_omits_general_ref_when_absent(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    (clients / "brisken").mkdir(parents=True)
    dest = ps.scaffold("brisken", "p1-expense", today=TODAY)
    assert "general_ref:" not in dest.read_text(encoding="utf-8")


def test_scaffold_refuses_overwrite(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    (clients / "brisken").mkdir(parents=True)
    ps.scaffold("brisken", "p2-rome", today=TODAY)
    try:
        ps.scaffold("brisken", "p2-rome", today=TODAY)
    except SystemExit as e:
        assert "refusing to overwrite" in str(e)
    else:
        raise AssertionError("expected SystemExit on overwrite")
