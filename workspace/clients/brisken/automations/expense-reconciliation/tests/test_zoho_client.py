"""ZohoClient tests — mocked transport, no network (slice 4.7)."""
from __future__ import annotations

import json

import pytest

from expense_recon.zoho.client import (
    ZohoAPIError,
    ZohoAuthError,
    ZohoConfig,
    ZohoClient,
)


def _cfg() -> ZohoConfig:
    return ZohoConfig(
        client_id="cid", client_secret="csecret",
        refresh_token="rtok", org_id="999",
    )


class FakeHttp:
    """Scriptable transport. Records calls; pops queued responses, or
    falls back to a default keyed by (method, path-substring)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url))
        status, payload = self._responses.pop(0)
        return status, payload


_TOKEN_OK = (200, {"access_token": "atok", "expires_in": 3600})


def test_refreshes_token_then_calls_api():
    http = FakeHttp([
        _TOKEN_OK,
        (200, {"code": 0, "organizations": [{"organization_id": "999", "name": "TEST"}]}),
    ])
    client = ZohoClient(_cfg(), http=http)

    orgs = client.list_organizations()

    assert orgs[0]["name"] == "TEST"
    # First call is the token refresh, second carries the bearer token.
    assert http.calls[0][0] == "POST" and "oauth/v2/token" in http.calls[0][1]
    assert "organizations" in http.calls[1][1]


def test_token_is_cached_across_calls():
    http = FakeHttp([
        _TOKEN_OK,
        (200, {"code": 0, "organizations": []}),
        (200, {"code": 0, "chartofaccounts": [], "page_context": {"has_more_page": False}}),
    ])
    client = ZohoClient(_cfg(), http=http)

    client.list_organizations()
    client.list_chart_of_accounts()

    # Exactly one token refresh for two API calls (3 HTTP calls total).
    refreshes = [c for c in http.calls if "oauth/v2/token" in c[1]]
    assert len(refreshes) == 1


def test_token_refreshes_after_expiry():
    clock = {"t": 0.0}
    http = FakeHttp([
        (200, {"access_token": "a1", "expires_in": 3600}),
        (200, {"code": 0, "organizations": []}),
        (200, {"access_token": "a2", "expires_in": 3600}),
        (200, {"code": 0, "organizations": []}),
    ])
    client = ZohoClient(_cfg(), http=http, clock=lambda: clock["t"])

    client.list_organizations()
    clock["t"] = 4000.0  # past the 3600s - 60s safety window
    client.list_organizations()

    refreshes = [c for c in http.calls if "oauth/v2/token" in c[1]]
    assert len(refreshes) == 2


def test_chart_of_accounts_follows_pagination():
    http = FakeHttp([
        _TOKEN_OK,
        (200, {"code": 0, "chartofaccounts": [{"account_name": "A"}],
               "page_context": {"has_more_page": True}}),
        (200, {"code": 0, "chartofaccounts": [{"account_name": "B"}],
               "page_context": {"has_more_page": False}}),
    ])
    client = ZohoClient(_cfg(), http=http)

    accounts = client.list_chart_of_accounts()

    assert [a["account_name"] for a in accounts] == ["A", "B"]


def test_org_id_injected_into_query():
    http = FakeHttp([_TOKEN_OK, (200, {"code": 0, "organizations": []})])
    client = ZohoClient(_cfg(), http=http)
    client.list_organizations()
    assert "organization_id=999" in http.calls[1][1]


def test_auth_error_on_bad_refresh_token():
    http = FakeHttp([(400, {"error": "invalid_code"})])
    client = ZohoClient(_cfg(), http=http)
    with pytest.raises(ZohoAuthError):
        client.list_organizations()


def test_api_error_on_nonzero_zoho_code():
    http = FakeHttp([_TOKEN_OK, (200, {"code": 4, "message": "no permission"})])
    client = ZohoClient(_cfg(), http=http)
    with pytest.raises(ZohoAPIError) as exc:
        client.list_chart_of_accounts()
    assert exc.value.code == 4


def test_list_expenses_follows_pagination():
    http = FakeHttp([
        _TOKEN_OK,
        (200, {"code": 0, "expenses": [{"vendor_name": "A", "date": "2026-01-05"}],
               "page_context": {"has_more_page": True}}),
        (200, {"code": 0, "expenses": [{"vendor_name": "B", "date": "2026-02-05"}],
               "page_context": {"has_more_page": False}}),
    ])
    client = ZohoClient(_cfg(), http=http)

    expenses = client.list_expenses()

    assert [e["vendor_name"] for e in expenses] == ["A", "B"]
    assert "/books/v3/expenses" in http.calls[1][1]
    assert "organization_id=999" in http.calls[1][1]


def test_list_expenses_filters_dates_client_side():
    # One page carrying records around the window; the filter happens on
    # OUR side (Zoho's own list filters are inconsistent across DCs), so
    # the request itself carries no date params.
    http = FakeHttp([
        _TOKEN_OK,
        (200, {"code": 0, "expenses": [
            {"vendor_name": "too-early", "date": "2025-12-31"},
            {"vendor_name": "in-window", "date": "2026-01-15"},
            {"vendor_name": "on-edge", "date": "2026-02-28"},
            {"vendor_name": "too-late", "date": "2026-03-01"},
            {"vendor_name": "undated"},
        ], "page_context": {"has_more_page": False}}),
    ])
    client = ZohoClient(_cfg(), http=http)

    expenses = client.list_expenses(date_start="2026-01-01", date_end="2026-02-28")

    assert [e["vendor_name"] for e in expenses] == ["in-window", "on-edge"]
    assert "date" not in http.calls[1][1]  # no date params sent to Zoho


def test_list_expenses_api_error():
    http = FakeHttp([_TOKEN_OK, (200, {"code": 57, "message": "no scope"})])
    client = ZohoClient(_cfg(), http=http)
    with pytest.raises(ZohoAPIError) as exc:
        client.list_expenses()
    assert exc.value.code == 57


def test_from_env_reports_all_missing_at_once():
    with pytest.raises(ValueError) as exc:
        ZohoConfig.from_env(env={"ZOHO_CLIENT_ID": "x"})
    msg = str(exc.value)
    assert "ZOHO_CLIENT_SECRET" in msg
    assert "ZOHO_REFRESH_TOKEN" in msg
    assert "ZOHO_ORG_ID" in msg


def test_from_env_builds_config_and_defaults_us_domain():
    cfg = ZohoConfig.from_env(env={
        "ZOHO_CLIENT_ID": "cid", "ZOHO_CLIENT_SECRET": "sec",
        "ZOHO_REFRESH_TOKEN": "rt", "ZOHO_ORG_ID": "1",
    })
    assert cfg.api_domain == "https://www.zohoapis.com"
    assert cfg.accounts_domain == "https://accounts.zoho.com"


# ── slice 4b: create_journal + list_journals ─────────────────────────


class RecordingHttp(FakeHttp):
    """FakeHttp that also records request bodies (the 4b POST tests
    assert on the exact JSON sent)."""

    def __init__(self, responses):
        super().__init__(responses)
        self.requests: list[tuple[str, str, bytes | None]] = []

    def __call__(self, method, url, headers, body):
        self.requests.append((method, url, body))
        return super().__call__(method, url, headers, body)


def test_create_journal_posts_json_and_returns_journal():
    http = RecordingHttp([
        _TOKEN_OK,
        (201, {"code": 0, "journal": {"journal_id": "J9", "entry_number": "JE-4"}}),
    ])
    client = ZohoClient(_cfg(), http=http)
    payload = {
        "journal_date": "2026-04-03",
        "reference_number": "t1",
        "status": "draft",
        "line_items": [
            {"account_id": "111", "amount": 180.0, "debit_or_credit": "debit"},
            {"account_id": "222", "amount": 180.0, "debit_or_credit": "credit"},
        ],
    }
    journal = client.create_journal(payload)
    assert journal["journal_id"] == "J9"
    method, url, body = http.requests[1]
    assert method == "POST" and "/books/v3/journals" in url
    assert "organization_id=999" in url
    assert json.loads(body.decode("utf-8")) == payload


def test_create_journal_api_error_carries_status_and_code():
    http = FakeHttp([_TOKEN_OK, (400, {"code": 15, "message": "invalid account"})])
    client = ZohoClient(_cfg(), http=http)
    with pytest.raises(ZohoAPIError) as exc:
        client.create_journal({"journal_date": "2026-04-03", "line_items": []})
    assert exc.value.status == 400
    assert exc.value.code == 15


def test_create_journal_success_without_journal_id_raises():
    # Accepted but unconfirmable: the 4.8 caller must be able to file
    # this as ambiguous, so it MUST surface as an error, not a success.
    http = FakeHttp([_TOKEN_OK, (201, {"code": 0, "message": "ok"})])
    client = ZohoClient(_cfg(), http=http)
    with pytest.raises(ZohoAPIError) as exc:
        client.create_journal({"journal_date": "2026-04-03", "line_items": []})
    assert exc.value.status is None


def test_list_journals_paginates_and_filters_client_side():
    http = FakeHttp([
        _TOKEN_OK,
        (200, {"code": 0, "journals": [
            {"reference_number": "t1", "journal_date": "2026-04-01"},
            {"reference_number": "t2", "journal_date": "2026-05-01"},
        ], "page_context": {"has_more_page": True}}),
        (200, {"code": 0, "journals": [
            {"reference_number": "t3", "journal_date": "2026-04-15"},
        ], "page_context": {"has_more_page": False}}),
    ])
    client = ZohoClient(_cfg(), http=http)
    journals = client.list_journals(date_start="2026-04-01", date_end="2026-04-30")
    assert [j["reference_number"] for j in journals] == ["t1", "t3"]
    assert "date" not in http.calls[1][1]  # filtering is client-side


# ── month-end injection: create_expense + list_contacts ──────────────
# Dirk needs the reconciled month in Zoho Books at month end (2026-09-22);
# the expense is the unit that lands, where the journal was the old shape.


def test_create_expense_posts_json_and_returns_expense():
    http = RecordingHttp([
        _TOKEN_OK,
        (201, {"code": 0, "expense": {"expense_id": "E7", "total": 412.5}}),
    ])
    client = ZohoClient(_cfg(), http=http)
    payload = {
        "date": "2026-09-08",
        "account_id": "4369050000000078289",
        "paid_through_account_id": "4369050000000320002",
        "amount": 412.5,
        "reference_number": "8841-2026-09",
        "description": "[External Match Audit] Bank Line ID: 8841 | ...",
    }
    expense = client.create_expense(payload)
    assert expense["expense_id"] == "E7"
    method, url, body = http.requests[1]
    assert method == "POST" and "/books/v3/expenses" in url
    assert "organization_id=999" in url
    assert json.loads(body.decode("utf-8")) == payload


def test_create_expense_api_error_carries_status_and_code():
    http = FakeHttp([_TOKEN_OK, (400, {"code": 1002, "message": "invalid account"})])
    client = ZohoClient(_cfg(), http=http)
    with pytest.raises(ZohoAPIError) as exc:
        client.create_expense({"date": "2026-09-08", "amount": 1})
    assert exc.value.status == 400
    assert exc.value.code == 1002


def test_create_expense_success_without_expense_id_raises():
    # Accepted but unconfirmable. Without an expense_id the caller cannot
    # record what it created, so a re-run could post the same charge twice.
    # That is precisely what the ledger exists to prevent, so this must
    # surface as an error the caller files as ambiguous, never as success.
    http = FakeHttp([_TOKEN_OK, (201, {"code": 0, "message": "ok"})])
    client = ZohoClient(_cfg(), http=http)
    with pytest.raises(ZohoAPIError) as exc:
        client.create_expense({"date": "2026-09-08", "amount": 1})
    assert exc.value.status is None


def test_list_contacts_paginates_and_filters_type_client_side():
    http = FakeHttp([
        _TOKEN_OK,
        (200, {"code": 0, "contacts": [
            {"contact_id": "c1", "contact_name": "OpenAI", "contact_type": "vendor"},
            {"contact_id": "c2", "contact_name": "A Client", "contact_type": "customer"},
        ], "page_context": {"has_more_page": True}}),
        (200, {"code": 0, "contacts": [
            {"contact_id": "c3", "contact_name": "AWS", "contact_type": "Vendor"},
        ], "page_context": {"has_more_page": False}}),
    ])
    client = ZohoClient(_cfg(), http=http)
    vendors = client.list_contacts(contact_type="vendor")
    # c3 proves the match is case-insensitive; c2 proves the filter bites.
    assert [c["contact_id"] for c in vendors] == ["c1", "c3"]
    # Filtering client-side, because a filter Zoho silently ignores would
    # answer confidently for the whole workspace.
    assert "contact_type" not in http.calls[1][1]


def test_list_contacts_unfiltered_returns_every_type():
    http = FakeHttp([
        _TOKEN_OK,
        (200, {"code": 0, "contacts": [
            {"contact_id": "c1", "contact_type": "vendor"},
            {"contact_id": "c2", "contact_type": "customer"},
        ], "page_context": {"has_more_page": False}}),
    ])
    client = ZohoClient(_cfg(), http=http)
    assert len(client.list_contacts()) == 2
