"""Shared pytest configuration for the expense-recon suite.

PR F made the web POST /runs background the pipeline by default and hand
back a polling page. The existing web tests assume the original synchronous
contract (POST -> 303 -> workbench, run ready immediately). Force the sync
seam on for the whole suite so those contracts hold; the PR-F tests that
exercise the async path delete this env var per-request.
"""
from __future__ import annotations

import os

os.environ.setdefault("EXPENSE_RECON_WEB_SYNC", "1")
