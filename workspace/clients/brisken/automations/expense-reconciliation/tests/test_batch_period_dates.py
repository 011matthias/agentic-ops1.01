"""Backlog item 25 (2026-08-23): a date that cannot belong to this month is
flagged, never silently accepted.

The defect, from the live April 2026 batch `ae61e122a505`: eleven of its
thirty-six receipt readings were dated 2020-2023. The stored raw extractions
already carried those years, so the parse layer was innocent; the vision read
was wrong at the source. Two mechanisms are visible in the images:

* `receipt_33_p39` prints its true date twice. The fiscal block says
  `Data: 2026-04-22`; the card slip above it says `26-04-22`, which is
  YY-MM-DD. The model read the slip day-first and returned 2022-04-26.
* `receipt_03_p9` prints `02/04/2026` in full and `02.04.26` on the slip. The
  model returned 2023-04-02: day and month right, the year invented.

The extraction prompt was tightened in the same round, but no prompt can be
pinned by a test and no prompt rescues a faded thermal slip. What IS pinned
here is that the tool stops accepting the answer quietly. The eleven real
misread dates below are the fixture, so this file fails the day the guard
stops catching the batch it was written for.
"""
from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.batch_period import (  # noqa: E402
    batch_period,
    month_from_dates,
    month_from_label,
    outside_period,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

# The live April batch, verbatim: what the model returned for each receipt,
# in file order. Eleven of these years are wrong, and nothing in the reading
# itself says which -- which is why they are judged against the month.
APRIL_2026_READINGS: tuple[tuple[str, str], ...] = (
    ("ERICK SPORT", "2026-04-01"),
    ("MEGA CENTRO COMERCIAL LTDA", "2023-04-02"),        # really 2026-04-02
    ("MEGA CENTRO COMERCIO DE MATERIAIS", "2026-04-04"),
    ("MEGA CENTER COMERCIO DE MATERIAIS", "2026-04-08"),
    ("MEGA CENTRO", "2026-04-11"),
    ("PagBank", "2026-04-01"),
    ("americanas sa", "2026-04-01"),
    ("Sushi Du Thiago", "2023-04-01"),                   # misread year
    ("KI MASSA", "2026-04-01"),
    ("SJCORDA GRANDE COMERCIO DE S", "2026-04-02"),
    ("SUPERMERCADO FENTI LTDA", "2023-10-18"),           # misread year
    ("PEIXARIA CHAGAS", "2026-04-02"),
    ("J C SOUZA DE LYRA", "2026-04-04"),
    ("CALDINHO DO MARACA", "2026-04-04"),
    ("MARINHO SUPERMERCADO LTDA", "2026-04-05"),
    ("SABRAY VISCHER - VIA CLIENTE", "2022-08-04"),      # misread year
    ("Mikaias Santos Pedrosa", "2020-04-09"),            # misread year
    ("SUPERMERCADO FENIX LTDA", "2026-04-10"),
    ("MIX BOLOS CASEIRO", "2026-04-10"),
    ("Espetinho do Ramos", "2023-04-11"),                # misread year
    ("NOBRE ATACADO SAO JOSE", "2026-04-12"),
    ("O REI DO ARRUMADINHO LTDA", "2026-04-15"),
    ("DANIELA DA TAPIOCA", "2026-04-16"),
    ("cielo", "2026-04-16"),
    ("O CASTELINHO", "2026-04-17"),
    ("BANCO BRADESCO", "2026-04-18"),
    ("Hiper Mercado Supermercado", "2023-04-18"),        # misread year
    ("PagBank", "2023-08-19"),                           # misread year
    ("MARTINO SUPERMERCADO LTDA", "2026-04-20"),
    ("COMERCIAL CASA DOS FRIOS LTDA", "2026-04-21"),
    ("RMA COMERCIO DE FRIOS LTDA", "2026-04-18"),
    ("VERSAILLES I-ROTISSE", "2022-04-26"),              # really 2026-04-22
    ("COTEGY COMBUSTIVEIS LTDA", "2023-04-21"),          # misread year
    ("CARNACHARIA AJ AMARAL", "2023-01-26"),             # misread year
    ("AUTO POSTO PINIMTEL", "2026-04-05"),
    ("RAC INDUSTRIA DE COMPRESSAO", "2026-04-17"),
)

MISREAD = tuple(d for _, d in APRIL_2026_READINGS if not d.startswith("2026-04"))


def test_the_fixture_is_the_live_batch():
    # Guard the guard: trimming this table would quietly weaken every
    # assertion below, so pin what it is supposed to contain.
    assert len(APRIL_2026_READINGS) == 36
    assert len(MISREAD) == len(set(MISREAD)) == 11


# -- the period primitives -------------------------------------------


def test_label_names_the_month():
    assert month_from_label("April 2026") == (2026, 4)
    assert month_from_label("april 2026") == (2026, 4)
    assert month_from_label("Abril 2026") == (2026, 4)
    assert month_from_label("2026 Apr") == (2026, 4)
    assert month_from_label("2026-04") == (2026, 4)
    assert month_from_label("Dezembro 2025") == (2025, 12)


def test_label_refuses_what_it_cannot_read():
    # No year: "January" alone could be any year, and picking one would put
    # every expense of the other year under suspicion.
    assert month_from_label("January") is None
    # Two months or two years named: ambiguous, so no period.
    assert month_from_label("March-April 2026") is None
    assert month_from_label("April 2025 2026") is None
    # A full date stamps when a run was CREATED (the real live labels
    # "chase-2838 2026-07-24" / "2838 2026-07-20"); it is not a month claim.
    assert month_from_label("chase-2838 2026-07-24") is None
    # Real non-month labels from the live store.
    assert month_from_label("AGENT-DIAG ER-00215 smoke") is None
    assert month_from_label("") is None
    assert month_from_label(None) is None
    # A word merely CONTAINING a month abbreviation is not a month.
    assert month_from_label("decision review 2026") is None
    assert month_from_label("marketing spend 2026") is None


def test_dates_decide_when_the_label_does_not():
    dates = [date.fromisoformat(d) for _, d in APRIL_2026_READINGS]
    # 25 of 36 readings say April 2026; the eleven misreads scatter and lose.
    assert month_from_dates(dates) == (2026, 4)


def test_dates_refuse_a_batch_with_no_agreement():
    # Too few to have a consensus at all.
    assert month_from_dates([date(2026, 4, 1), date(2026, 4, 2)]) is None
    # A tie is a genuinely mixed batch, and a mixed batch has no period.
    tie = [date(2026, 4, 1), date(2026, 4, 2), date(2026, 5, 1), date(2026, 5, 2)]
    assert month_from_dates(tie) is None
    # A plurality too thin to trust: 4 of 11 is not a month, even though it
    # beats the runner-up.
    thin = (
        [date(2026, 4, i) for i in range(1, 5)]
        + [date(2026, 5, i) for i in range(1, 4)]
        + [date(2026, 6, i) for i in range(1, 3)]
        + [date(2026, 7, i) for i in range(1, 3)]
    )
    assert len(thin) == 11
    assert month_from_dates(thin) is None
    # Three receipts must agree whatever the share works out to, so two votes
    # out of four does not make a month even though it wins on percentage.
    assert month_from_dates(
        [date(2026, 4, 1), date(2026, 4, 2), date(2026, 5, 1), date(2026, 6, 1)]
    ) is None
    assert month_from_dates(
        [date(2026, 4, 1), date(2026, 4, 2), date(2026, 4, 3), date(2026, 6, 1)]
    ) == (2026, 4)


def test_window_spans_the_neighbouring_months():
    period = batch_period("April 2026", [])
    assert period == (date(2026, 3, 1), date(2026, 5, 31))
    # A receipt from the last days of March or the first of May lands in an
    # April folder often enough that flagging it would only cost a look.
    assert not outside_period(date(2026, 3, 31), period)
    assert not outside_period(date(2026, 5, 1), period)
    assert outside_period(date(2026, 2, 28), period)
    assert outside_period(date(2026, 6, 1), period)
    # Year boundaries do not wrap wrong.
    assert batch_period("January 2026", []) == (date(2025, 12, 1), date(2026, 2, 28))
    assert batch_period("December 2026", []) == (date(2026, 11, 1), date(2027, 1, 31))
    # February in a leap year ends on the 29th.
    assert batch_period("January 2028", [])[1] == date(2028, 2, 29)


def test_no_period_means_nothing_is_ever_flagged():
    assert batch_period("AGENT-DIAG ER-00215 smoke", []) is None
    assert not outside_period(date(1999, 1, 1), None)
    assert not outside_period(None, (date(2026, 3, 1), date(2026, 5, 31)))


def test_every_misread_year_in_the_live_april_batch_is_outside():
    period = batch_period("April 2026", [])
    for raw in MISREAD:
        assert outside_period(date.fromisoformat(raw), period), raw
    for _, raw in APRIL_2026_READINGS:
        if raw not in MISREAD:
            assert not outside_period(date.fromisoformat(raw), period), raw


# -- the guard where the reviewer meets it ---------------------------


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_COA_PROVISION", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(vendor: str, iso_date: str) -> ExtractedReceipt:
    return ExtractedReceipt(
        date=iso_date, total="42.50", currency="BRL", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _batch(client, monkeypatch, readings, label="April 2026"):
    mock = MockLLMClient(
        extraction_responses=[_extraction(v, d) for v, d in readings]
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    files = [
        ("files", (f"r{i:02d}.jpg", JPG + str(i).encode(), "application/octet-stream"))
        for i in range(len(readings))
    ]
    resp = client.post(
        "/api/expense-batches", files=files,
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["status"] == "done", job
    return body["batch_id"]


def _rows(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["expenses"]


def _flagged(rows):
    return [r for r in rows if r["review"]["reason_code"] == "date_outside_period"]


def test_the_live_april_batch_flags_exactly_its_eleven_misreads(client, monkeypatch):
    """The defect, end to end. Eleven expenses are dated years away from the
    month they were filed under, and every one of them now reaches the
    reviewer as `check` instead of shipping quietly into the report."""
    rows = _rows(client, _batch(client, monkeypatch, APRIL_2026_READINGS))
    flagged = _flagged(rows)
    assert len(flagged) == 11
    assert sorted(r["date"] for r in flagged) == sorted(MISREAD)

    row = next(r for r in flagged if r["date"] == "2022-04-26")  # really 2026-04-22
    assert row["review"]["state"] == "check"
    # Structured beside the prose, so the SPA writes its own sentence.
    assert row["review"]["period"] == {"start": "2026-03-01", "end": "2026-05-31"}
    assert row["review"]["date"] == "2022-04-26"
    assert "2022-04-26" in row["review"]["reason"]


def test_the_twenty_five_good_readings_stay_out_of_review(client, monkeypatch):
    """The guard must not turn a working month into a wall of flags."""
    rows = _rows(client, _batch(client, monkeypatch, APRIL_2026_READINGS))
    clean = [r for r in rows if r["date"] not in MISREAD]
    assert len(clean) == 25
    for r in clean:
        assert r["review"]["reason_code"] != "date_outside_period", r["date"]


def test_correcting_the_date_clears_the_flag(client, monkeypatch):
    """The reviewer's fix is the exit. Typing the real date both moves the
    expense into the month and silences the guard."""
    batch_id = _batch(client, monkeypatch, APRIL_2026_READINGS)
    before = next(
        r for r in _rows(client, batch_id) if r["date"] == "2022-04-26"
    )
    # Assert the flag is UP first, or "it cleared" would also be true of a
    # guard that never fired.
    assert before["review"]["reason_code"] == "date_outside_period"
    doc = before["document_id"]
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "date", "value": "2026-04-22"},
    )
    assert resp.status_code == 200, resp.text
    row = next(r for r in _rows(client, batch_id) if r["document_id"] == doc)
    assert row["date"] == "2026-04-22"
    assert row["review"]["reason_code"] != "date_outside_period"


def test_a_reviewer_who_confirms_the_old_date_is_believed(client, monkeypatch):
    """The third case the diagnosis had to allow for: a re-issued invoice
    really does print an old date. Confirming it by hand ends the argument.
    Without this the flag could never be cleared and the row would sit in
    review forever, which is how a guard turns into noise people ignore."""
    batch_id = _batch(client, monkeypatch, APRIL_2026_READINGS)
    before = next(
        r for r in _rows(client, batch_id) if r["date"] == "2020-04-09"
    )
    assert before["review"]["reason_code"] == "date_outside_period"
    doc = before["document_id"]
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "date", "value": "2020-04-09"},
    )
    assert resp.status_code == 200, resp.text
    row = next(r for r in _rows(client, batch_id) if r["document_id"] == doc)
    assert row["date"] == "2020-04-09"
    assert row["review"]["reason_code"] != "date_outside_period"


def test_an_unlabelled_batch_is_still_guarded(client, monkeypatch):
    """No label, so the batch's own dates decide. The misread years are the
    minority and lose the vote, exactly as they do with a label."""
    rows = _rows(client, _batch(client, monkeypatch, APRIL_2026_READINGS, label=""))
    assert sorted(r["date"] for r in _flagged(rows)) == sorted(MISREAD)


def test_the_month_report_names_the_dates_it_distrusts(client, monkeypatch):
    """Item 25 was FOUND on this document, not in the grid: line two of the
    live April report showed a 2023 date and said nothing about it. The
    report now names the expense numbers whose dates fall outside the month,
    so a reader sees the doubt without cross-checking a screen."""
    import io

    from pypdf import PdfReader

    batch_id = _batch(client, monkeypatch, APRIL_2026_READINGS)
    pdf = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert pdf.status_code == 200, pdf.text
    text = "\n".join(
        p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf.content)).pages
    )
    assert "falls outside this month" in text
    # The misread rows are listed by expense number, and the note is plural
    # because eleven of them are wrong.
    assert "date read on expenses" in text


def test_the_month_report_stays_quiet_when_every_date_fits(client, monkeypatch):
    import io

    from pypdf import PdfReader

    clean = tuple(r for r in APRIL_2026_READINGS if r[1] not in MISREAD)
    batch_id = _batch(client, monkeypatch, clean)
    pdf = client.get(f"/runs/{batch_id}/expense-report.pdf").content
    text = "\n".join(
        p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages
    )
    assert "falls outside this month" not in text


def test_a_batch_with_no_knowable_month_flags_nothing(client, monkeypatch):
    """Four expenses in four different months, under a label that names no
    month. Nothing here says which month is the real one, so the guard says
    nothing rather than putting three of four rows under suspicion."""
    readings = (
        ("A", "2026-01-05"), ("B", "2026-04-05"),
        ("C", "2026-07-05"), ("D", "2026-10-05"),
    )
    rows = _rows(client, _batch(client, monkeypatch, readings, label="mixed upload"))
    assert _flagged(rows) == []
