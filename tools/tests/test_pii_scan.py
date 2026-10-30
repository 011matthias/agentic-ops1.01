"""tools/pii_scan.py, .claude/hooks/pii-push-gate.py and the repo-sweep wiring
(layout plan W1-14). The negative cases are the contract: ordinary checkpoints,
schema snapshots and one-line source edits stay silent. Every address and
number is built at runtime from fake parts, so no literal reaches the repo.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
HOOK = TOOLS.parent / ".claude" / "hooks" / "pii-push-gate.py"
sys.path.insert(0, str(TOOLS))
import pii_scan  # noqa: E402

CONSUMER = "gm" + "ail.com"


def addr(i: int, domain: str = CONSUMER) -> str:
    return f"piiscan-fixture-{i}-qx@{domain}"


def iban(valid: bool = True) -> str:
    # The Bundesbank's published example account, assembled at runtime.
    return "DE" + ("89" if valid else "88") + " 3704 0044 0532 0130 00"


def mobile(i: int) -> str:
    return f"+49 151 0000 {1000 + i}"


# --- detectors: positives ---------------------------------------------------

def test_three_consumer_addresses_flag():
    text = " ".join(addr(i) for i in range(3))
    assert pii_scan.scan_text("docs/x.md", text) == {"consumer": 3}


def test_one_consumer_address_repeated_eight_times_flags():
    assert pii_scan.scan_text("docs/x.md", " ".join([addr(0)] * 8)) == {"consumer": 1}


def test_twenty_business_addresses_flag():
    text = "\n".join(addr(i, "example.org") for i in range(20))
    assert pii_scan.scan_text("data/list.csv", text) == {"emails": 20}


def test_valid_iban_flags_and_bad_checksum_does_not():
    assert pii_scan.scan_text("docs/x.md", f"pay to {iban()}") == {"iban": 1}
    assert pii_scan.scan_text("docs/x.md", f"pay to {iban(valid=False)}") == {}


def test_three_german_mobiles_flag():
    text = ", ".join(mobile(i) for i in range(3))
    assert pii_scan.scan_text("docs/x.md", text) == {"phone_de": 3}


def test_json_export_with_fifty_email_values_flags():
    rows = [{"email": addr(i, "example.org").replace("@", "@x")} for i in range(50)]
    found = pii_scan.scan_text("data/export.json", json.dumps(rows))
    assert found.get("pii_keys") == 50


def test_single_line_token_file_flags_only_as_a_whole_file():
    token = "".join(chr(65 + (i * 7) % 26) + str(i % 10) for i in range(16))
    assert pii_scan.scan_text("tok.txt", token) == {"high_entropy": 1}
    assert pii_scan.scan_text("src/a.py", token, whole_file=False) == {}


def test_confidential_name_flags_in_docs_only():
    names = ["Fixturecorp Holding"]
    text = "met the fixturecorp holding treasury team"
    assert pii_scan.scan_text("docs/c.md", text, names) == {"conf_names": 1}
    assert pii_scan.scan_text("workspace/c.md", text, names) == {}


# --- detectors: negatives (the contract) ------------------------------------

def test_two_consumer_addresses_in_a_checkpoint_stay_silent():
    text = f"Sent from {addr(0)}; replied to {addr(1)} on 2026-10-28 at 14:05."
    assert pii_scan.scan_text("docs/2026-10-28 - X/Checkpoint.md", text) == {}


def test_nineteen_business_addresses_stay_silent():
    text = "\n".join(addr(i, "example.org") for i in range(19))
    assert pii_scan.scan_text("data/list.csv", text) == {}


def test_schema_snapshot_name_keys_stay_silent():
    cols = [{"name": "email", "type": "text"}, {"name": "phone", "type": "text"}] * 60
    assert pii_scan.scan_text("platform/drizzle/meta/0001_snapshot.json", json.dumps(cols)) == {}


def test_dates_amounts_and_ids_are_not_phones():
    text = "2026-10-28 EUR 0151.00, PR #1663, run 40774502174, item 0171"
    assert pii_scan.scan_text("docs/x.md", text) == {}


def test_allowlisted_paths_stay_silent():
    text = " ".join(addr(i) for i in range(5))
    for rel in ("tools/tests/t.py", "a/fixtures/f.csv", ".claude/skills/s/x.md",
                "data/leads.example.csv"):
        assert pii_scan.scan_text(rel, text) == {}, rel


def test_inline_marker_silences_a_file():
    text = "pii-allow: synthetic demo roster\n" + " ".join(addr(i) for i in range(5))
    assert pii_scan.scan_text("docs/x.md", text) == {}


def test_bare_marker_without_reason_does_not_silence():
    text = "pii-allow:\n" + " ".join(addr(i) for i in range(5))
    assert pii_scan.scan_text("docs/x.md", text) == {"consumer": 5}


# --- range scanning over a real repo ----------------------------------------

def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, encoding="utf-8").stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / "ledger.md").write_text(" ".join(addr(i) for i in range(5)) + "\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "checkout", "-q", "-b", "feat")
    return repo


def test_range_scans_added_lines_not_the_old_ledger(tmp_path):
    repo = _repo(tmp_path)
    with open(repo / "ledger.md", "a", encoding="utf-8") as f:
        f.write("one clean new row\n")
    _git(repo, "commit", "-qam", "append")
    assert pii_scan.scan_range(repo, "main...HEAD") == {}


def test_range_removing_addresses_stays_silent(tmp_path):
    """D3 deletes rosters; a push that removes personal data must not ask."""
    repo = _repo(tmp_path)
    (repo / "ledger.md").write_text("addresses moved to context/\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "scrub")
    assert pii_scan.scan_range(repo, "main...HEAD") == {}


def test_range_flags_a_new_roster(tmp_path):
    repo = _repo(tmp_path)
    (repo / "roster.csv").write_text("\n".join(addr(i) for i in range(3)), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "roster")
    assert pii_scan.scan_range(repo, "main...HEAD") == {"roster.csv": {"consumer": 3}}


def test_range_respects_a_marker_outside_the_added_lines(tmp_path):
    repo = _repo(tmp_path)
    (repo / "demo.md").write_text("pii-allow: synthetic\n\nintro\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "demo")
    with open(repo / "demo.md", "a", encoding="utf-8") as f:
        f.write(" ".join(addr(i) for i in range(4)) + "\n")
    _git(repo, "commit", "-qam", "rows")
    assert pii_scan.scan_range(repo, "HEAD~1..HEAD") == {}


def test_unresolvable_range_is_none(tmp_path):
    assert pii_scan.scan_range(_repo(tmp_path), "nope...HEAD") is None


# --- path arguments through main() --------------------------------------------

def test_directory_argument_scans_the_files_under_it(tmp_path, capsys):
    # Differential: the same roster flags whether named as a file or by its
    # folder; a folder used to read as one unreadable file and report 0.
    repo = _repo(tmp_path)
    (repo / "docs" / "site").mkdir(parents=True)
    roster = repo / "docs" / "site" / "roster.csv"
    roster.write_text("\n".join(addr(i) for i in range(3)), encoding="utf-8")
    assert pii_scan.main(["--repo", str(repo), str(roster)]) == 1
    assert pii_scan.main(["--repo", str(repo), str(repo / "docs")]) == 1
    assert "docs/site/roster.csv: consumer=3" in capsys.readouterr().out
    roster.write_text("no addresses here\n", encoding="utf-8")
    assert pii_scan.main(["--repo", str(repo), str(repo / "docs")]) == 0


def test_missing_path_refuses_instead_of_reporting_clean(tmp_path, capsys):
    repo = _repo(tmp_path)
    assert pii_scan.main(["--repo", str(repo), str(repo / "no-such-dir")]) == 2
    assert "no such path" in capsys.readouterr().err


# --- the push gate, end to end ----------------------------------------------

def _gate(repo: Path, command: str, **env) -> str:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    out = subprocess.run([sys.executable, str(HOOK)], input=payload, cwd=repo,
                         capture_output=True, encoding="utf-8", timeout=60,
                         env={**os.environ, **env})
    return out.stdout


def test_gate_asks_on_a_push_adding_a_roster_with_counts_not_values(tmp_path):
    repo = _repo(tmp_path)
    (repo / "roster.csv").write_text("\n".join(addr(i) for i in range(3)), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "roster")
    out = _gate(repo, "git push -u origin feat")
    decision = json.loads(out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "ask"
    assert "roster.csv: consumer=3" in decision["permissionDecisionReason"]
    assert "@" not in decision["permissionDecisionReason"]


def test_gate_silent_on_an_ordinary_push(tmp_path):
    repo = _repo(tmp_path)
    (repo / "notes.md").write_text(f"Checkpoint. Reply from {addr(0)}.\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "notes")
    assert _gate(repo, "git push -u origin feat") == ""


def test_gate_ignores_other_commands_and_honours_the_override(tmp_path):
    repo = _repo(tmp_path)
    (repo / "roster.csv").write_text("\n".join(addr(i) for i in range(3)), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "roster")
    assert _gate(repo, "git status") == ""
    assert _gate(repo, "git push", PII_PUSH_GATE_ALLOW="1") == ""


def test_gate_fails_open_outside_a_repo(tmp_path):
    assert _gate(tmp_path, "git push") == ""


# --- repo-sweep wiring --------------------------------------------------------

def _sweep():
    spec = importlib.util.spec_from_file_location("repo_sweep_pii", TOOLS / "repo-sweep.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sweep_plan_skips_an_untracked_roster(tmp_path):
    sweep = _sweep()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "roster.md").write_text(" ".join(addr(i) for i in range(3)),
                                                 encoding="utf-8")
    (tmp_path / "docs" / "notes.md").write_text("plain notes\n", encoding="utf-8")
    groups, skipped = sweep.plan(str(tmp_path), [("??", "docs/roster.md"), ("??", "docs/notes.md")])
    assert skipped == ["docs/roster.md (personal data: consumer=3)"]
    assert [p for paths in groups.values() for p in paths] == ["docs/notes.md"]
