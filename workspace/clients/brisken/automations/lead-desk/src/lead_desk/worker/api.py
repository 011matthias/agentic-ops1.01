"""HTTP client for the Lead Desk outbox/worker API + the /events sink.

Thin httpx wrapper. Transient network errors raise ``ApiUnavailable`` after
one retry - the tick aborts cleanly (nothing claimed = nothing stuck) and
the next scheduled run picks up. Result posts are idempotent server-side,
so replays are always safe.
"""
from __future__ import annotations

import time

import httpx

from .config import WorkerConfig


class ApiUnavailable(RuntimeError):
    pass


class ApiRejected(RuntimeError):
    """Non-2xx that is not transient (auth, validation)."""

    def __init__(self, status_code: int, body: str):
        super().__init__(f"HTTP {status_code}: {body[:300]}")
        self.status_code = status_code


class LeadDeskApi:
    def __init__(self, cfg: WorkerConfig, timeout: float = 30.0):
        self.cfg = cfg
        self._client = httpx.Client(base_url=cfg.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def _call(self, method: str, path: str, *, secret: str, json_body=None,
              params=None) -> dict:
        headers = {"Authorization": f"Bearer {secret}"}
        last_exc: Exception | None = None
        for attempt in (1, 2):
            try:
                resp = self._client.request(method, path, headers=headers,
                                            json=json_body, params=params)
            except httpx.HTTPError as exc:
                last_exc = exc
                time.sleep(3 * attempt)
                continue
            if resp.status_code >= 500:
                last_exc = ApiUnavailable(f"HTTP {resp.status_code}")
                time.sleep(3 * attempt)
                continue
            if resp.status_code >= 400:
                raise ApiRejected(resp.status_code, resp.text)
            return resp.json()
        raise ApiUnavailable(str(last_exc))

    # -- worker API (worker secret) ---------------------------------------

    def status(self) -> dict:
        return self._call("GET", "/api/worker/status", secret=self.cfg.worker_secret)

    def claim(self, max_items: int = 10, peek: bool = False) -> dict:
        return self._call("POST", "/api/outbox/claim", secret=self.cfg.worker_secret,
                          json_body={"worker_id": self.cfg.worker_id,
                                     "max_items": max_items, "peek": peek})

    def result(self, payload: dict) -> dict:
        return self._call("POST", "/api/outbox/result",
                          secret=self.cfg.worker_secret, json_body=payload)

    def draft_sent(self, payload: dict) -> dict:
        return self._call("POST", "/api/outbox/draft-sent",
                          secret=self.cfg.worker_secret, json_body=payload)

    def watchlist(self) -> dict:
        return self._call("GET", "/api/worker/watchlist",
                          secret=self.cfg.worker_secret)

    def heartbeat(self, counters: dict) -> dict:
        return self._call("POST", "/api/worker/heartbeat",
                          secret=self.cfg.worker_secret,
                          json_body={"worker_id": self.cfg.worker_id,
                                     "counters": counters})

    # -- event sink (ingest secret) ----------------------------------------

    def post_events(self, events: list[dict]) -> dict:
        if not events:
            return {"ok": True, "inserted": 0}
        return self._call("POST", "/events", secret=self.cfg.ingest_secret,
                          json_body=events)
