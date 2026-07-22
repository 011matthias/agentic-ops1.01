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
    # Keep tests hermetic: repoint the projects root too, or the sweep would
    # scan the REAL workspace/projects tree from inside a tmp-dir test.
    monkeypatch.setattr(ps, "PROJECTS_DIR", tmp_path / "workspace" / "projects")
    return clients


def _project_tree(tmp_path):
    projects = tmp_path / "workspace" / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    return projects


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


# --- sweep-stale (the SessionStart auto-surface) ---------------------------

def _seed(clients, client, name, updated, state="active"):
    d = clients / client / "status"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(
        f"---\nproject: {client}\nworkstream: w\nstate: {state}\nupdated: {updated}\n---\n",
        encoding="utf-8")


def test_sweep_finds_stale_across_clients(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    _seed(clients, "brisken", "p2-rome.md", "2026-04-01")      # stale
    _seed(clients, "brisken", "p1.md", "2026-06-19")           # fresh
    _seed(clients, "meji", "a0.md", "2026-06-18")              # fresh, other client
    (clients / "wimmer").mkdir(parents=True)                   # no status/ -> skipped
    findings = ps.sweep_stale(TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert [(f["client"], f["file"]) for f in findings] == [("brisken", "p2-rome.md")]


def test_sweep_empty_when_all_fresh(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    _seed(clients, "brisken", "p2-rome.md", "2026-06-19")
    assert ps.sweep_stale(TODAY, ps.DEFAULT_MAX_AGE_DAYS) == []


def test_sweep_catches_malformed(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    d = clients / "brisken" / "status"
    d.mkdir(parents=True)
    (d / "bad.md").write_text("---\nproject: brisken\n---\n", encoding="utf-8")  # missing keys
    findings = ps.sweep_stale(TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert len(findings) == 1 and findings[0]["problems"]


def test_sweep_no_clients_dir_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "CLIENTS_DIR", tmp_path / "nope")
    monkeypatch.setattr(ps, "PROJECTS_DIR", tmp_path / "also-nope")
    assert ps.sweep_stale(TODAY, ps.DEFAULT_MAX_AGE_DAYS) == []


# --- projects root (workspace/projects, added 2026-07-22 for uwi) -----------

def test_check_resolves_a_project_slug(tmp_path, monkeypatch):
    _client_tree(tmp_path, monkeypatch)
    projects = _project_tree(tmp_path)
    d = projects / "upwork-independence" / "status"
    d.mkdir(parents=True)
    (d / "u1-cold-email-infra.md").write_text(
        "---\nproject: upwork-independence\nworkstream: u1\nstate: active\nupdated: 2026-06-19\n---\n",
        encoding="utf-8")
    rows, code = ps.check("upwork-independence", TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert code == 0
    assert [r["file"] for r in rows] == ["u1-cold-email-infra.md"]


def test_sweep_covers_the_projects_root(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    projects = _project_tree(tmp_path)
    _seed(clients, "brisken", "p2-rome.md", "2026-06-19")          # fresh client
    d = projects / "upwork-independence" / "status"
    d.mkdir(parents=True)
    (d / "u2-aeo-content.md").write_text(
        "---\nproject: upwork-independence\nworkstream: u2\nstate: active\nupdated: 2026-04-01\n---\n",
        encoding="utf-8")                                          # stale project
    monkeypatch.setattr(ps, "_fresher_on_origin", lambda p, u: False)
    findings = ps.sweep_stale(TODAY, ps.DEFAULT_MAX_AGE_DAYS)
    assert [(f["client"], f["file"]) for f in findings] == \
        [("upwork-independence", "u2-aeo-content.md")]


def test_client_shadows_project_on_slug_collision(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    projects = _project_tree(tmp_path)
    (clients / "twin" / "status").mkdir(parents=True)
    (projects / "twin" / "status").mkdir(parents=True)
    assert ps.slug_dir("twin") == clients / "twin"


def test_scaffold_into_a_project(tmp_path, monkeypatch):
    _client_tree(tmp_path, monkeypatch)
    projects = _project_tree(tmp_path)
    (projects / "upwork-independence").mkdir(parents=True, exist_ok=True)
    dest = ps.scaffold("upwork-independence", "u3-linkedin-outbound", today=TODAY)
    assert dest == projects / "upwork-independence" / "status" / "u3-linkedin-outbound.md"
    assert dest.exists()


def test_scaffold_unknown_slug_names_both_roots(tmp_path, monkeypatch):
    _client_tree(tmp_path, monkeypatch)
    try:
        ps.scaffold("ghost", "w", today=TODAY)
    except SystemExit as e:
        assert "no client or project folder" in str(e)
    else:
        raise AssertionError("expected SystemExit for unknown slug")


def test_main_sweep_always_exit0(tmp_path, monkeypatch, capsys):
    clients = _client_tree(tmp_path, monkeypatch)
    monkeypatch.setattr(ps, "_SWEEP_STAMP", tmp_path / "stamp.json")
    _seed(clients, "brisken", "p2-rome.md", "2026-04-01")  # stale -> findings printed
    assert ps.main(["--sweep-stale"]) == 0
    assert "stale" in capsys.readouterr().out


def test_once_per_day_stamp(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "_SWEEP_STAMP", tmp_path / "stamp.json")
    assert ps._already_swept_today(TODAY) is False   # no stamp yet
    ps._mark_swept_today(TODAY)
    assert ps._already_swept_today(TODAY) is True     # stamped today
    assert ps._already_swept_today(dt.date(2026, 6, 22)) is False  # different day


def test_once_per_day_skips_second_run(tmp_path, monkeypatch, capsys):
    clients = _client_tree(tmp_path, monkeypatch)
    monkeypatch.setattr(ps, "_SWEEP_STAMP", tmp_path / "stamp.json")
    _seed(clients, "brisken", "p2-rome.md", "2026-04-01")  # stale
    ps.main(["--sweep-stale", "--once-per-day"])
    first = capsys.readouterr().out
    ps.main(["--sweep-stale", "--once-per-day"])           # same day -> skipped
    second = capsys.readouterr().out
    assert "stale" in first and second == ""


# --- sweep vs a checkout behind origin/main --------------------------------

def _stale_tree(tmp_path, monkeypatch):
    clients = _client_tree(tmp_path, monkeypatch)
    d = clients / "brisken" / "status"
    d.mkdir(parents=True)
    (d / "p2-rome.md").write_text(
        "---\nproject: brisken\nworkstream: rome\nstate: active\n"
        "updated: 2026-04-01\n---\n", encoding="utf-8")
    return d / "p2-rome.md"


def test_sweep_flags_a_genuinely_stale_file(tmp_path, monkeypatch):
    _stale_tree(tmp_path, monkeypatch)
    monkeypatch.setattr(ps, "_fresher_on_origin", lambda p, u: False)
    assert [f["file"] for f in ps.sweep_stale(TODAY)] == ["p2-rome.md"]


def test_sweep_suppresses_a_file_already_refreshed_on_origin(tmp_path, monkeypatch):
    """The sweep reads the WORKING TREE, so a checkout behind origin/main
    nags about files somebody already updated.

    Same defect class as the optimize overview's STALE CHECKOUT blind spot,
    but here it produces false positives, which is worse for an advisory: it
    trains the reader to ignore the line.
    """
    _stale_tree(tmp_path, monkeypatch)
    monkeypatch.setattr(ps, "_fresher_on_origin", lambda p, u: True)
    assert ps.sweep_stale(TODAY) == []


def test_sweep_still_reports_malformed_files_even_if_origin_is_newer(tmp_path, monkeypatch):
    """Suppression is scoped to STALENESS only.

    A malformed file is malformed in this checkout regardless of what
    origin/main holds, and hiding it would be a real miss rather than a
    spared false alarm.
    """
    clients = _client_tree(tmp_path, monkeypatch)
    d = clients / "brisken" / "status"
    d.mkdir(parents=True)
    (d / "broken.md").write_text(
        "---\nproject: brisken\nstate: nonsense\nupdated: 2026-04-01\n---\n",
        encoding="utf-8")
    monkeypatch.setattr(ps, "_fresher_on_origin", lambda p, u: True)
    findings = ps.sweep_stale(TODAY)
    assert [f["file"] for f in findings] == ["broken.md"]
    assert findings[0]["problems"]


def test_fresher_on_origin_fails_open_outside_a_repo(tmp_path):
    """Any git problem must mean 'cannot tell' and report as normal.

    Suppressing on a guess would hide real rot; this path is reached on every
    SessionStart, so it has to be the safe direction.
    """
    p = tmp_path / "p2-rome.md"
    p.write_text("---\nupdated: 2026-04-01\n---\n", encoding="utf-8")
    assert ps._fresher_on_origin(p, "2026-04-01") is False


def test_fresher_on_origin_needs_a_local_date(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("---\n---\n", encoding="utf-8")
    assert ps._fresher_on_origin(p, None) is False
