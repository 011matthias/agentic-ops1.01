"""Shared pytest configuration for the expense-recon suite.

The sync seam applies to POST /api/intakes/{id}/run only: with
EXPENSE_RECON_WEB_SYNC=1 it reconciles inline and answers {run_id}
directly instead of backgrounding a job. Keep it on suite-wide so the
intake-lifecycle tests stay synchronous; the async-path tests delete the
env var per-request. POST /api/runs is always async regardless (the SPA
polls /jobs/{id}), and TestClient finishes background tasks before the
response returns, so those tests never need the seam.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("EXPENSE_RECON_WEB_SYNC", "1")


@pytest.fixture(autouse=True)
def _no_ecb_network(monkeypatch):
    """Item 82: creating a month and attaching a statement ask the ECB for
    its monthly rates. The suite never reaches the network: every test sees
    a quiet ECB (no rates, so every config stays exactly as before), and a
    test that means to exercise the rates replaces `fetch_monthly` itself."""
    from expense_recon.web import ecb_rates

    monkeypatch.setattr(ecb_rates, "fetch_monthly", lambda start, end, **kw: {})
