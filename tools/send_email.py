#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Reusable plain-text email sender: Microsoft Graph primary, Resend fallback.

Shared by the scheduled exec-assistant flows (weekly-synthesis, eod-capture).
Primary backend (owner directive 2026-07-17: "use graph to send from my
outlook"): app-only Graph sendMail from the user's own Brisken mailbox to
himself -- internal telemetry only. The SENDER is HARD-PINNED in code to
matthias.silva@brisken.com (stricter than the {dirk, matthias} allowlist in
rule_brisken_graph_first): this tool must never write from anyone else's
mailbox, regardless of input. Credentials come from env vars or the
gitignored Brisken context .env in the PRIMARY clone (absolute path, so the
cadence worktree -- which has no gitignored files -- still resolves them).

Fallback: the original Resend path (with its Cloudflare User-Agent contract)
when RESEND_API_KEY is set and Graph is unavailable.

Usage:
  printf '%s' "$BODY" | python3 tools/send_email.py "Subject line" [recipient]
  # recipient falls back to $BRIEFING_TO, then to the sender's own mailbox.

Exit code 0 only on GRAPH_OK / RESEND_OK, so a scheduler step fails loud.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

SENDER = "matthias.silva@brisken.com"  # HARD PIN -- never parameterize
DEFAULT_TO = "matthias.silva@brisken.com"
ENV_FILE = (r"C:\Users\neuma_p1qrsic\Repo\agentic-ops1"
            r"\workspace\clients\brisken\context\.env")
GRAPH_KEYS = ("BRISKEN_TENANT_ID", "BRISKEN_GRAPH_CLIENT_ID",
              "BRISKEN_GRAPH_CLIENT_SECRET")


def parse_env_file(text: str) -> dict[str, str]:
    """KEY=VALUE lines; comments and blanks skipped; quotes stripped."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip("'\"")
    return out


def load_graph_creds() -> dict[str, str] | None:
    creds = {k: os.environ.get(k, "") for k in GRAPH_KEYS}
    if not all(creds.values()):
        try:
            file_vals = parse_env_file(open(ENV_FILE, encoding="utf-8").read())
        except OSError:
            file_vals = {}
        for k in GRAPH_KEYS:
            creds[k] = creds[k] or file_vals.get(k, "")
    return creds if all(creds.values()) else None


def _post(url: str, data: bytes, headers: dict) -> tuple[int, str]:
    req = urllib.request.Request(url, data=data, headers=headers)
    resp = urllib.request.urlopen(req, timeout=30)
    return resp.status, resp.read().decode(errors="replace")


def graph_send(creds: dict[str, str], subject: str, to: str, body: str) -> str:
    if SENDER != "matthias.silva@brisken.com":  # tamper tripwire
        raise RuntimeError(f"sender {SENDER!r} not allowlisted; refusing to send")
    token_status, token_body = _post(
        f"https://login.microsoftonline.com/{creds['BRISKEN_TENANT_ID']}"
        "/oauth2/v2.0/token",
        urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": creds["BRISKEN_GRAPH_CLIENT_ID"],
            "client_secret": creds["BRISKEN_GRAPH_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
        }).encode(),
        {"Content-Type": "application/x-www-form-urlencoded"})
    token = json.loads(token_body)["access_token"]
    status, _ = _post(
        f"https://graph.microsoft.com/v1.0/users/{SENDER}/sendMail",
        json.dumps({
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            },
            "saveToSentItems": "true",
        }).encode(),
        {"Authorization": f"Bearer {token}",
         "Content-Type": "application/json"})
    return f"GRAPH_OK {status} from={SENDER} to={to}"


def resend_send(key: str, subject: str, to: str, body: str) -> str:
    status, resp = _post(
        "https://api.resend.com/emails",
        json.dumps({"from": "onboarding@resend.dev", "to": to,
                    "subject": subject, "text": body}).encode(),
        {"Authorization": f"Bearer {key}",
         "Content-Type": "application/json",
         # Cloudflare in front of api.resend.com 403s (code 1010) the
         # default Python-urllib User-Agent. A real UA passes.
         "User-Agent": "agentic-ops-exec-assistant/1.0"})
    return "RESEND_OK " + resp


def main() -> int:
    subject = sys.argv[1] if len(sys.argv) > 1 else "(no subject)"
    to = (sys.argv[2] if len(sys.argv) > 2 else
          os.environ.get("BRIEFING_TO") or DEFAULT_TO)
    body = sys.stdin.read()

    creds = load_graph_creds()
    if creds:
        try:
            print(graph_send(creds, subject, to, body))
            return 0
        except Exception as e:  # noqa: BLE001 - want the reason in the log
            detail = getattr(e, "read", lambda: b"")()
            print(f"GRAPH_ERR {e} "
                  f"{detail.decode(errors='replace') if detail else ''}",
                  file=sys.stderr)

    key = os.environ.get("RESEND_API_KEY")
    if key:
        try:
            print(resend_send(key, subject, to, body))
            return 0
        except Exception as e:  # noqa: BLE001
            detail = getattr(e, "read", lambda: b"")()
            print(f"RESEND_ERR {e} "
                  f"{detail.decode(errors='replace') if detail else ''}",
                  file=sys.stderr)
    else:
        print("NO_SEND: no Graph credentials and no RESEND_API_KEY",
              file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
