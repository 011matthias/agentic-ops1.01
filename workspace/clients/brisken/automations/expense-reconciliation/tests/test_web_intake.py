"""Testing-mode intake: POST /intakes saves the documents WITHOUT running
the pipeline; the operator queue lists them with the auto-detect advisory."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import INTAKE_RECEIVED, RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _files(receipts: bool = True):
    files = {
        "statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(),
            "text/csv",
        ),
    }
    if receipts:
        files["receipts"] = (
            "receipts.example.csv",
            (EXAMPLES / "receipts.example.csv").read_bytes(),
            "text/csv",
        )
    return files


def test_intake_saves_files_and_row_without_running(client):
    resp = client.post(
        "/intakes",
        files=_files(),
        data={"card_name": "Corporate card 2838", "month": "2026-06"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        intakes = store.list_intakes()
        runs = store.list_runs()
    assert len(intakes) == 1
    intake = intakes[0]
    assert intake.status == INTAKE_RECEIVED
    assert intake.label == "Corporate card 2838 2026-06"
    assert "column map auto-detected" in (intake.detect_note or "")
    # files persisted in the intake work dir
    work = Path(intake.work_dir)
    assert (work / intake.statement_name).stat().st_size > 0
    assert (work / intake.receipts_name).stat().st_size > 0
    # crucially: NO pipeline run happened
    assert runs == []


def test_intake_without_receipts_is_accepted_and_flagged(client):
    resp = client.post(
        "/intakes",
        files=_files(receipts=False),
        data={"card_name": "Corporate card 2838"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        intake = store.list_intakes()[0]
    assert intake.receipts_name is None


def test_intake_requires_card_label(client):
    resp = client.post("/intakes", files=_files(), data={"month": "2026-06"})
    assert resp.status_code == 400
    assert "which card" in resp.text.lower()


def test_intake_rejects_wrong_statement_extension(client):
    resp = client.post(
        "/intakes",
        files={"statement": ("notes.txt", b"hello", "text/plain")},
        data={"card_name": "Corporate card 2838"},
    )
    assert resp.status_code == 400
    assert ".csv, .xlsx or .pdf" in resp.text


def test_intake_accepts_pdf_receipts(client):
    """Chris's real artifact (2026-07-16): the Zoho Expense report PDF,
    not only the extracted-fields CSV."""
    resp = client.post(
        "/intakes",
        files={
            "statement": (
                "statement.example.csv",
                (EXAMPLES / "statement.example.csv").read_bytes(),
                "text/csv",
            ),
            "receipts": ("expense-report.pdf", b"%PDF-1.4 synthetic", "application/pdf"),
        },
        data={"card_name": "Corporate card 2838", "month": "2026-06"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        intake = store.list_intakes()[0]
    assert intake.receipts_name == "expense-report.pdf"


def test_intake_rejects_wrong_receipts_extension(client):
    resp = client.post(
        "/intakes",
        files={
            "statement": (
                "statement.example.csv",
                (EXAMPLES / "statement.example.csv").read_bytes(),
                "text/csv",
            ),
            "receipts": ("notes.txt", b"hello", "text/plain"),
        },
        data={"card_name": "Corporate card 2838"},
    )
    assert resp.status_code == 400
    assert ".csv export or a Zoho Expense report .pdf" in resp.text


def test_undetectable_statement_still_accepted_with_note(client):
    resp = client.post(
        "/intakes",
        files={
            "statement": ("weird.csv", b"colA,colB\n1,2\n", "text/csv"),
            "receipts": (
                "receipts.example.csv",
                (EXAMPLES / "receipts.example.csv").read_bytes(),
                "text/csv",
            ),
        },
        data={"card_name": "Corporate card 2838"},
        follow_redirects=False,
    )
    # Detection failure is advisory, never a wall in front of the uploader.
    assert resp.status_code == 303, resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        intake = store.list_intakes()[0]
    assert "missing" in (intake.detect_note or "") or "failed" in (
        intake.detect_note or ""
    )


def test_card_preset_fills_label_and_key(client, tmp_path, monkeypatch):
    cards = {
        "cards": [
            {
                "key": "corp-2838",
                "label": "Corporate card ending 2838",
                "account_id": "card-2838",
                "legal_entity": "Corporate Services",
                "currency": "USD",
            }
        ]
    }
    cards_path = tmp_path / "cards.json"
    cards_path.write_text(json.dumps(cards), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_CARDS", str(cards_path))
    resp = client.post(
        "/intakes",
        files=_files(),
        data={"card_key": "corp-2838", "month": "2026-06"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        intake = store.list_intakes()[0]
    assert intake.card_key == "corp-2838"
    assert intake.label == "Corporate card ending 2838 2026-06"


def test_operator_queue_lists_intake(client):
    client.post(
        "/intakes",
        files=_files(),
        data={"card_name": "Corporate card 2838", "month": "2026-06"},
        follow_redirects=False,
    )
    resp = client.get("/")  # gate disabled => operator home
    assert resp.status_code == 200
    assert "Intake queue" in resp.text
    assert "Corporate card 2838 2026-06" in resp.text
    assert "Prepare run" in resp.text
