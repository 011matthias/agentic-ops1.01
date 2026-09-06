"""Travel-alias mail routing + the trip join (backlog item 38, R3).

The intake gains ONE configurable setting, `intake.travel_alias` (unset
by default: the owner has not picked the local-part), and one rule: mail
addressed to that alias RESTS in the travel pool. It never consults the
month batches, never auto-joins a trip, and is claimed only by an
operator's click (`POST /api/inbound/{archive}/join-trip`) — the
suggestion a pooled row carries when exactly ONE open trip covers its
receipt dates is a reading, not a decision.

The load-bearing regression pin: with the alias configured, mail to
receipts@ behaves byte-identically to a deployment where the alias does
not exist. The travel branch keys on the To-address alone (item 38
ruling 1: declared, never inferred), so nothing else may move.
"""
from __future__ import annotations

import calendar
import json
from datetime import date, timedelta
from email.message import EmailMessage

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.intake_mail import (  # noqa: E402
    HELD_BODY_ONLY,
    HELD_FAILED,
    STATUS_INGESTED,
    STATUS_POOLED,
    IntakeConfig,
    archive_incoming,
    claim_pooled,
    inbound_root,
    normalize_intake_setting,
    parse_inbound,
    process_message,
    render_ingest,
    replay_held,
)
from expense_recon.web.service import (  # noqa: E402
    claim_trip_batch_slot,
    covering_trips,
    release_trip_batch_slot,
)
from expense_recon.web.store import RunStore, TripRow  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000
DOMAIN = "expenses.brisken.com"
OUTSIDE = "guest@example.org"

# Relative fixture dates, like test_intake_mail.py: the plausibility
# clamp must never expire this file. The receipt lands in last month.
RECEIPT_DAY = date.today().replace(day=1) - timedelta(days=20)
RECEIPT_MONTH = f"{RECEIPT_DAY.year:04d}-{RECEIPT_DAY.month:02d}"
MONTH_LABEL = f"{calendar.month_name[RECEIPT_DAY.month]} {RECEIPT_DAY.year}"
TRIP_START = (RECEIPT_DAY - timedelta(days=3)).isoformat()
TRIP_END = (RECEIPT_DAY + timedelta(days=3)).isoformat()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_INTAKE_SMTP", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        c._db_path = tmp_path / "recon-web.sqlite"
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date=RECEIPT_DAY.isoformat(), total="42.50", currency="USD",
                vendor="Trattoria", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _mail(from_addr: str, to_addr: str, attachments=None,
          body: str = "receipt attached", subject: str = "Taxi Rome") -> bytes:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Message-ID"] = "<travel-test@brisken.com>"
    msg.set_content(body)
    for name, data in attachments or []:
        maintype, subtype = (
            ("application", "pdf") if name.endswith(".pdf")
            else ("image", "jpeg")
        )
        msg.add_attachment(data, maintype=maintype, subtype=subtype,
                           filename=name)
    return msg.as_bytes()


def _set_travel_alias(client, alias: str = "travel") -> None:
    resp = client.put("/api/settings", json={
        "intake": {"travel_alias": alias},
    })
    assert resp.status_code == 200, resp.text


def _send(client, raw: bytes) -> dict:
    return process_message(
        client._db_path, None, client._data_root, raw, synchronous=True,
    )


def _make_trip(client, name="Rome 2026", start=TRIP_START, end=TRIP_END,
               travelers=("Dirk Neumann",)):
    resp = client.post("/api/trips", json={
        "name": name, "start": start, "end": end,
        "travelers": list(travelers),
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def _meta(client, archive: str) -> dict:
    return json.loads(
        (inbound_root(client._data_root) / archive / "meta.json")
        .read_text(encoding="utf-8")
    )


def _log_row(client, archive: str) -> dict:
    rows = [
        e for e in client.get("/api/inbound/log").json()["entries"]
        if e.get("archive") == archive
    ]
    assert rows, f"no log row for {archive}"
    return rows[-1]


# ── the setting ─────────────────────────────────────────────────────


def test_travel_alias_normalization():
    assert normalize_intake_setting({"travel_alias": " Reisen "}) == {
        "travel_alias": "reisen"
    }
    # "" stores as unset — the owner clears the alias by blanking it.
    assert normalize_intake_setting({"travel_alias": ""}) == {
        "travel_alias": ""
    }
    for bad in ("has space", "a@b", 7):
        with pytest.raises(ValueError):
            normalize_intake_setting({"travel_alias": bad})
    # The canonical company local would swallow the whole intake.
    with pytest.raises(ValueError, match="receipts"):
        normalize_intake_setting({"travel_alias": "receipts"})
    # A person alias in the same payload (= the stored aliases, because
    # the intake object replaces wholesale) must not be shadowed.
    with pytest.raises(ValueError, match="collides"):
        normalize_intake_setting({
            "aliases": {"dirk": "Dirk Neumann"}, "travel_alias": "dirk",
        })


def test_from_settings_belt_drops_a_bad_stored_alias():
    cfg = IntakeConfig.from_settings({"intake": {"travel_alias": "receipts"}})
    assert cfg.travel_alias == ""
    cfg = IntakeConfig.from_settings({"intake": {
        "aliases": {"dirk": "Dirk"}, "travel_alias": "dirk",
    }})
    assert cfg.travel_alias == ""
    cfg = IntakeConfig.from_settings({"intake": {"travel_alias": "reisen"}})
    assert cfg.travel_alias == "reisen"


# ── covering_trips (the suggestion rule) ────────────────────────────


def _trip_row(trip_id: str, start: str, end: str) -> TripRow:
    return TripRow(trip_id=trip_id, created_at="", name=trip_id,
                   start_date=start, end_date=end, travelers=[])


def test_covering_trips_matches_inclusive_range_only():
    inside = _trip_row("t1", "2026-09-20", "2026-09-25")
    other = _trip_row("t2", "2026-10-01", "2026-10-05")
    assert covering_trips([inside, other], ["2026-09-20"]) == [inside]
    assert covering_trips([inside, other], ["2026-09-25"]) == [inside]
    assert covering_trips([inside, other], ["2026-09-26"]) == []
    assert covering_trips([inside, other], []) == []
    assert covering_trips([inside, other], ["not-a-date"]) == []
    overlapping = _trip_row("t3", "2026-09-24", "2026-09-30")
    assert len(covering_trips([inside, other, overlapping],
                              ["2026-09-24"])) == 2


# ── routing: travel rests, receipts@ is untouched ───────────────────


def test_travel_mail_rests_even_when_its_month_is_open(
    client, monkeypatch,
):
    _set_travel_alias(client)
    # An OPEN month batch matching the receipt's printed month — the
    # exact situation where month mail would ingest immediately.
    _patch_ocr(monkeypatch, _extraction(vendor="Seed"))
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("seed.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services", "label": MONTH_LABEL},
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    _patch_ocr(monkeypatch, _extraction())
    result = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    assert result["status"] == STATUS_POOLED
    assert result["pool_kind"] == "travel"
    assert result["pool_month"] == RECEIPT_MONTH

    meta = _meta(client, result["archive"])
    assert meta["pool_kind"] == "travel"
    # The open month gained nothing, and an explicit claim sweep leaves
    # the travel mail resting.
    claim = claim_pooled(client._db_path, None, client._data_root)
    assert claim["claimed"] == 0
    assert claim["still_pooled"] == 1
    assert _meta(client, result["archive"])["status"] == STATUS_POOLED
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert grid["summary"]["n_expenses"] == 1  # the seed alone


def test_receipts_behavior_is_identical_with_and_without_the_alias(
    tmp_path_factory, monkeypatch,
):
    """The regression pin: the SAME receipts@ traffic, one app with the
    alias configured, one without. Both halves of the month path are
    compared — the POOLED outcome (no month open) and the DIRECT-INGEST
    outcome (month open) — field for field, ids and timestamps aside."""
    volatile = {"archive", "at", "job_id", "batch_id"}

    def _comparable(result, meta, row):
        return (
            {k: v for k, v in result.items() if k not in volatile},
            {k: v for k, v in meta.items()
             if k not in volatile | {"message_id", "peer"}},
            {k: v for k, v in row.items() if k not in volatile},
        )

    outcomes = []
    for configure_alias in (False, True):
        tmp = tmp_path_factory.mktemp(
            "alias-on" if configure_alias else "alias-off"
        )
        monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        app = create_app(tmp)
        with TestClient(app) as c:
            c._data_root = tmp
            c._db_path = tmp / "recon-web.sqlite"
            if configure_alias:
                _set_travel_alias(c)
            # Half 1: no month open -> the mail pools.
            _patch_ocr(monkeypatch, _extraction())
            pooled = _send(c, _mail(
                "dirk.neumann@brisken.com", f"receipts@{DOMAIN}",
                attachments=[("taxi.jpg", JPG)],
            ))
            pooled_state = _comparable(
                pooled, _meta(c, pooled["archive"]),
                _log_row(c, pooled["archive"]),
            )
            # Open the month (its create also claims the pooled mail:
            # queue = seed extraction + the claim's ingest extraction).
            _patch_ocr(monkeypatch, _extraction(vendor="Seed"),
                       _extraction())
            resp = c.post(
                "/api/expense-batches",
                files=[("files",
                        ("seed.jpg", JPG + b"s", "application/octet-stream"))],
                data={"legal_entity": "Corporate Services",
                      "label": MONTH_LABEL},
            )
            assert resp.status_code == 200, resp.text
            assert c.get(
                f"/jobs/{resp.json()['job_id']}"
            ).json()["status"] == "done"
            # Half 2: month open -> the mail direct-ingests.
            _patch_ocr(monkeypatch,
                       _extraction(vendor="Cafe", total="9.00"),
                       _extraction(vendor="Cafe", total="9.00"))
            ingested = _send(c, _mail(
                "dirk.neumann@brisken.com", f"receipts@{DOMAIN}",
                attachments=[("cafe.jpg", JPG + b"c", )],
                subject="Cafe",
            ))
            ingested_state = _comparable(
                ingested, _meta(c, ingested["archive"]),
                _log_row(c, ingested["archive"]),
            )
        outcomes.append((pooled_state, ingested_state))
    assert outcomes[0] == outcomes[1]
    # And the shared shapes are the month path, never the travel pool.
    assert outcomes[0][0][0]["status"] == STATUS_POOLED
    assert "pool_kind" not in {
        k for k, v in outcomes[0][0][1].items() if v
    }
    assert outcomes[0][1][1]["status"] == STATUS_INGESTED


def test_unset_alias_routes_travel_named_mail_as_ordinary(
    client, monkeypatch,
):
    """No alias configured => a mail to travel@ is just an unknown local
    at our domain: ordinary month routing, no travel stamp."""
    _patch_ocr(monkeypatch, _extraction())
    result = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    assert result["status"] == STATUS_POOLED
    assert "pool_kind" not in result
    # Routed non-travel writes the empty stamp ("" = decided, not
    # travel); only an unrouted archive lacks the key entirely.
    assert not _meta(client, result["archive"]).get("pool_kind")


# ── the pooled row: suggestion + labels + counts ────────────────────


def test_travel_row_suggestion_fires_on_exactly_one_covering_trip(
    client, monkeypatch,
):
    _set_travel_alias(client)
    _patch_ocr(monkeypatch, _extraction())
    result = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    archive = result["archive"]

    # Zero trips: honest blank, the waiting label.
    body = client.get("/api/inbound/log").json()
    row = [e for e in body["entries"] if e.get("archive") == archive][-1]
    assert row["pool_kind"] == "travel"
    assert "trip_suggestion" not in row
    assert "pool_month_state" not in row
    assert row["status_label"] == "Travel, waiting for its trip"
    assert body["n_pooled_travel"] == 1
    assert body["n_pooled"] == 1

    # Exactly one covering trip: named, as a reading.
    trip = _make_trip(client)
    row = _log_row(client, archive)
    assert row["trip_suggestion"]["trip_id"] == trip["trip_id"]
    assert row["trip_suggestion"]["name"] == "Rome 2026"
    assert row["status_label"] == 'Travel; reads as "Rome 2026"'

    # A second covering trip: ambiguity surfaces as absence.
    _make_trip(client, name="Milan 2026")
    row = _log_row(client, archive)
    assert "trip_suggestion" not in row
    assert row["status_label"] == "Travel, waiting for its trip"


# ── the join ────────────────────────────────────────────────────────


def test_join_creates_the_trip_batch_with_the_mailed_receipt(
    client, monkeypatch,
):
    _set_travel_alias(client)
    trip = _make_trip(client)
    _patch_ocr(monkeypatch, _extraction(), _extraction())
    result = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    resp = client.post(
        f"/api/inbound/{result['archive']}/join-trip",
        json={"trip_id": trip["trip_id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created_batch"] is True
    assert body["documents"], body

    meta = _meta(client, result["archive"])
    assert meta["status"] == STATUS_INGESTED
    assert meta["batch_id"] == body["batch_id"]

    # The batch is the trip's (declared type, label = trip name), holds
    # the mailed receipt with its submitter, and stays off /months.
    grid = client.get(f"/api/expense-batches/{body['batch_id']}").json()
    assert grid["batch_type"] == "trip"
    assert grid["trip"]["trip_id"] == trip["trip_id"]
    assert grid["label"] == "Rome 2026"
    assert grid["summary"]["n_expenses"] == 1
    submitted = grid["expenses"][0]["submitted_by"]
    assert submitted["address"] == "dirk.neumann@brisken.com"
    months = client.get("/api/expense-batches").json()["batches"]
    assert body["batch_id"] not in [b["batch_id"] for b in months]
    trips = client.get("/api/trips").json()["trips"]
    assert trips[0]["batch_id"] == body["batch_id"]


def test_second_join_appends_to_the_existing_trip_batch(
    client, monkeypatch,
):
    _set_travel_alias(client)
    trip = _make_trip(client)
    _patch_ocr(monkeypatch, _extraction(), _extraction())
    first = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    r1 = client.post(f"/api/inbound/{first['archive']}/join-trip",
                     json={"trip_id": trip["trip_id"]})
    assert r1.status_code == 200, r1.text

    _patch_ocr(monkeypatch, _extraction(vendor="Hotel", total="99.00"),
               _extraction(vendor="Hotel", total="99.00"))
    second = _send(client, _mail(
        "criss@brisken.com", f"travel@{DOMAIN}",
        attachments=[("hotel.jpg", JPG + b"2")], subject="Hotel Rome",
    ))
    r2 = client.post(f"/api/inbound/{second['archive']}/join-trip",
                     json={"trip_id": trip["trip_id"]})
    assert r2.status_code == 200, r2.text
    assert "created_batch" not in r2.json()
    assert r2.json()["batch_id"] == r1.json()["batch_id"]
    grid = client.get(f"/api/expense-batches/{r1.json()['batch_id']}").json()
    assert grid["summary"]["n_expenses"] == 2


def test_join_guards(client, monkeypatch):
    _set_travel_alias(client)
    trip = _make_trip(client)
    # Month mail (no travel stamp) may not be pushed onto a trip.
    _patch_ocr(monkeypatch, _extraction())
    month_mail = _send(client, _mail(
        "dirk.neumann@brisken.com", f"receipts@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    resp = client.post(f"/api/inbound/{month_mail['archive']}/join-trip",
                       json={"trip_id": trip["trip_id"]})
    assert resp.status_code == 409
    assert "travel" in resp.json()["error"]

    _patch_ocr(monkeypatch, _extraction())
    travel_mail = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("t2.jpg", JPG + b"9")],
    ))
    assert client.post(
        f"/api/inbound/{travel_mail['archive']}/join-trip",
        json={"trip_id": "nope"},
    ).status_code == 404
    assert client.post(
        f"/api/inbound/{travel_mail['archive']}/join-trip", json={},
    ).status_code == 400
    assert client.post(
        "/api/inbound/20990101T000000-deadbeef/join-trip",
        json={"trip_id": trip["trip_id"]},
    ).status_code == 404

    # A joined mail cannot be joined twice.
    _patch_ocr(monkeypatch, _extraction())
    ok = client.post(f"/api/inbound/{travel_mail['archive']}/join-trip",
                     json={"trip_id": trip["trip_id"]})
    assert ok.status_code == 200, ok.text
    again = client.post(f"/api/inbound/{travel_mail['archive']}/join-trip",
                        json={"trip_id": trip["trip_id"]})
    assert again.status_code == 409


# ── plus-addressing + multi-recipient (findings 4 + 9b) ─────────────


def test_plus_tag_on_the_travel_alias_is_still_travel(client, monkeypatch):
    _set_travel_alias(client)
    _patch_ocr(monkeypatch, _extraction())
    result = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel+rome2026@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    assert result["status"] == STATUS_POOLED
    assert result.get("pool_kind") == "travel"


def test_receipts_plus_travel_tag_stays_month_mail(client, monkeypatch):
    """receipts+X@ is the person-tag convention; a tag that happens to
    spell the travel alias does not reroute the company intake."""
    _set_travel_alias(client)
    _patch_ocr(monkeypatch, _extraction())
    result = _send(client, _mail(
        "dirk.neumann@brisken.com", f"receipts+travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    assert result["status"] == STATUS_POOLED
    assert "pool_kind" not in result
    assert not _meta(client, result["archive"]).get("pool_kind")


def test_mail_addressed_to_both_intakes_is_travel(client, monkeypatch):
    """To receipts@ AND Cc travel@: travel wins, pinned. Resting in the
    travel pool is one click to recover; auto-ingesting into a month
    against the sender's travel flag is the worse error."""
    _set_travel_alias(client)
    _patch_ocr(monkeypatch, _extraction())
    raw = _mail(
        "dirk.neumann@brisken.com", f"receipts@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ).replace(b"Subject:", f"Cc: travel@{DOMAIN}\nSubject:".encode(), 1)
    result = _send(client, raw)
    assert result["status"] == STATUS_POOLED
    assert result.get("pool_kind") == "travel"


# ── crash recovery keeps the address's meaning (finding 3) ──────────


def test_replay_re_derives_travel_for_a_pre_routing_crash(
    client, monkeypatch,
):
    """Custody taken (250 sent), router died BEFORE the routing CAS: no
    pool_kind stamp exists. Replay must re-derive travel from the
    archived base locals rather than month-routing blind."""
    _set_travel_alias(client)
    raw = _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    )
    parsed = parse_inbound(raw, DOMAIN)
    arch = archive_incoming(client._data_root, raw, parsed)
    # Age the `received` stamp past the stale threshold so replay takes it.
    meta_path = arch / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "pool_kind" not in meta  # the crash left no routing stamp
    meta["at"] = "2026-01-01T00:00:00+00:00"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    _patch_ocr(monkeypatch, _extraction())
    swept = replay_held(client._db_path, None, client._data_root)
    assert swept["pooled"] == 1
    final = _meta(client, arch.name)
    assert final["status"] == STATUS_POOLED
    assert final["pool_kind"] == "travel"


# ── the join under contention (findings 1, 2, 5) ────────────────────


def test_join_refuses_while_an_upload_is_creating_the_batch(
    client, monkeypatch,
):
    _set_travel_alias(client)
    trip = _make_trip(client)
    _patch_ocr(monkeypatch, _extraction())
    result = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    with RunStore(client._db_path) as store:
        assert claim_trip_batch_slot(store, trip["trip_id"]) is None
    try:
        resp = client.post(
            f"/api/inbound/{result['archive']}/join-trip",
            json={"trip_id": trip["trip_id"]},
        )
        assert resp.status_code == 409
        assert "being created" in resp.json()["error"]
        # The mail went back to RESTING, so the next click works.
        assert _meta(client, result["archive"])["status"] == STATUS_POOLED
    finally:
        release_trip_batch_slot(trip["trip_id"])
    _patch_ocr(monkeypatch, _extraction())
    ok = client.post(f"/api/inbound/{result['archive']}/join-trip",
                     json={"trip_id": trip["trip_id"]})
    assert ok.status_code == 200, ok.text


def test_failed_append_join_returns_the_mail_to_the_pool(
    client, monkeypatch,
):
    """A staging/disk failure on the APPEND branch must not strand the
    archive in `claiming` (the create branch already guards this)."""
    _set_travel_alias(client)
    trip = _make_trip(client)
    _patch_ocr(monkeypatch, _extraction(), _extraction())
    first = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    ok = client.post(f"/api/inbound/{first['archive']}/join-trip",
                     json={"trip_id": trip["trip_id"]})
    assert ok.status_code == 200, ok.text

    _patch_ocr(monkeypatch, _extraction(vendor="Hotel"))
    second = _send(client, _mail(
        "criss@brisken.com", f"travel@{DOMAIN}",
        attachments=[("hotel.jpg", JPG + b"2")], subject="Hotel",
    ))

    def _boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr("expense_recon.web.intake_mail._start_ingest", _boom)
    resp = client.post(f"/api/inbound/{second['archive']}/join-trip",
                       json={"trip_id": trip["trip_id"]})
    assert resp.status_code == 500
    final = _meta(client, second["archive"])
    assert final["status"] == STATUS_POOLED
    assert "disk full" in final.get("error", "")


# ── the other roads into the pool stay travel-aware ─────────────────


def test_rendered_travel_body_mail_pools_as_travel(client, monkeypatch):
    _set_travel_alias(client)
    result = _send(client, _mail(
        OUTSIDE, f"travel@{DOMAIN}", attachments=[],
        body="Your ride receipt: EUR 23.50",
    ))
    assert result["status"] == HELD_BODY_ONLY
    assert _meta(client, result["archive"])["pool_kind"] == "travel"

    _patch_ocr(monkeypatch, _extraction())
    rendered = render_ingest(
        client._db_path, None, client._data_root, result["archive"],
        operator="op",
    )
    assert rendered["status"] == STATUS_POOLED
    assert rendered["pool_kind"] == "travel"
    assert _meta(client, result["archive"])["status"] == STATUS_POOLED


def test_replay_returns_stuck_travel_mail_to_the_pool(client, monkeypatch):
    _set_travel_alias(client)
    _patch_ocr(monkeypatch, _extraction())
    result = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    arch = inbound_root(client._data_root) / result["archive"]
    meta = json.loads((arch / "meta.json").read_text(encoding="utf-8"))
    meta["status"] = HELD_FAILED  # a crashed join / router
    (arch / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    swept = replay_held(client._db_path, None, client._data_root)
    assert swept["pooled"] == 1
    assert swept["replayed"] == 0
    assert _meta(client, result["archive"])["status"] == STATUS_POOLED


def test_travel_ack_names_the_trip_review_not_the_month_join(
    client, monkeypatch,
):
    sent = []
    monkeypatch.setattr(
        "expense_recon.web.graph_notify.enabled", lambda: True
    )
    monkeypatch.setattr(
        "expense_recon.web.graph_notify.send_mail",
        lambda rcpt, subject, body, **kw: sent.append(body) or True,
    )
    _set_travel_alias(client)
    _patch_ocr(monkeypatch, _extraction())
    result = _send(client, _mail(
        "dirk.neumann@brisken.com", f"travel@{DOMAIN}",
        attachments=[("taxi.jpg", JPG)],
    ))
    assert result["status"] == STATUS_POOLED
    assert sent, "pooled travel mail must still be acked"
    assert "travel receipts" in sent[-1]
    assert "join that month's" not in sent[-1]
    # Finding 7: the review promise and the signature both follow the
    # address the sender used, never the month run / receipts@.
    assert "trip's expenses" in sent[-1]
    assert "monthly run" not in sent[-1]
    assert f"travel@{DOMAIN}" in sent[-1]
