"""zoho-post CLI gate tests — every deny-by-default path (BLUEPRINT 4.8).

The property under test: NO combination of flags, config, and env short
of `enabled:true` + `EXPENSE_RECON_ZOHO_POST=1` + allowlisted org +
`--go` + a clean plan can make the CLI post anything. Client is a
scripted fake injected via `zoho_post_cli._make_client`."""
from __future__ import annotations

import csv
import json

import pytest

from expense_recon import zoho_post_cli
from expense_recon.cli import main as cli_main
from expense_recon.output.zoho_export import ZOHO_COLUMNS
from expense_recon.zoho.idempotent import PostLedger
from expense_recon.zoho_post_cli import POST_ENV, main

ORG = "822741658"


class FakeClient:
    def __init__(self, results=(), journals=()):
        self._results = list(results)
        self._journals = list(journals)
        self.posted_payloads: list[dict] = []

    def create_journal(self, payload):
        self.posted_payloads.append(payload)
        return self._results.pop(0)

    def list_journals(self, **kwargs):
        return list(self._journals)


def _chart_file(tmp_path, org=ORG):
    chart = {org: {"org": {"name": "Corporate Services"}, "accounts": [
        {"account_id": "111", "account_name": "Travel: Flights",
         "account_code": "6000", "account_type": "expense",
         "parent_account_name": None, "is_active": True},
        {"account_id": "222", "account_name": "Amex Card", "account_code": "A200",
         "account_type": "credit_card", "parent_account_name": None,
         "is_active": True},
    ]}}
    path = tmp_path / "coa.json"
    path.write_text(json.dumps(chart), encoding="utf-8")
    return path


def _config_file(tmp_path, *, enabled=True, org=ORG, ledger="ledger.sqlite",
                 extra_post=None):
    post = {"enabled": enabled, "ledger_path": ledger}
    post.update(extra_post or {})
    cfg = {
        "zoho": {"post": post},
        "coa_validation": {"chart_path": "coa.json", "org_id": org},
    }
    path = tmp_path / "run.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


def _csv_file(tmp_path, rows, name="zoho-journal.csv"):
    path = tmp_path / name
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(ZOHO_COLUMNS)
        writer.writerows(rows)
    return path


def _rows(ref="t1", amount="180.00", debit_acct="Travel: Flights"):
    return [
        ["2026-04-03", debit_acct, "flight", ref, "", amount, "", "", ""],
        ["2026-04-03", "Amex Card", "Payment to X", ref, "", "", amount, "", ""],
    ]


def _no_client(monkeypatch):
    def boom(org_id):
        raise AssertionError("client must not be constructed on this path")
    monkeypatch.setattr(zoho_post_cli, "_make_client", boom)


@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    monkeypatch.delenv(POST_ENV, raising=False)
    _chart_file(tmp_path)
    return tmp_path


def test_dry_run_prints_plan_and_posts_nothing(workdir, monkeypatch, capsys):
    _no_client(monkeypatch)
    cfg = _config_file(workdir)
    csv_path = _csv_file(workdir, _rows())
    assert main(["--config", str(cfg), "--csv", str(csv_path)]) == 0
    out = capsys.readouterr().out
    assert "TO POST: 1" in out and "t1" in out
    assert "Would REFUSE --go" in out  # env not set: dry run reports it
    assert not (workdir / "ledger.sqlite").exists()  # dry run creates nothing


def test_go_refused_without_env(workdir, monkeypatch, capsys):
    _no_client(monkeypatch)
    cfg = _config_file(workdir)
    csv_path = _csv_file(workdir, _rows())
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 2
    assert POST_ENV in capsys.readouterr().err
    assert not (workdir / "ledger.sqlite").exists()


def test_go_refused_when_config_disabled(workdir, monkeypatch, capsys):
    _no_client(monkeypatch)
    monkeypatch.setenv(POST_ENV, "1")
    cfg = _config_file(workdir, enabled=False)
    csv_path = _csv_file(workdir, _rows())
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 2
    assert "zoho.post.enabled" in capsys.readouterr().err


def test_go_refused_for_non_allowlisted_org(tmp_path, monkeypatch, capsys):
    _no_client(monkeypatch)
    monkeypatch.setenv(POST_ENV, "1")
    _chart_file(tmp_path, org="999000111")
    cfg = _config_file(tmp_path, org="999000111")
    csv_path = _csv_file(tmp_path, _rows())
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 2
    assert "allowlist" in capsys.readouterr().err


def test_go_refused_on_expect_mismatch(workdir, monkeypatch, capsys):
    _no_client(monkeypatch)
    monkeypatch.setenv(POST_ENV, "1")
    cfg = _config_file(workdir)
    csv_path = _csv_file(workdir, _rows())
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go",
                 "--expect", "3"]) == 2
    assert "--expect 3" in capsys.readouterr().err


def test_go_refused_on_unpostable_unless_allow_partial(workdir, monkeypatch, capsys):
    monkeypatch.setenv(POST_ENV, "1")
    cfg = _config_file(workdir)
    rows = _rows("clean") + _rows("flagged", debit_acct="(uncategorized - assign)")
    csv_path = _csv_file(workdir, rows)

    _no_client(monkeypatch)
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 2
    assert "unpostable" in capsys.readouterr().err

    client = FakeClient(results=[{"journal_id": "J1", "entry_number": None}])
    monkeypatch.setattr(zoho_post_cli, "_make_client", lambda org: client)
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go",
                 "--allow-partial"]) == 0
    assert [p["reference_number"] for p in client.posted_payloads] == ["clean"]


def test_happy_go_posts_then_second_run_skips(workdir, monkeypatch, capsys):
    monkeypatch.setenv(POST_ENV, "1")
    cfg = _config_file(workdir)
    csv_path = _csv_file(workdir, _rows("t1") + _rows("t2", amount="9.99"))
    client = FakeClient(results=[
        {"journal_id": "J1", "entry_number": "JE-1"},
        {"journal_id": "J2", "entry_number": "JE-2"},
    ])
    monkeypatch.setattr(zoho_post_cli, "_make_client", lambda org: client)

    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go",
                 "--expect", "2"]) == 0
    out = capsys.readouterr().out
    assert "POSTED t1 -> journal J1" in out
    assert len(client.posted_payloads) == 2

    # Second, identical run: the ledger cross-reference posts nothing.
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 0
    out = capsys.readouterr().out
    assert "Nothing to post" in out
    assert len(client.posted_payloads) == 2  # unchanged


def test_forget_releases_reference(workdir, monkeypatch, capsys):
    monkeypatch.setenv(POST_ENV, "1")
    cfg = _config_file(workdir)
    csv_path = _csv_file(workdir, _rows("t1"))
    client = FakeClient(results=[{"journal_id": "J1", "entry_number": None},
                                 {"journal_id": "J9", "entry_number": None}])
    monkeypatch.setattr(zoho_post_cli, "_make_client", lambda org: client)

    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 0
    assert main(["--config", str(cfg), "--forget", "t1"]) == 0
    assert "may post again" in capsys.readouterr().out
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 0
    assert len(client.posted_payloads) == 2  # posted again after forget


def _seed_unresolved(workdir, *, recorded_at):
    with PostLedger(workdir / "ledger.sqlite") as ledger:
        ledger.mark_inflight(ORG, "t1", "h1", now_iso=recorded_at)
        ledger.mark_ambiguous(ORG, "t1", now_iso=recorded_at, content_hash="h1")
        ledger.mark_inflight(ORG, "t2", "h2", now_iso=recorded_at)


def test_verify_confirms_but_keeps_absent_without_clear_flag(workdir, monkeypatch,
                                                            capsys):
    cfg = _config_file(workdir)
    _seed_unresolved(workdir, recorded_at="2026-07-26T10:00:00+00:00")
    client = FakeClient(journals=[
        {"reference_number": "t1", "journal_id": "J5", "entry_number": "JE-5"},
    ])
    monkeypatch.setattr(zoho_post_cli, "_make_client", lambda org: client)

    assert main(["--config", str(cfg), "--verify"]) == 0
    out = capsys.readouterr().out
    assert "CONFIRMED in Zoho: t1 -> journal J5" in out
    assert "KEPT unresolved: t2" in out and "CLEARED" not in out
    with PostLedger(workdir / "ledger.sqlite") as ledger:
        assert ledger.status_for(ORG, "t1").state == "posted"
        assert ledger.status_for(ORG, "t2").state == "inflight"  # NOT cleared


def test_verify_clear_absent_honors_grace_window(workdir, monkeypatch, capsys):
    cfg = _config_file(workdir)
    # Recorded two days ago: far older than the 1h grace, clears.
    _seed_unresolved(workdir, recorded_at="2026-07-26T10:00:00+00:00")
    client = FakeClient(journals=[
        {"reference_number": "t1", "journal_id": "J5", "entry_number": "JE-5"},
    ])
    monkeypatch.setattr(zoho_post_cli, "_make_client", lambda org: client)

    assert main(["--config", str(cfg), "--verify", "--clear-absent"]) == 0
    out = capsys.readouterr().out
    assert "CONFIRMED in Zoho: t1 -> journal J5" in out
    assert "CLEARED (absent + aged past grace): t2" in out
    with PostLedger(workdir / "ledger.sqlite") as ledger:
        assert ledger.status_for(ORG, "t1").state == "posted"
        assert ledger.status_for(ORG, "t2") is None


def test_verify_clear_absent_keeps_rows_inside_grace(workdir, monkeypatch, capsys):
    from datetime import datetime, timezone
    cfg = _config_file(workdir)
    # Recorded just now: inside the 1h grace even with --clear-absent.
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _seed_unresolved(workdir, recorded_at=now)
    client = FakeClient(journals=[])
    monkeypatch.setattr(zoho_post_cli, "_make_client", lambda org: client)

    assert main(["--config", str(cfg), "--verify", "--clear-absent"]) == 0
    assert "KEPT unresolved" in capsys.readouterr().out
    with PostLedger(workdir / "ledger.sqlite") as ledger:
        assert ledger.status_for(ORG, "t1") is not None
        assert ledger.status_for(ORG, "t2") is not None


def test_ledger_listing(workdir, monkeypatch, capsys):
    _no_client(monkeypatch)
    cfg = _config_file(workdir)
    with PostLedger(workdir / "ledger.sqlite") as ledger:
        ledger.mark_inflight(ORG, "t1", "h", now_iso="2026-07-28T10:00:00+00:00")
        ledger.mark_posted(ORG, "t1", zoho_journal_id="J1", entry_number=None,
                           now_iso="2026-07-28T10:00:01+00:00", content_hash="h")
    assert main(["--config", str(cfg), "--ledger"]) == 0
    out = capsys.readouterr().out
    assert "posted" in out and "t1" in out and "J1" in out


def test_allow_partial_never_waives_blocked_or_conflict(workdir, monkeypatch, capsys):
    # --allow-partial waives ONLY unpostable; an unresolved ledger row
    # must still refuse the whole batch (typed refusal kinds, not
    # message prose).
    _no_client(monkeypatch)
    monkeypatch.setenv(POST_ENV, "1")
    cfg = _config_file(workdir)
    csv_path = _csv_file(workdir, _rows("t1"))
    with PostLedger(workdir / "ledger.sqlite") as ledger:
        ledger.mark_inflight(ORG, "t1", "h", now_iso="2026-07-26T10:00:00+00:00")
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go",
                 "--allow-partial"]) == 2
    assert "unresolved ledger state" in capsys.readouterr().err


def test_enabled_must_be_boolean_true(workdir, monkeypatch, capsys):
    # A kill switch must not read the string "false" (or any truthy
    # non-boolean) as on.
    _no_client(monkeypatch)
    monkeypatch.setenv(POST_ENV, "1")
    cfg = _config_file(workdir, enabled="false")
    csv_path = _csv_file(workdir, _rows())
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 2
    assert "boolean true" in capsys.readouterr().err


def test_config_allowlist_can_only_narrow_not_widen(tmp_path, monkeypatch, capsys):
    # A runtime config must not be able to authorize an org the code
    # was never reviewed for: org_allowlist intersects the built-in
    # set, so listing a foreign org grants nothing.
    _no_client(monkeypatch)
    monkeypatch.setenv(POST_ENV, "1")
    _chart_file(tmp_path, org="555000999")
    cfg = _config_file(tmp_path, org="555000999",
                       extra_post={"org_allowlist": ["555000999"]})
    csv_path = _csv_file(tmp_path, _rows())
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 2
    assert "allowlist" in capsys.readouterr().err


def test_cross_org_duplicate_refused_without_waiver(workdir, monkeypatch, capsys):
    monkeypatch.setenv(POST_ENV, "1")
    cfg = _config_file(workdir)
    csv_path = _csv_file(workdir, _rows("t1"))
    other_org = "697686691"
    with PostLedger(workdir / "ledger.sqlite") as ledger:
        ledger.mark_inflight(other_org, "t1", "h",
                             now_iso="2026-07-26T10:00:00+00:00")
        ledger.mark_posted(other_org, "t1", zoho_journal_id="J1", entry_number=None,
                           now_iso="2026-07-26T10:00:01+00:00", content_hash="h")

    _no_client(monkeypatch)
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 2
    assert "DIFFERENT org" in capsys.readouterr().err

    client = FakeClient(results=[{"journal_id": "J9", "entry_number": None}])
    monkeypatch.setattr(zoho_post_cli, "_make_client", lambda org: client)
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go",
                 "--allow-cross-org"]) == 0
    assert [p["reference_number"] for p in client.posted_payloads] == ["t1"]


def test_status_flows_from_config_and_validates(workdir, monkeypatch, capsys):
    monkeypatch.setenv(POST_ENV, "1")
    csv_path = _csv_file(workdir, _rows("t1"))

    # Default: draft in the actual posted payload.
    cfg = _config_file(workdir)
    client = FakeClient(results=[{"journal_id": "J1", "entry_number": None}])
    monkeypatch.setattr(zoho_post_cli, "_make_client", lambda org: client)
    assert main(["--config", str(cfg), "--csv", str(csv_path), "--go"]) == 0
    assert client.posted_payloads[0]["status"] == "draft"

    # Configured published flows into the payload (fresh ledger).
    (workdir / "ledger.sqlite").unlink()
    cfg2 = _config_file(workdir, extra_post={"status": "published"})
    client2 = FakeClient(results=[{"journal_id": "J2", "entry_number": None}])
    monkeypatch.setattr(zoho_post_cli, "_make_client", lambda org: client2)
    assert main(["--config", str(cfg2), "--csv", str(csv_path), "--go"]) == 0
    assert client2.posted_payloads[0]["status"] == "published"

    # Invalid status refuses before anything runs.
    _no_client(monkeypatch)
    cfg3 = _config_file(workdir, extra_post={"status": "final"})
    assert main(["--config", str(cfg3), "--csv", str(csv_path)]) == 2
    assert "draft|published" in capsys.readouterr().err


def test_forget_refuses_young_inflight_row(workdir, monkeypatch, capsys):
    from datetime import datetime, timezone
    _no_client(monkeypatch)
    cfg = _config_file(workdir)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with PostLedger(workdir / "ledger.sqlite") as ledger:
        ledger.mark_inflight(ORG, "t1", "h", now_iso=now)
    assert main(["--config", str(cfg), "--forget", "t1"]) == 2
    assert "grace window" in capsys.readouterr().err
    with PostLedger(workdir / "ledger.sqlite") as ledger:
        assert ledger.status_for(ORG, "t1") is not None  # survived


def test_missing_org_id_refuses(workdir, monkeypatch, capsys):
    _no_client(monkeypatch)
    cfg_path = workdir / "run.json"
    cfg_path.write_text(json.dumps({"zoho": {"post": {"enabled": True}}}),
                        encoding="utf-8")
    csv_path = _csv_file(workdir, _rows())
    assert main(["--config", str(cfg_path), "--csv", str(csv_path)]) == 2
    assert "coa_validation.org_id" in capsys.readouterr().err


def test_cli_dispatch_reaches_zoho_post(workdir, monkeypatch, capsys):
    _no_client(monkeypatch)
    assert cli_main(["zoho-post", "--config", str(workdir / "absent.json")]) == 2
    assert "config not found" in capsys.readouterr().err
