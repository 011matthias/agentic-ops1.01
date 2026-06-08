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
