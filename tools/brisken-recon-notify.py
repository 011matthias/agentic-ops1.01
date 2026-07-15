# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.31"]
# ///
"""Dev-side notifier for the Brisken expense-recon intake flow.

The hosted app (brisken-expense-recon.fly.dev) stays API-free per the One
Assessment precedent: it never holds Graph credentials and never sends
mail. THIS script, run on a dev machine (manually with --once after a
publish, or via a scheduled task every ~15 min), polls the app's
operator-state endpoint and sends the two notification mails via
Microsoft Graph:

* new intake (user uploaded documents)  -> mail the dev
* newly published run (result is ready) -> mail the user (Chris) + dev

State (which intakes/publishes were already announced) lives in a local
gitignored JSON file, so re-runs never double-send.

Env / config:
    EXPENSE_RECON_OPERATOR_CODE   operator access code (login to the app)
    BRISKEN_TENANT_ID             Graph app-only credentials
    BRISKEN_GRAPH_CLIENT_ID       (from workspace/clients/brisken/context/.env;
    BRISKEN_GRAPH_CLIENT_SECRET    pass --env-file to load it)
    EXPENSE_RECON_NOTIFY_USER     the user's email for ready-pings (optional;
                                  publish pings are skipped-with-log until set)

Usage:
    uv run tools/brisken-recon-notify.py --once [--dry-run]
    uv run tools/brisken-recon-notify.py --once --env-file workspace/clients/brisken/context/.env
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BASE_URL = os.environ.get(
    "EXPENSE_RECON_BASE_URL", "https://brisken-expense-recon.fly.dev"
)
# HARD allowlist (rule_brisken_graph_first): the credential can act as any
# tenant mailbox until the Exchange Application Access Policy exists, so
# the sender is pinned in code and recipients are restricted to the known
# set. Never widen this from config.
SENDER = "matthias.silva@brisken.com"
ALLOWED_SENDERS = frozenset({"matthias.silva@brisken.com", "dirk.neumann@brisken.com"})
DEV_RECIPIENTS = ("matthias.silva@brisken.com",)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = REPO_ROOT / ".scratch" / "recon-notify-state.json"
DEFAULT_ENV_FILE = REPO_ROOT / "workspace" / "clients" / "brisken" / "context" / ".env"


def diff_state(state: dict, remote: dict) -> tuple[list[dict], list[dict]]:
    """Pure diff: (new_intakes, new_publishes) not yet announced.

    `state` = {"seen_intakes": [...ids], "seen_published": [...run_ids]}.
    Announced = present in state. A re-published run (unpublish -> publish)
    is NOT re-announced; that is deliberate (testing-mode churn should not
    spam the user).
    """
    seen_intakes = set(state.get("seen_intakes", []))
    seen_published = set(state.get("seen_published", []))
    new_intakes = [
        i for i in remote.get("intakes", []) if i.get("intake_id") not in seen_intakes
    ]
    new_publishes = [
        r
        for r in remote.get("published_runs", [])
        if r.get("run_id") not in seen_published
    ]
    return new_intakes, new_publishes


def apply_to_state(state: dict, remote: dict) -> dict:
    """Mark everything currently visible as seen (after announcing)."""
    return {
        "seen_intakes": sorted(
            {i.get("intake_id") for i in remote.get("intakes", []) if i.get("intake_id")}
        ),
        "seen_published": sorted(
            {
                r.get("run_id")
                for r in remote.get("published_runs", [])
                if r.get("run_id")
            }
        ),
    }


def load_env_file(path: Path) -> None:
    """Minimal KEY=VALUE .env loader (no dependency); existing env wins."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def graph_token() -> str:
    import requests

    tenant = os.environ["BRISKEN_TENANT_ID"]
    resp = requests.post(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["BRISKEN_GRAPH_CLIENT_ID"],
            "client_secret": os.environ["BRISKEN_GRAPH_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def send_mail(token: str, subject: str, body: str, recipients: tuple[str, ...]) -> None:
    import requests

    if SENDER not in ALLOWED_SENDERS:
        raise RuntimeError(f"sender {SENDER!r} not allowlisted; refusing to send")
    allowed_rcpt = set(DEV_RECIPIENTS) | set(ALLOWED_SENDERS)
    user_email = os.environ.get("EXPENSE_RECON_NOTIFY_USER", "").strip()
    if user_email:
        allowed_rcpt.add(user_email)
    bad = [r for r in recipients if r not in allowed_rcpt]
    if bad:
        raise RuntimeError(f"recipients {bad} not allowlisted; refusing to send")
    resp = requests.post(
        f"https://graph.microsoft.com/v1.0/users/{SENDER}/sendMail",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [
                    {"emailAddress": {"address": r}} for r in recipients
                ],
            },
            "saveToSentItems": True,
        },
        timeout=30,
    )
    if resp.status_code != 202:
        raise RuntimeError(f"sendMail failed: {resp.status_code} {resp.text[:300]}")


def fetch_state_from_app() -> dict:
    import requests

    code = os.environ.get("EXPENSE_RECON_OPERATOR_CODE", "").strip()
    session = requests.Session()
    if code:
        login = session.post(
            f"{BASE_URL}/login", data={"code": code}, timeout=60,
            allow_redirects=False,
        )
        if login.status_code != 303:
            raise RuntimeError(f"operator login failed: {login.status_code}")
    resp = session.get(f"{BASE_URL}/api/operator/state", timeout=60)
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="single pass (the only mode)")
    parser.add_argument("--dry-run", action="store_true", help="print, send nothing")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    args = parser.parse_args()

    load_env_file(args.env_file)

    remote = fetch_state_from_app()
    state = {}
    if args.state.exists():
        state = json.loads(args.state.read_text(encoding="utf-8"))
    new_intakes, new_publishes = diff_state(state, remote)

    if not new_intakes and not new_publishes:
        print("nothing new")
        return 0

    user_email = os.environ.get("EXPENSE_RECON_NOTIFY_USER", "").strip()
    plans: list[tuple[str, str, tuple[str, ...]]] = []
    for i in new_intakes:
        subject = f"Expense recon: new upload - {i.get('label', '?')}"
        body = (
            f"New documents uploaded to the expense tool.\n\n"
            f"What: {i.get('label')}\n"
            f"When: {i.get('created_at')}\n"
            f"Files: {i.get('statement_name')}"
            + (f" + {i.get('receipts_name')}" if i.get("receipts_name") else " (no receipts yet)")
            + f"\nAuto-detect: {i.get('detect_note') or 'n/a'}\n\n"
            f"Queue: {BASE_URL}/\n"
        )
        plans.append((subject, body, DEV_RECIPIENTS))
    for r in new_publishes:
        subject = f"Your reconciliation is ready - {r.get('label', '?')}"
        body = (
            f"The reconciliation for {r.get('label')} is ready for your review.\n\n"
            f"Open it here: {BASE_URL}/runs/{r.get('run_id')}\n"
        )
        recipients = tuple([user_email] if user_email else []) + DEV_RECIPIENTS
        if not user_email:
            print(
                f"note: EXPENSE_RECON_NOTIFY_USER unset; ready-ping for "
                f"{r.get('run_id')} goes to the dev copy only"
            )
        plans.append((subject, body, recipients))

    if args.dry_run:
        for subject, body, recipients in plans:
            print(f"--- would send to {', '.join(recipients)}: {subject}\n{body}")
        return 0

    token = graph_token()
    for subject, body, recipients in plans:
        send_mail(token, subject, body, recipients)
        print(f"sent to {', '.join(recipients)}: {subject}")

    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(
        json.dumps(apply_to_state(state, remote), indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
