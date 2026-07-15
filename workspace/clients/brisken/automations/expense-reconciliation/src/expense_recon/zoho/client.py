"""Zoho Books API client — BLUEPRINT slice 4.7 (read path).

Server-to-server OAuth using a stored refresh token (the Self Client
flow). Credentials come from the environment, never a committed file:

    ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN, ZOHO_ORG_ID

plus optional ZOHO_API_DOMAIN / ZOHO_ACCOUNTS_DOMAIN for non-US data
centers (US defaults: https://www.zohoapis.com / https://accounts.zoho.com;
EU would be zohoapis.eu / accounts.zoho.eu).

The client refreshes a short-lived access token on demand and caches
it until just before expiry. All network I/O goes through an
injectable `http` callable so tests run without touching Zoho.

Scope of this slice: READ endpoints (organizations, chart of
accounts). The journal-posting path (`create_journal`, slice 4b) is
deliberately not here yet — posting real journal entries is
irreversible and gated on the account-scope decision with Chris.
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib import request as _urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

# An HTTP transport: (method, url, headers, body_bytes) -> (status, payload_dict).
# The default uses urllib; tests inject a fake to avoid network I/O.
Transport = Callable[[str, str, Mapping[str, str], bytes | None], "tuple[int, dict]"]

# Refresh this many seconds before the access token actually expires,
# so an in-flight request never races the expiry boundary.
_EXPIRY_SAFETY_SECONDS = 60


class ZohoAuthError(RuntimeError):
    """Raised when the OAuth token refresh fails (bad/expired refresh
    token, wrong data center, revoked client)."""


class ZohoAPIError(RuntimeError):
    """Raised when a Books API call returns a non-success status or a
    non-zero Zoho `code`. Carries the HTTP status and Zoho code for
    callers that want to branch on them."""

    def __init__(self, message: str, *, status: int | None = None, code: int | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass(frozen=True)
class ZohoConfig:
    client_id: str
    client_secret: str
    refresh_token: str
    org_id: str
    api_domain: str = "https://www.zohoapis.com"
    accounts_domain: str = "https://accounts.zoho.com"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "ZohoConfig":
        """Build config from environment variables. Raises ValueError
        naming every missing required var at once (not one at a time)."""
        env = os.environ if env is None else env
        required = {
            "client_id": "ZOHO_CLIENT_ID",
            "client_secret": "ZOHO_CLIENT_SECRET",
            "refresh_token": "ZOHO_REFRESH_TOKEN",
            "org_id": "ZOHO_ORG_ID",
        }
        values = {field: env.get(var) for field, var in required.items()}
        missing = [var for field, var in required.items() if not values[field]]
        if missing:
            raise ValueError(
                f"Zoho credentials missing from environment: {', '.join(missing)}"
            )
        return cls(
            client_id=values["client_id"],
            client_secret=values["client_secret"],
            refresh_token=values["refresh_token"],
            org_id=values["org_id"],
            api_domain=env.get("ZOHO_API_DOMAIN", "https://www.zohoapis.com"),
            accounts_domain=env.get("ZOHO_ACCOUNTS_DOMAIN", "https://accounts.zoho.com"),
        )


class ZohoClient:
    """Thin Books API client. Handles token refresh + pagination; the
    endpoint surface is intentionally small (the tool needs reads now,
    posting later)."""

    def __init__(
        self,
        config: ZohoConfig,
        *,
        http: Transport | None = None,
        clock: Callable[[], float] | None = None,
    ):
        self._cfg = config
        self._http = http or _urllib_transport
        self._clock = clock or time.monotonic
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    # ── auth ─────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        body = urlencode(
            {
                "grant_type": "refresh_token",
                "client_id": self._cfg.client_id,
                "client_secret": self._cfg.client_secret,
                "refresh_token": self._cfg.refresh_token,
            }
        ).encode("utf-8")
        status, payload = self._http(
            "POST",
            f"{self._cfg.accounts_domain}/oauth/v2/token",
            {"Content-Type": "application/x-www-form-urlencoded"},
            body,
        )
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if status != 200 or not token:
            err = payload.get("error") if isinstance(payload, dict) else payload
            raise ZohoAuthError(f"token refresh failed (status {status}): {err}")
        self._access_token = token
        expires_in = float(payload.get("expires_in", 3600))
        self._expires_at = self._clock() + expires_in - _EXPIRY_SAFETY_SECONDS

    def _token(self) -> str:
        if self._access_token is None or self._clock() >= self._expires_at:
            self._refresh()
        assert self._access_token is not None  # set by _refresh
        return self._access_token

    # ── requests ─────────────────────────────────────────────────────

    def _get(self, path: str, params: Mapping[str, str] | None = None) -> dict:
        query = {**(params or {}), "organization_id": self._cfg.org_id}
        url = f"{self._cfg.api_domain}{path}?{urlencode(query)}"
        status, payload = self._http(
            "GET", url, {"Authorization": f"Zoho-oauthtoken {self._token()}"}, None
        )
        if not isinstance(payload, dict):
            raise ZohoAPIError(f"GET {path}: non-JSON response", status=status)
        # Zoho wraps every response in a `code` (0 == success) + `message`.
        code = payload.get("code", 0)
        if status != 200 or code not in (0, None):
            raise ZohoAPIError(
                f"GET {path} failed: {payload.get('message', 'unknown error')}",
                status=status,
                code=code,
            )
        return payload

    # ── endpoints ────────────────────────────────────────────────────

    def list_organizations(self) -> list[dict]:
        return self._get("/books/v3/organizations").get("organizations", [])

    def list_chart_of_accounts(self) -> list[dict]:
        """Return every account in the org's chart of accounts,
        following `page_context.has_more_page` pagination."""
        accounts: list[dict] = []
        page = 1
        while True:
            payload = self._get(
                "/books/v3/chartofaccounts", {"page": str(page), "per_page": "200"}
            )
            accounts.extend(payload.get("chartofaccounts", []))
            ctx = payload.get("page_context") or {}
            if not ctx.get("has_more_page"):
                break
            page += 1
        return accounts

    def list_expenses(
        self, *, date_start: str | None = None, date_end: str | None = None
    ) -> list[dict]:
        """All expense records (paginated per_page=200), date-filtered
        CLIENT-SIDE on each record's `date` field (YYYY-MM-DD string
        comparison; Zoho's own list filters are inconsistent across DCs).
        `date_start` / `date_end` are inclusive bounds; None means open."""
        expenses: list[dict] = []
        page = 1
        while True:
            payload = self._get(
                "/books/v3/expenses", {"page": str(page), "per_page": "200"}
            )
            expenses.extend(payload.get("expenses", []))
            ctx = payload.get("page_context") or {}
            if not ctx.get("has_more_page"):
                break
            page += 1
        if date_start is None and date_end is None:
            return expenses

        def _in_window(rec: dict) -> bool:
            d = rec.get("date") or ""
            if not d:
                return False  # an undated record cannot be affirmed in-window
            if date_start is not None and d < date_start:
                return False
            if date_end is not None and d > date_end:
                return False
            return True

        return [e for e in expenses if _in_window(e)]


def _urllib_transport(
    method: str, url: str, headers: Mapping[str, str], body: bytes | None
) -> tuple[int, dict]:
    """Default transport over urllib. Returns (status, parsed JSON).

    HTTPError bodies are still parsed — Zoho returns a JSON error body
    with a non-2xx status, and the caller needs that message.
    """
    req = _urlrequest.Request(url, data=body, headers=dict(headers), method=method)
    try:
        with _urlrequest.urlopen(req, timeout=30) as resp:
            return resp.status, _parse_json(resp.read())
    except HTTPError as exc:
        return exc.code, _parse_json(exc.read())
    except URLError as exc:
        raise ZohoAPIError(f"network error calling {url}: {exc.reason}") from exc


def _parse_json(raw: bytes) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {"data": parsed}
