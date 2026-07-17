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


# ── Replace / late-add files on a queued intake (2026-07-16 feedback:
# "tem que ter opcao para tirar o arquivo que foi colocado errado") ──


def _one_intake(client, **kw):
    resp = client.post(
        "/intakes",
        files=_files(**kw),
        data={"card_name": "Corporate card 2838", "month": "2026-06"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        return store.list_intakes()[0]


def test_replace_receipts_on_received_intake(client):
    intake = _one_intake(client)
    old_name = intake.receipts_name
    resp = client.post(
        f"/intakes/{intake.intake_id}/files",
        files={"receipts": ("expense-report.pdf", b"%PDF-1.4 replacement", "application/pdf")},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        updated = store.get_intake(intake.intake_id)
    assert updated.receipts_name == "expense-report.pdf"
    work = Path(updated.work_dir)
    assert (work / "expense-report.pdf").read_bytes() == b"%PDF-1.4 replacement"
    assert not (work / old_name).exists()          # the wrong file is gone
    assert updated.statement_name == intake.statement_name  # untouched


def test_late_add_receipts_to_waiting_intake(client):
    intake = _one_intake(client, receipts=False)
    assert intake.receipts_name is None
    resp = client.post(
        f"/intakes/{intake.intake_id}/files",
        files={"receipts": (
            "receipts.example.csv",
            (EXAMPLES / "receipts.example.csv").read_bytes(),
            "text/csv",
        )},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        updated = store.get_intake(intake.intake_id)
    assert updated.receipts_name == "receipts.example.csv"


def test_replace_statement_refreshes_detect_note(client):
    intake = _one_intake(client)
    resp = client.post(
        f"/intakes/{intake.intake_id}/files",
        files={"statement": ("chase.pdf", b"%PDF-1.4 stmt", "application/pdf")},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        updated = store.get_intake(intake.intake_id)
    assert updated.statement_name == "chase.pdf"
    assert "Chase PDF" in (updated.detect_note or "")
    # the original statement file was cleaned up
    assert not (Path(updated.work_dir) / intake.statement_name).exists()


def test_replace_rejects_wrong_receipts_extension(client):
    intake = _one_intake(client)
    resp = client.post(
        f"/intakes/{intake.intake_id}/files",
        files={"receipts": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
    assert ".csv export or a Zoho Expense report .pdf" in resp.text
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        unchanged = store.get_intake(intake.intake_id)
    assert unchanged.receipts_name == intake.receipts_name


def test_replace_with_no_files_is_form_error(client):
    intake = _one_intake(client)
    resp = client.post(f"/intakes/{intake.intake_id}/files")
    assert resp.status_code == 400
    assert "at least one file" in resp.text.lower()


def test_replace_blocked_once_processing(client):
    from expense_recon.web.store import INTAKE_PROCESSING

    intake = _one_intake(client)
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        store.set_intake_status(
            intake.intake_id, INTAKE_PROCESSING, updated_at="2026-07-17T00:00:00"
        )
    resp = client.post(
        f"/intakes/{intake.intake_id}/files",
        files={"receipts": ("r.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 400
    assert "already being processed" in resp.text


def test_replace_unknown_intake_404(client):
    resp = client.post(
        "/intakes/deadbeef/files",
        files={"receipts": ("r.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert resp.status_code == 404


def test_user_home_shows_swap_control_on_received_intake(tmp_path, monkeypatch):
    """The replace form renders on the USER home for a queued intake, and
    disappears once the intake leaves `received`."""
    from expense_recon.web.store import INTAKE_READY

    monkeypatch.setenv("EXPENSE_RECON_ACCESS_CODE", "user-code-1")
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", "operator-code-1")
    monkeypatch.setenv("EXPENSE_RECON_INSECURE_COOKIE", "1")
    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.post("/login", data={"code": "user-code-1"}, follow_redirects=False)
        assert resp.status_code == 303
        c.post(
            "/intakes",
            files=_files(),
            data={"card_name": "Corporate card 2838"},
            follow_redirects=False,
        )
        html = c.get("/").text
        assert "Sent the wrong file? Replace it here." in html
        assert "/files" in html

        with RunStore(tmp_path / "recon-web.sqlite") as store:
            intake = store.list_intakes()[0]
            store.set_intake_status(
                intake.intake_id, INTAKE_READY, updated_at="2026-07-17T00:00:00"
            )
        html = c.get("/").text
        assert "Sent the wrong file? Replace it here." not in html
