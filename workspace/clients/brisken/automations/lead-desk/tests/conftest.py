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

import pytest

from lead_desk.web import cadence

_FIXED_NOW = _dt.datetime(2026, 7, 15, 9, 0, tzinfo=_dt.timezone.utc)


@pytest.fixture(autouse=True)
def _pin_engine_clock(monkeypatch):
    monkeypatch.setattr(cadence, "now_utc", lambda: _FIXED_NOW)
