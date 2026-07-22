"""JSON twins of the browser-form mutations (2026-07-21).

The Lovable SPA owns the UI; the server-rendered pages are on their way
out. Every mutation the review workflow needs is now mounted twice: the
bare path answers a browser with a 303 back to the page, the ``/api``
path answers the SPA with JSON. One handler serves both, so the two
contracts cannot drift.

The security half matters more than the convenience half. The
operator-only rules in ``auth._OPERATOR_RULES`` are ``^``-anchored path
regexes, so a twin mounted under ``/api`` escapes its rule unless the
matcher canonicalizes the prefix. Without that, the USER role (Chris)
could publish, unpublish, forget, commit memory, reset memory, and
trigger pipeline runs through the SPA surface while being correctly
blocked on the bare paths.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web import auth  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

USER_CODE = "user-code-1"
OP_CODE = "operator-code-1"


@pytest.fixture
def gated_client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_ACCESS_CODE", USER_CODE)
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    monkeypatch.setenv("EXPENSE_RECON_INSECURE_COOKIE", "1")
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _login(client, code):
    resp = client.post("/login", data={"code": code}, follow_redirects=False)
    assert resp.status_code == 303
    return resp


# ── the escalation guard ─────────────────────────────────────────────

# Operator-only on the bare path; each must stay operator-only on /api.
OPERATOR_ONLY_API = [
    "/api/runs/some-run/publish",
    "/api/runs/some-run/unpublish",
    "/api/runs/some-run/commit-memory",
    "/api/runs/some-run/forget",
    "/api/intakes/some-intake/run",
    "/api/memory/reset",
]


@pytest.mark.parametrize("path", OPERATOR_ONLY_API)
def test_user_role_cannot_reach_operator_mutations_through_api(gated_client, path):
    """The regression this guard exists for. A 200/303/404 here would mean
    the handler RAN for a user; only 403 proves the gate held."""
    _login(gated_client, USER_CODE)
    resp = gated_client.post(path, json={}, follow_redirects=False)
    assert resp.status_code == 403, f"{path} reachable by user role"
    assert resp.json()["error"] == "operator access required"


@pytest.mark.parametrize("path", OPERATOR_ONLY_API)
def test_bare_twin_is_operator_only_too(gated_client, path):
    """The bare paths were already gated; assert it so a future edit to
    the rules cannot quietly loosen one side while the other holds."""
    _login(gated_client, USER_CODE)
    bare = path[len("/api"):]
    resp = gated_client.post(bare, json={}, follow_redirects=False)
    assert resp.status_code == 403


def test_path_requires_operator_canonicalizes_the_api_prefix():
    """Unit-level: the rule matcher itself, independent of routing."""
    for bare in (
        "/runs/x/publish", "/runs/x/unpublish",
        "/runs/x/commit-memory", "/runs/x/forget",
        "/intakes/x/run", "/memory/reset", "/memory/forget",
    ):
        assert auth.path_requires_operator(bare, "POST"), bare
        assert auth.path_requires_operator("/api" + bare, "POST"), "/api" + bare


def test_canonicalization_does_not_over_restrict():
    """Stripping /api must not make previously-open paths operator-only,
    and the explicitly /api-prefixed rules must keep matching."""
    # Open to any logged-in role, on both surfaces.
    assert not auth.path_requires_operator("/feedback", "POST")
    assert not auth.path_requires_operator("/api/feedback", "POST")
    assert not auth.path_requires_operator("/runs/x/decisions", "POST")
    assert not auth.path_requires_operator("/api/runs/x/decisions", "POST")
    assert not auth.path_requires_operator("/runs/x/categories", "POST")
    assert not auth.path_requires_operator("/api/runs/x/categories", "POST")
    # Method-scoped rule stays method-scoped.
    assert auth.path_requires_operator("/api/settings", "PUT")
    assert not auth.path_requires_operator("/api/settings", "GET")
    # A rule that exists ONLY in /api form still fires (no bare equivalent).
    assert auth.path_requires_operator("/api/operator/state", "GET")


# ── the twins answer JSON, the pages still answer a browser ──────────


def test_user_can_reach_the_review_mutations_on_api(gated_client):
    """Chris's own workflow (decide, recategorize, manual-match) has to
    work for the user role on the SPA surface. The run does not exist, so
    a JSON 404 is the right answer: it proves the handler ran and produced
    JSON rather than a redirect to a login or home page."""
    _login(gated_client, USER_CODE)
    for path, body in (
        ("/api/runs/missing/decisions", {"transaction_id": "t1", "status": "confirmed"}),
        ("/api/runs/missing/categories", {"document_id": "d1", "category": "Meals"}),
        ("/api/runs/missing/manual-match", {"transaction_id": "t1", "document_id": "d1"}),
        ("/api/runs/missing/disposition", {"transaction_id": "t1", "disposition": "keep"}),
    ):
        resp = gated_client.post(path, json=body, follow_redirects=False)
        assert resp.status_code in (400, 404), (path, resp.status_code)
        assert resp.headers["content-type"].startswith("application/json"), path


def test_operator_api_publish_returns_json_not_a_redirect(gated_client):
    _login(gated_client, OP_CODE)
    resp = gated_client.post("/api/runs/missing/publish", follow_redirects=False)
    assert resp.status_code == 404
    assert resp.json() == {"error": "run not found"}


def test_bare_publish_still_redirects_the_browser(gated_client):
    """The HTML contract is unchanged while the pages are still live."""
    _login(gated_client, OP_CODE)
    resp = gated_client.post("/runs/missing/publish", follow_redirects=False)
    assert resp.status_code == 404
    assert not resp.headers["content-type"].startswith("application/json")


def test_api_memory_reset_accepts_json_and_an_empty_body(gated_client):
    _login(gated_client, OP_CODE)
    resp = gated_client.post("/api/memory/reset", follow_redirects=False)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = gated_client.post(
        "/api/memory/reset", json={"table": "merchant_category"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    assert resp.json()["table"] == "merchant_category"


def test_api_intake_upload_returns_the_intake_id(gated_client):
    """The SPA needs the id back to drive the rest of the flow; the page
    only needed a redirect home, so the id was never in the response."""
    _login(gated_client, USER_CODE)
    resp = gated_client.post(
        "/api/intakes",
        files={"statement": ("statement.csv", b"Date,Description,Amount\n", "text/csv")},
        data={"card_name": "CorpServ 2838", "month": "2026-05"},
        follow_redirects=False,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["intake_id"]
    assert "CorpServ 2838" in body["label"]


def test_bare_intake_upload_still_redirects(gated_client):
    _login(gated_client, USER_CODE)
    resp = gated_client.post(
        "/intakes",
        files={"statement": ("statement.csv", b"Date,Description,Amount\n", "text/csv")},
        data={"card_name": "CorpServ 2838", "month": "2026-05"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"


def test_api_intake_upload_reports_a_bad_file_as_json(gated_client):
    """A rejected upload has to come back as a readable error, not a
    400 HTML page the SPA cannot parse."""
    _login(gated_client, USER_CODE)
    resp = gated_client.post(
        "/api/intakes",
        files={"statement": ("statement.exe", b"nope", "application/octet-stream")},
        data={"card_name": "CorpServ 2838", "month": "2026-05"},
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["error"]


def test_api_intake_files_and_run_are_mounted(gated_client):
    """Both exist on /api and answer JSON for a missing intake (404), which
    proves routing rather than a 405 from an unmounted path."""
    _login(gated_client, OP_CODE)
    resp = gated_client.post(
        "/api/intakes/missing/files",
        files={"statement": ("s.csv", b"a,b\n", "text/csv")},
        follow_redirects=False,
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "upload not found"

    resp = gated_client.post("/api/intakes/missing/run", data={}, follow_redirects=False)
    assert resp.status_code == 404
    assert resp.json()["error"] == "upload not found"


def test_bearer_token_works_on_the_new_api_twins(gated_client):
    """The SPA authenticates with a bearer, never a cookie. The twins must
    accept it the same way the pre-existing /api routes do."""
    token = gated_client.post("/api/login", json={"code": OP_CODE}).json()["token"]
    fresh = TestClient(gated_client.app)
    resp = fresh.post(
        "/api/runs/missing/publish",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert resp.status_code == 404
    assert resp.json() == {"error": "run not found"}

    # And a USER bearer is still refused on the operator twin.
    user_token = gated_client.post("/api/login", json={"code": USER_CODE}).json()["token"]
    resp = fresh.post(
        "/api/runs/missing/publish",
        headers={"Authorization": f"Bearer {user_token}"},
        follow_redirects=False,
    )
    assert resp.status_code == 403
