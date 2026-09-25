"""Tests for tools/recon-categorization-score.py on a synthetic payload dir.

Two GL months (July, Corporate Services; August, Cloud Services) plus one
bucket month, and a small Zoho pull whose account names resolve through the
real curated chart in the expense-recon module. Every charge row is built to
exercise one rule: the join window, the strict variant, one-to-one pairing,
the answer-source fold, the open-row split and the copy exclusion.
"""
import importlib.util
import json
from decimal import Decimal

import pytest

from hooklib import TOOLS


def _load():
    spec = importlib.util.spec_from_file_location("recon_categorization_score",
                                                  TOOLS / "recon-categorization-score.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rcs = _load()

CORP, CLOUD, GMBH = "822741658", "697686691", "696750461"
ACCOUNT_COMPANIES = [
    {"label": "Cloud Services", "org_id": CLOUD, "labels": ["Brisken Cloud Services, LLC", "Cloud Services"]},
    {"label": "Corporate Services", "org_id": CORP, "labels": ["Brisken Corp Services, LLC", "Corporate Services"]},
]


def row(tx, vendor, day, amount, *, entity="Corporate Services", code=None, source=None, refusal=None,
        bucket="unmatched", status="posted"):
    cat = {"category": code, "source": source, "zoho_account": None} if code else None
    return {"transaction_id": tx, "vendor": vendor, "date": day, "amount": amount, "currency": "USD",
            "legal_entity_id": entity, "effective_bucket": bucket, "entry_status": status,
            "posting_category": cat, "charge_category": cat if bucket == "unmatched" else None,
            "review": {"state": "refused" if refusal else "none", "refusal": refusal, "reason_code": None}}


JULY_ROWS = [
    row("R1", "ANTHROPIC", "2026-07-10", "100.00", code="E100020", source="VENDOR"),
    row("R2", "SUPERMERCADO FENIX", "2026-07-05", "10.82", code="Meals & Entertainment", source="REGISTRY"),
    row("R3", "SUPMEC SAO JOSE", "2026-07-06", "25.00", code="E100010-31", source="REGISTRY"),
    row("R4", "LOVABLE", "2026-07-15", "50.00", code="E100020-10", source="LINE; REVIEW",
        bucket="reconciled", status="subscription"),
    row("R5", "SUPABASE", "2026-07-20", "30.00", code="E100020-10", source="LEARNED"),
    row("R6", "BIELLYS", "2026-07-22", "8.40", refusal="account_unresolved"),
    row("R7", "POSTO SANTOS", "2026-07-25", "12.00"),
    row("R8", "OTHER CO", "2026-07-11", "77.00", code="E100020", source="VENDOR"),
    row("R9", "CENT OFF", "2026-07-11", "45.00", code="E100020", source="VENDOR"),
    row("R10", "GITHUB", "2026-07-12", "4.00", code="E500010-10", source="VENDOR"),
    row("R11", "GITHUB", "2026-07-12", "4.00", code="E500010-10", source="VENDOR"),
    row("R12", "WISPR", "2026-07-18", "15.00", code="E100020-10", source="VENDOR"),
    row("R13", "FOURDAYS", "2026-07-02", "60.00", code="E100020-10", source="LINE", bucket="reconciled"),
    row("RF","ANTHROPIC", "2026-07-10", "100.00", bucket="refund"),
]
AUG_ROWS = [
    row("A1", "OPENAI", "2026-08-03", "20.00", entity="Cloud Services", code="E500010-10", source="VENDOR",
        status=None),
    row("A2", "DIGITALOCEAN", "2026-08-05", "12.00", entity="Cloud Services", code="E700030-30",
        source="VENDOR", status=None),
    row("A3", "SENDGRID", "2026-08-07", "9.00", entity="Cloud Services", code="E500010-10", source="VENDOR",
        status="subscription"),
]


def expense(doc, lines, *, refusal=None, reason=None, boxes=None, entity="Corporate Services"):
    return {"document_id": doc, "legal_entity_id": entity, "currency": "USD",
            "boxes": ["x"] if boxes is None else boxes, "vendor": {"display": doc, "raw": doc},
            "review": {"refusal": refusal, "reason_code": reason},
            "line_items": [{"category": c, "line_total": t} for c, t in lines]}


JULY_EXPENSES = [
    expense("E1", [("E100020-10", "10.00")]),
    expense("E2", [(None, "5.00")], refusal="account_unresolved"),
    expense("E3", [(None, "5.00")], refusal="account_unresolved", boxes=[]),        # a copy
    expense("E4", [("E100020-10", "3.00"), (None, "7.00")], reason="partial_uncategorized"),
    expense("E5", [(None, "9.00")], refusal="entity_missing", entity=""),
    expense("E6", [(None, "4.00")], reason="waits_for_statement", entity=""),
    expense("E7", [], reason="missing_fields"),
]


def zoho_expense(day, total, desc, account):
    return {"date": day, "total": total, "description": desc, "vendor_name": "", "account_name": account,
            "currency_code": "USD", "paid_through_account_name": "Chase card"}


FOOD = "CorpServ | Travel Expense | Food"
CORP_IT = "CorpServ | IT Expenses"
COGS_INFRA = "COGS - Other Infra and IT Costs for Cloud Business"
ZOHO = {
    "pulled_at": "2026-09-18",
    "orgs": {
        CORP: {"expenses": [
            zoho_expense("2026-07-11", "100.00", "ANTHROPIC", COGS_INFRA),        # R1 d1: both joins
            zoho_expense("2026-07-08", "10.82", "Food", FOOD),                    # R2 d3: loose only
            zoho_expense("2026-07-07", "25.00", "Groceries", FOOD),               # R3 d1, no token: loose only
            zoho_expense("2026-07-15", "50.00", "Subscription", CORP_IT),         # R4 same day: both
            zoho_expense("2026-07-21", "30.00", "SUPABASE", CORP_IT),             # R5
            zoho_expense("2026-07-23", "8.40", "BIELLYS", FOOD),                  # R6 refused
            zoho_expense("2026-07-26", "12.00", "POSTO SANTOS", FOOD),            # R7 no answer
            zoho_expense("2026-07-11", "45.01", "CENT OFF", CORP_IT),             # R9 a cent off
            zoho_expense("2026-07-13", "4.00", "GITHUB", COGS_INFRA),             # R10/R11 compete
            zoho_expense("2026-07-21", "15.00", "WISPR", CORP_IT),                # R12 far candidate
            zoho_expense("2026-07-19", "15.00", "WISPR", CORP_IT),                # R12 near candidate
            zoho_expense("2026-07-06", "60.00", "FOURDAYS", CORP_IT),             # R13 four days out
            zoho_expense("2026-06-30", "99.00", "JUNE", CORP_IT),                 # outside the window
        ]},
        CLOUD: {"expenses": [
            zoho_expense("2026-07-11", "77.00", "OTHER CO", COGS_INFRA),          # R8's amount, other company
            zoho_expense("2026-08-04", "20.00", "OPENAI", "COGS - DEV Infrastructure (SAP Apps & others)"),
            zoho_expense("2026-08-06", "12.00", "DIGITALOCEAN", COGS_INFRA),
            zoho_expense("2026-08-08", "9.00", "SENDGRID", COGS_INFRA),
        ]},
        GMBH: {"expenses": [zoho_expense("2026-07-10", "100.00", "ANTHROPIC", "Anything")]},
    },
}


def _write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


@pytest.fixture
def payload(tmp_path):
    d = tmp_path / "payload"
    d.mkdir()
    july_summary = {"n_categorized": 1, "n_uncategorized": 5, "n_charges_category_guessed": 0}
    _write(d / "batch_jul001.json", {"label": "July 2026", "category_vocabulary": "gl",
                                     "summary": july_summary, "expenses": JULY_EXPENSES})
    _write(d / "run_jul001.json", {"label": "July 2026", "rows": JULY_ROWS, "summary": july_summary})
    aug_summary = {"n_categorized": 0, "n_uncategorized": 0}
    _write(d / "batch_aug001.json", {"label": "August 2026", "category_vocabulary": "gl",
                                     "summary": aug_summary, "expenses": []})
    _write(d / "run_aug001.json", {"label": "August 2026", "rows": AUG_ROWS, "summary": aug_summary})
    _write(d / "batch_jun001.json", {"label": "June 2026", "category_vocabulary": "buckets",
                                     "summary": {"n_categorized": 1, "n_uncategorized": 0},
                                     "expenses": [expense("J1", [("Software", "1.00")])]})
    _write(d / "settings.json", {"account_companies": ACCOUNT_COMPANIES, "merchants": {}})
    zoho = tmp_path / "zoho.json"
    _write(zoho, ZOHO)
    return d, zoho


def _report(payload, **kw):
    d, zoho = payload
    return rcs.build_report(d, zoho, **kw)


# ---- the join --------------------------------------------------------------------------

def _joined_tx(section):
    return sorted(r["tx"] for r in section["rows"])


def test_loose_join_window_company_cent_and_one_to_one(payload):
    loose = _report(payload)["accuracy"]["loose"]
    # R8 (other company), R9 (a cent off), R13 (four days out) and the refund
    # never join; R10/R11 compete for one posting, so exactly one of them joins.
    assert _joined_tx(loose) == sorted(["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R10", "R12",
                                        "A1", "A2", "A3"])
    assert loose["joined"] == 12


def test_nearest_date_wins_the_pair(payload):
    loose = _report(payload)["accuracy"]["loose"]
    r12 = next(r for r in loose["rows"] if r["tx"] == "R12")
    assert r12["day_diff"] == 1


def test_strict_join_needs_a_shared_token_within_a_day_or_the_same_day(payload):
    strict = _report(payload)["accuracy"]["strict"]
    # R2 is three days out; R3 is a day out with no shared descriptor token.
    # R4 shares no token either but is the same day, so it stays.
    assert "R2" not in _joined_tx(strict) and "R3" not in _joined_tx(strict)
    assert "R4" in _joined_tx(strict)
    assert strict["joined"] == 10


def test_truth_window_and_curated_orgs(payload):
    inputs = _report(payload)["inputs"]
    # June posting and the GmbH (uncurated) org are outside the truth.
    assert inputs["truth_months"] == ["2026-07", "2026-08"]
    assert inputs["truth_rows"] == 16
    assert inputs["truth_rows_unresolved"] == 0


def test_truth_months_override_widens_the_window(payload):
    assert _report(payload, truth_months=["2026-06", "2026-07", "2026-08"])["inputs"]["truth_rows"] == 17


# ---- source split -------------------------------------------------------------------------

def test_accuracy_by_source_folds_review_and_flags_non_code_answers(payload):
    loose = _report(payload)["accuracy"]["loose"]
    src = loose["by_source"]
    assert (loose["right"], loose["answered"]) == (5, 10)
    assert src["REGISTRY"] == {"answered": 2, "right": 1, "code_answers": 1, "label_answers": 1}
    assert src["LEARNED"]["right"] == 1 and src["LEARNED"]["answered"] == 1
    assert src["LINE"] == {"answered": 1, "right": 1, "code_answers": 1, "label_answers": 0}   # LINE; REVIEW
    assert (src["VENDOR"]["right"], src["VENDOR"]["answered"]) == (2, 6)
    assert loose["verdicts"] == {"disagree": 5, "agree": 5, "refused": 1, "no_answer": 1}


def test_answer_source_fold():
    assert rcs.answer_source("LINE; REVIEW") == "LINE"
    assert rcs.answer_source("REVIEW") == "REVIEW"
    assert rcs.answer_source("LINE; REGISTRY") == "MIXED"
    assert rcs.answer_source(None) is None


def test_markdown_shows_codes_apart_from_the_retired_label(payload):
    md = rcs.render_markdown(_report(payload))
    assert "| REGISTRY | 1/2 (1/1 on codes, 1 non-code) | 0/0 |" in md
    assert "| **All answered** | **5/10** | **4/8** |" in md


# ---- open rows and money -----------------------------------------------------------------------

def test_open_rows_exclude_posted_and_subscription(payload):
    loose = _report(payload)["accuracy"]["loose"]
    # Only A1 and A2 were still to be booked; A3 is a subscription row.
    assert loose["open_rows"]["joined"] == 2
    assert (loose["open_rows"]["right"], loose["open_rows"]["answered"]) == (1, 2)


def test_amount_weighted_view(payload):
    usd = _report(payload)["accuracy"]["loose"]["amounts"]["USD"]
    assert Decimal(usd["agree"]) == Decimal("132.00")
    assert Decimal(usd["disagree"]) == Decimal("143.82")
    assert Decimal(usd["refused"]) == Decimal("8.40")
    assert Decimal(usd["no_answer"]) == Decimal("12.00")


# ---- receipts: copies and refusals -------------------------------------------------------------

def test_copies_are_excluded_from_the_screen_baseline(payload):
    july = _report(payload)["months"]["July 2026"]["receipts"]
    assert (july["n_receipts"], july["n_copies"]) == (6, 1)
    assert (july["n_categorized"], july["n_uncategorized"]) == (1, 5)
    assert july["screen"]["agrees"] is True
    assert "E3" not in {r["document_id"] for r in july["refusals"]}


def test_refusal_groups_split_engine_from_intake(payload):
    july = _report(payload)["months"]["July 2026"]["receipts"]
    # E2 the model refused; E4 has one open line; E5 has no company, E6 waits
    # for a statement, E7 has no lines.
    assert july["refusal_groups"] == {"refused": 1, "partial": 1, "intake": 3}
    assert july["refusal_keys"]["partial:partial_uncategorized"] == 1


def test_bucket_month_is_baselined_but_not_scored(payload):
    rep = _report(payload)
    assert rep["months"]["June 2026"]["vocab"] == "buckets"
    assert rep["months"]["June 2026"]["charges"] is None
    assert rep["receipts_total_gl"]["n_receipts"] == 6
    assert list(rep["months"]) == ["June 2026", "July 2026", "August 2026"]


def test_charge_baseline_counts_guesses_the_app_counter_hides(payload):
    july = _report(payload)["months"]["July 2026"]["charges"]
    assert (july["n_unmatched"], july["with_account"], july["refused"], july["no_answer"]) == (11, 9, 1, 1)
    assert july["account_sources"] == {"VENDOR": 6, "REGISTRY": 2, "LEARNED": 1}
    assert july["app_guess_counter"] == 0


# ---- the account map ---------------------------------------------------------------------------------

def test_account_map_absent_says_so(payload):
    assert _report(payload)["account_map"] == {"available": False, "n_merchants_with_map": 0}


def test_account_map_precision_through_the_registry(payload):
    pytest.importorskip("rapidfuzz")
    d, _zoho = payload
    _write(d / "settings.json", {"account_companies": ACCOUNT_COMPANIES, "merchants": {
        "Anthropic": {"accounts": {"Corporate Services": "E700030-30"}},
        "OpenAI": {"accounts": {"Brisken Cloud Services, LLC": "E700030-19"}},
        "GitHub": {"accounts": {"Corporate Services": "E100020-10"}},
    }})
    lever = _report(payload)["account_map"]
    assert (lever["covered"], lever["agree"]) == (3, 2)
    assert lever["effect_vs_today"] == {"fixed_wrong": 2, "wrong": 1}


# ---- fetch -------------------------------------------------------------------------------------------

class _Resp:
    def __init__(self, body):
        self._body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body


def _fake_api(slow_path=None):
    calls, clock = [], {"t": 0.0}
    bodies = {
        "/healthz": {"status": "ok"}, "/api/login": {"token": "SECRET-TOKEN"},
        "/api/expense-batches": {"batches": [{"batch_id": "jul001", "label": "July 2026"}]},
        "/api/expense-batches/jul001": {"label": "July 2026"}, "/api/runs/jul001": {"rows": []},
        "/api/settings": {"account_companies": []}, "/api/memory": {"by_vendor": []},
    }

    def opener(req, timeout):
        path = req.full_url.split(".test", 1)[1]
        calls.append((req.get_method(), path, req.get_header("Authorization")))
        clock["t"] += 50.0 if path == slow_path else 1.0
        return _Resp(bodies[path])

    return calls, clock, opener


def test_fetch_reads_each_endpoint_once_spaced_and_keeps_the_token_off_disk(tmp_path):
    calls, clock, opener = _fake_api()
    sleeps = []
    written = rcs.fetch(tmp_path, "https://recon.test", ["jul001"], "the-code", opener=opener,
                        sleep=sleeps.append, clock=lambda: clock["t"], log=lambda *_: None)
    paths = [p for _m, p, _a in calls]
    assert paths == ["/healthz", "/api/login", "/api/expense-batches", "/api/expense-batches/jul001",
                     "/api/runs/jul001", "/api/settings", "/api/memory"]
    assert sleeps == [rcs.FETCH_GAP_S] * (len(paths) - 1)
    assert calls[3][2] == "Bearer SECRET-TOKEN"
    assert sorted(written) == ["batch_jul001.json", "batches.json", "memory.json", "run_jul001.json",
                               "settings.json"]
    for f in tmp_path.iterdir():
        text = f.read_text(encoding="utf-8")
        assert "SECRET-TOKEN" not in text and "the-code" not in text


def test_fetch_brakes_on_a_slow_read(tmp_path):
    calls, clock, opener = _fake_api(slow_path="/api/expense-batches/jul001")
    with pytest.raises(rcs.Braked):
        rcs.fetch(tmp_path, "https://recon.test", ["jul001"], "c", opener=opener, sleep=lambda s: None,
                  clock=lambda: clock["t"], log=lambda *_: None)
    assert [p for _m, p, _a in calls][-1] == "/api/expense-batches/jul001"   # nothing read after the brake


def test_fetch_refuses_an_unknown_month(tmp_path):
    _calls, clock, opener = _fake_api()
    with pytest.raises(rcs.InputError, match="unknown"):
        rcs.fetch(tmp_path, "https://recon.test", ["nope"], "c", opener=opener, sleep=lambda s: None,
                  clock=lambda: clock["t"], log=lambda *_: None)


# ---- CLI --------------------------------------------------------------------------------------------------

def test_cli_writes_json_and_markdown_with_the_constants(payload, tmp_path, capsys):
    d, zoho = payload
    out = tmp_path / "out"
    assert rcs.main(["--payload-dir", str(d), "--zoho", str(zoho), "--out", str(out)]) == 0
    rep = json.loads((out / "categorization-score.json").read_text(encoding="utf-8"))
    assert rep["constants"]["join"].startswith("same company + amount to the cent + |date| <= 3 days")
    assert "## Constants" in (out / "categorization-score.md").read_text(encoding="utf-8")
    assert "5/10" in capsys.readouterr().out


def test_cli_missing_payload_exits_2(tmp_path):
    assert rcs.main(["--payload-dir", str(tmp_path / "nope"), "--zoho", str(tmp_path / "z.json")]) == 2
