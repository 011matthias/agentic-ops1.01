"""Shared test fixtures.

Pin the campaign-engine wall clock. Several suites claim sends at a FIXED
datetime (IN_WINDOW / INSIDE = 2026-07-15 09:00 UTC) but approve/start stamp
``approved_at`` via the real ``cadence.now_utc()``. Once the real clock passed
2026-07-15, ``approved_at`` moved past the fixed claim time and a day-0 step
stopped being 'due' at claim time - a latent time-bomb that turned green
suites red with no code change. Pinning ``now_utc`` to the window time makes
the whole approve -> start -> claim flow deterministic regardless of the date.
"""
from __future__ import annotations

import datetime as _dt
import os

import pytest

from lead_desk.web import cadence

_FIXED_NOW = _dt.datetime(2026, 7, 15, 9, 0, tzinfo=_dt.timezone.utc)


@pytest.fixture(autouse=True)
def _pin_engine_clock(monkeypatch):
    monkeypatch.setattr(cadence, "now_utc", lambda: _FIXED_NOW)


@pytest.fixture(autouse=True)
def _no_dev_env_graph_creds(monkeypatch):
    """Graph creds come from env only under test. ``sync._load_creds`` falls
    back to the gitignored client ``context/.env``, which exists on a dev
    checkout: every ``TestClient(app)`` startup then armed the sheet-sync and
    truth-scan schedulers against LIVE Graph, and the suite hung at the first
    such test. CI has no .env, so it never showed there. Tests that exercise
    env-provided creds still work: they set the env vars themselves."""
    from lead_desk import sync

    def _env_only() -> dict:
        creds = {k: os.environ[k] for k in sync._CREDS if k in os.environ}
        missing = [k for k in sync._CREDS if k not in creds]
        if missing:
            raise RuntimeError(f"missing Graph credentials: {', '.join(missing)}")
        return creds

    monkeypatch.setattr(sync, "_load_creds", _env_only)


@pytest.fixture(autouse=True)
def _no_cloud_worker(monkeypatch):
    """The in-app cloud worker is opt-in (LEAD_DESK_CLOUD_WORKER=1 on Fly
    only). Hard-delete it here so a dev shell that exported it can never leak
    a live Graph loop into a TestClient app."""
    monkeypatch.delenv("LEAD_DESK_CLOUD_WORKER", raising=False)
