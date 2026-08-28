"""Duplicates the reviewer can see on the row they are reading.

The detector has flagged duplicates since Tier-1 #4, and it works: the live
April batch carries one group, the Pressmaster FZCO invoice at 135.00 USD
forwarded twice under two different file names, correctly grouped. What it
did not do was say so anywhere a reviewer looks. `duplicate_groups` is a
side list of document ids; the 40-row grid above it showed the two copies
with nothing to tell them apart from any other pair of rows, so finding the
duplicate meant noticing the amount twice by eye. A flag nobody sees is not
a flag.

Four things are under test:

1. **The row carries it.** Every member of a live group gets `duplicate`,
   with the first copy marked as the original and the rest as extras. That
   split is what lets a grid say "same as row 39" instead of marking both
   rows equally guilty.
2. **A dismissal actually dismisses.** `resolution: ignore` clears the
   marker everywhere, including the count. A flag that outlives the
   reviewer's ruling teaches them to ignore all flags.
3. **The count answers its own question.** `n_duplicate_copies` is how many
   copies are redundant; `n_duplicate_groups` is how many situations there
   are. Two names because they are two questions, per the `n_categorized`
   failure of 2026-08-22.
4. **The document names them.** The reconciliation PDF printed
   "N possible duplicate groups" and nothing else, which is a number a
   reader can act on only by going to look for it themselves.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from expense_recon.duplicates import duplicate_row_flags, n_extra_copies

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _wire(monkeypatch, n=6):
    """Every receipt reads back as the SAME purchase, which is what a twice
    forwarded invoice looks like to the extractor."""
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-04-15", total="135.00", currency="USD",
                vendor="Pressmaster FZCO", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ] * n,
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("135.00"), reasoning="same purchase",
            )
        ] * 24,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _batch(client, n_files=2, label="April 2026"):
    resp = client.post(
        "/api/expense-batches",
        files=[
            # Distinct BYTES, identical CONTENT: two scans of one invoice,
            # which is what a twice-forwarded receipt actually looks like.
            # Byte-identical files are dropped by the pool's own dedupe at
            # add time and never reach the detector.
            ("files", (f"invoice-{i}.jpg", JPG + bytes([i]),
                       "application/octet-stream"))
            for i in range(n_files)
        ],
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _csv(*rows: tuple[str, str, str]) -> bytes:
    body = "".join(f"{d},{a},{v}\n" for d, a, v in rows)
    return ("Date,Amount,Vendor\n" + body).encode()


def _upload(client, batch_id, body: bytes, name="statement.csv"):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (name, body, "application/octet-stream")},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
        },
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── 1. the helper, on its own ───────────────────────────────────────────


def _group(kind="receipt", members=("a", "b"), resolution=None, gid="g1"):
    return {
        "group_id": gid, "kind": kind,
        "members": list(members), "resolution": resolution,
    }


def test_the_first_copy_is_the_original_and_the_rest_are_extras():
    """Which one is the extra has to be a stable answer, or a grid that
    says "delete this one" points somewhere different on every reload."""
    flags = duplicate_row_flags([_group(members=("a", "b", "c"))], kind="receipt")
    assert set(flags) == {"a", "b", "c"}
    assert [flags[m]["copy"] for m in "abc"] == [1, 2, 3]
    assert [flags[m]["is_extra"] for m in "abc"] == [False, True, True]
    assert {flags[m]["of"] for m in "abc"} == {"a"}
    assert {flags[m]["n_copies"] for m in "abc"} == {3}
    assert n_extra_copies(flags) == 2


def test_a_dismissed_group_leaves_no_marker_behind():
    """The reviewer ruled it is not a duplicate. A marker that survives the
    ruling is one they learn to ignore, and then they ignore the real ones
    too."""
    ignored = duplicate_row_flags(
        [_group(resolution="ignore")], kind="receipt"
    )
    assert ignored == {}
    assert n_extra_copies(ignored) == 0


def test_a_confirmed_group_keeps_its_marker():
    """Acknowledging a duplicate is not removing it: the second copy is
    still on the screen and still in the total until somebody deletes it."""
    flags = duplicate_row_flags([_group(resolution="confirmed")], kind="receipt")
    assert flags["b"]["is_extra"] is True
    assert flags["b"]["resolution"] == "confirmed"


def test_a_charge_group_never_lands_on_a_receipt_row():
    """The two id spaces are not disjoint by construction. One merged map
    would put a charge's verdict on a receipt that happens to share the
    string."""
    groups = [_group(kind="charge", members=("x", "y"), gid="c1")]
    assert duplicate_row_flags(groups, kind="receipt") == {}
    assert set(duplicate_row_flags(groups, kind="charge")) == {"x", "y"}


def test_a_group_of_one_is_not_a_duplicate():
    """A group whose other members were filtered out (ids the payload does
    not hold) describes nothing, and marking its survivor would accuse a
    row of duplicating itself."""
    assert duplicate_row_flags([_group(members=("only",))], kind="receipt") == {}


# ── 2. the expense grid, through the route ──────────────────────────────


def test_the_two_copies_of_one_invoice_are_marked_on_their_own_rows(
    client, monkeypatch
):
    """The live case: one invoice, forwarded twice, two expense rows. Before
    this the grid showed both and said nothing."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    view = _grid(client, batch_id)

    assert view["summary"]["n_duplicate_groups"] == 1
    assert view["summary"]["n_duplicate_copies"] == 1, view["summary"]

    marked = [e for e in view["expenses"] if e["duplicate"]]
    assert len(marked) == 2, [e["document_id"] for e in view["expenses"]]
    assert len({m["duplicate"]["group_id"] for m in marked}) == 1
    assert sorted(m["duplicate"]["is_extra"] for m in marked) == [False, True]

    # `of` points at a row that is actually in this grid, or "same as
    # row N" names a row nobody can find.
    ids = {e["document_id"] for e in view["expenses"]}
    assert {m["duplicate"]["of"] for m in marked} <= ids

    # And the group id on the row is the one the resolve endpoint takes.
    assert marked[0]["duplicate"]["group_id"] == (
        view["duplicate_groups"][0]["group_id"]
    )


def test_a_row_in_no_group_carries_the_field_as_none(client, monkeypatch):
    """Parallel field, not a retyped one: a renderer reading `duplicate`
    gets null rather than a missing key on an ordinary row."""
    _wire(monkeypatch)
    batch_id = _batch(client, n_files=1)
    view = _grid(client, batch_id)
    assert view["summary"]["n_duplicate_copies"] == 0
    assert [e["duplicate"] for e in view["expenses"]] == [None]


def test_dismissing_the_group_clears_the_rows_and_the_count(
    client, monkeypatch
):
    """Two files can legitimately be one purchase billed twice. When the
    reviewer says so, the grid has to stop saying otherwise."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    gid = _grid(client, batch_id)["duplicate_groups"][0]["group_id"]

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": gid, "action": "ignore"},
    )
    assert resp.status_code == 200, resp.text

    view = _grid(client, batch_id)
    assert [e["duplicate"] for e in view["expenses"]] == [None, None]
    assert view["summary"]["n_duplicate_copies"] == 0
    # The group itself is still listed, carrying the ruling: "we looked at
    # this and it is fine" is worth keeping.
    assert view["duplicate_groups"][0]["resolution"] == "ignore"


def test_resolving_from_the_grid_replies_with_the_grids_own_summary(
    client, monkeypatch
):
    """The endpoint answered every caller with `build_view`'s summary. On an
    expense batch that is the wrong payload: none of the fields the grid
    renders its header from (`n_expenses`, `n_ready`, `n_duplicate_copies`)
    exist in it, so the SPA's header went blank on the reply to its own
    click."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    gid = _grid(client, batch_id)["duplicate_groups"][0]["group_id"]

    summary = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": gid, "action": "ignore"},
    ).json()["summary"]

    assert summary["mode"] == "expense_generation", summary
    assert summary["n_expenses"] == 2
    assert summary["n_duplicate_copies"] == 0


def test_deleting_the_extra_copy_settles_the_flag(client, monkeypatch):
    """The action the flag exists to prompt. The reviewer deletes the extra
    row; one copy is left, and one copy is not a duplicate of anything."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    view = _grid(client, batch_id)
    extra = next(e for e in view["expenses"] if e["duplicate"]["is_extra"])

    resp = client.delete(
        f"/api/runs/{batch_id}/expenses/{extra['document_id']}"
    )
    assert resp.status_code == 200, resp.text

    after = _grid(client, batch_id)
    assert after["summary"]["n_duplicate_copies"] == 0
    assert after["summary"]["n_duplicate_groups"] == 0
    assert [e["duplicate"] for e in after["expenses"]] == [None]


# ── 3. the workbench ────────────────────────────────────────────────────


def test_a_charge_billed_twice_is_marked_on_both_charge_rows(
    client, monkeypatch
):
    """The other half of the same question: not the same receipt twice, the
    same charge twice on the statement."""
    _wire(monkeypatch)
    batch_id = _batch(client, n_files=1)
    _upload(client, batch_id, _csv(
        ("2026-04-15", "135.00", "PRESSMASTER FZCO"),
        ("2026-04-16", "135.00", "PRESSMASTER FZCO"),
        ("2026-04-20", "9.99", "AWS"),
    ))

    view = client.get(f"/api/runs/{batch_id}").json()
    marked = [r for r in view["rows"] if r["duplicate"]]
    assert len(marked) == 2, [(r["vendor"], r["duplicate"]) for r in view["rows"]]
    assert {m["duplicate"]["kind"] for m in marked} == {"charge"}
    assert sorted(m["duplicate"]["is_extra"] for m in marked) == [False, True]
    assert view["summary"]["n_duplicate_copies"] == 1

    aws = next(r for r in view["rows"] if r["vendor"] == "AWS")
    assert aws["duplicate"] is None


def test_the_duplicate_receipt_is_marked_in_the_hand_match_picker(
    client, monkeypatch
):
    """`assignable_receipts` is where a reviewer picks a receipt for a
    charge by hand, and it holds every receipt including matched ones. It
    is the one place both copies of an invoice could be assigned to two
    different charges, and it is what makes `n_duplicate_copies` backed by
    rows on screen: a matched duplicate is in neither `rows` nor
    `unmatched_receipts`."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _upload(client, batch_id, _csv(("2026-04-15", "135.00", "PRESSMASTER FZCO")))

    view = client.get(f"/api/runs/{batch_id}").json()
    marked = [r for r in view["assignable_receipts"] if r["duplicate"]]
    assert len(marked) == 2, view["assignable_receipts"]
    assert sorted(m["duplicate"]["is_extra"] for m in marked) == [False, True]
    assert view["summary"]["n_duplicate_copies"] == 1

    # One of the two IS matched, so the count would have no row behind it
    # anywhere else in the payload.
    assert len(view["unmatched_receipts"]) < 2, view["unmatched_receipts"]


def test_the_same_merchant_a_month_apart_is_a_subscription_not_a_double(
    client, monkeypatch
):
    """The detector's date window doing its job, asserted here because the
    row marker is what would make a false positive expensive: a monthly
    subscription flagged as a double charge on every row, every month,
    trains the reviewer to dismiss the marker."""
    _wire(monkeypatch)
    batch_id = _batch(client, n_files=1)
    _upload(client, batch_id, _csv(
        ("2026-04-02", "9.99", "AWS"),
        ("2026-05-02", "9.99", "AWS"),
    ))

    view = client.get(f"/api/runs/{batch_id}").json()
    assert [r["duplicate"] for r in view["rows"]] == [None, None]
    assert view["summary"]["n_duplicate_copies"] == 0


# ── 4. the document ─────────────────────────────────────────────────────


def test_the_report_names_the_duplicate_instead_of_counting_it(
    client, monkeypatch, tmp_path
):
    """"2 possible duplicate groups" sends the reader to go and find them.
    The vendor, the date and the amount are what they were going to look
    for."""
    pytest.importorskip("reportlab")
    pytest.importorskip("pypdf")
    from pypdf import PdfReader

    _wire(monkeypatch)
    batch_id = _batch(client, n_files=1)
    _upload(client, batch_id, _csv(
        ("2026-04-15", "135.00", "PRESSMASTER FZCO"),
        ("2026-04-16", "135.00", "PRESSMASTER FZCO"),
    ))

    resp = client.get(f"/runs/{batch_id}/reconciliation-report.pdf")
    assert resp.status_code == 200, resp.text
    path = tmp_path / "dup.pdf"
    path.write_bytes(resp.content)
    text = " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(str(path)).pages).split()
    )
    assert "possible duplicate" in text, text[:300]
    # Between the duplicate heading and the charge listing, which is the
    # only slice the duplicate table occupies. Asserting the vendor over the
    # WHOLE document proves nothing: it is in the charge listing regardless,
    # so the assertion survived deleting the table entirely.
    section = text[text.index("possible duplicate"):text.index("All charges")]
    assert "Copies" in section, section
    assert "PRESSMASTER FZCO" in section, section
    assert "135.00" in section, section


def test_a_dismissed_group_is_not_an_exception_in_the_document(
    client, monkeypatch, tmp_path
):
    """A report that keeps raising a question the reviewer already answered
    is a report they skim."""
    pytest.importorskip("reportlab")
    pytest.importorskip("pypdf")
    from pypdf import PdfReader

    _wire(monkeypatch)
    batch_id = _batch(client, n_files=1)
    _upload(client, batch_id, _csv(
        ("2026-04-15", "135.00", "PRESSMASTER FZCO"),
        ("2026-04-16", "135.00", "PRESSMASTER FZCO"),
    ))
    view = client.get(f"/api/runs/{batch_id}").json()
    gid = next(
        g["group_id"] for g in view["duplicate_groups"] if g["kind"] == "charge"
    )
    client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": gid, "action": "ignore"},
    )

    resp = client.get(f"/runs/{batch_id}/reconciliation-report.pdf")
    path = tmp_path / "dismissed.pdf"
    path.write_bytes(resp.content)
    text = " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(str(path)).pages).split()
    )
    assert "possible duplicate" not in text, text[:300]
