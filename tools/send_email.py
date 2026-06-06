#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Reusable plain-text email sender (Resend HTTP API, stdlib only).

Shared by the scheduled exec-assistant agents (eod-capture, weekly-review).
Kept separate from tools/morning_briefing.py on purpose: that file is
deliberately self-contained so it runs in a bare GitHub Actions sandbox.
This one carries the same Resend + User-Agent contract for the agent-driven
flows that generate their body at runtime.

Usage:
  printf '%s' "$BODY" | RESEND_API_KEY=re_... python3 tools/send_email.py "Subject line" recipient@example.com
  # recipient falls back to $BRIEFING_TO when argv[2] is omitted.

Exit code 0 only on RESEND_OK, so a scheduler step fails loud on a bad send.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request


def main() -> int:
    subject = sys.argv[1] if len(sys.argv) > 1 else "(no subject)"
    to = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("BRIEFING_TO")
    key = os.environ.get("RESEND_API_KEY")
    body = sys.stdin.read()
    if not key or not to:
        print("NO_SEND: missing RESEND_API_KEY or recipient", file=sys.stderr)
        return 1
    payload = json.dumps({
        "from": "onboarding@resend.dev", "to": to,
        "subject": subject, "text": body,
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 # Cloudflare in front of api.resend.com 403s (code 1010) the
                 # default Python-urllib User-Agent. A real UA passes.
                 "User-Agent": "agentic-ops-exec-assistant/1.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=30).read().decode()
        print("RESEND_OK " + resp)
        return 0
    except Exception as e:  # noqa: BLE001 - want the reason in the log
        detail = getattr(e, "read", lambda: b"")()
        print(f"RESEND_ERR {e} {detail.decode(errors='replace') if detail else ''}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
