"""Keep the Lead Desk DB current with each campaign's master sheet, via
Microsoft Graph (app-only, the BRISKEN MARKETING OPS INTEGRATION registration).

Source of truth is per-campaign: every campaign syncs from its OWN master sheet
(``CAMPAIGN_SOURCES`` below, overridable at runtime via ``set_source`` without a
redeploy). The sheet stays authoritative for identity / classification /
provenance / suppression; the app keeps its own pipeline work (see
``migrate.APP_OWNED_ON_RESYNC``). Idempotent and non-destructive; safe to run on
a schedule.

    lead-desk-sync --data ./lead-desk-data                 # all campaigns, one pass
    lead-desk-sync --data ./lead-desk-data --campaign rome-2026
    lead-desk-sync --data ./lead-desk-data --loop 86400    # daily

Credentials come from env (Fly secrets) or, in dev, the client .env:
``BRISKEN_TENANT_ID`` / ``BRISKEN_GRAPH_CLIENT_ID`` / ``BRISKEN_GRAPH_CLIENT_SECRET``.
The app must hold a Sites.Selected grant on each campaign's SharePoint site.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
from collections import Counter
from pathlib import Path

from .migrate import fold_send_logs, import_workbook
from .web.store import ContactStore

GRAPH = "https://graph.microsoft.com/v1.0"

# Per-campaign source of truth. Add a campaign by adding an entry here, or point
# a campaign at a different sheet at runtime with set_source() (stored in the DB
# `state` table). Resolution order in source_for(): DB override -> registry -> env.
CAMPAIGN_SOURCES: dict[str, dict] = {
    "rome-2026": {
        "site_id": ("brisken.sharepoint.com,65b8d36f-2777-4cff-bd80-58ff9022d17c,"
                    "e9089a15-9498-4149-a6f3-b4bc8e4d21ac"),
        "file_path": ("/30_Events/TA Cook/TA Cook 2026/"
                      "TAC Rome2026-post-event-master-contacts_260627_DN-Edits.xlsx"),
    },
}
_CREDS = ("BRISKEN_TENANT_ID", "BRISKEN_GRAPH_CLIENT_ID", "BRISKEN_GRAPH_CLIENT_SECRET")


def _load_creds() -> dict:
    """Env first (Fly secrets); fall back to the gitignored client .env in dev."""
    creds = {k: os.environ[k] for k in _CREDS if k in os.environ}
    if all(k in creds for k in _CREDS):
        return creds
    env_path = Path(__file__).resolve().parents[4] / "context" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() in _CREDS:
                    creds.setdefault(k.strip(), v.strip())
    missing = [k for k in _CREDS if k not in creds]
    if missing:
        raise RuntimeError(f"missing Graph credentials: {', '.join(missing)}")
    return creds


def have_creds() -> bool:
    try:
        _load_creds()
        return True
    except Exception:
        return False


def graph_token(creds: dict | None = None) -> str:
    import requests

    creds = creds or _load_creds()
    r = requests.post(
        f"https://login.microsoftonline.com/{creds['BRISKEN_TENANT_ID']}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": creds["BRISKEN_GRAPH_CLIENT_ID"],
            "client_secret": creds["BRISKEN_GRAPH_CLIENT_SECRET"],
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


# -- per-campaign source resolution -----------------------------------------

def source_for(campaign: str, store: ContactStore | None = None) -> dict:
    """DB state override > code registry > env fallback."""
    if store is not None:
        raw = store.get_state(f"source:{campaign}")
        if raw:
            return json.loads(raw)
    if campaign in CAMPAIGN_SOURCES:
        return dict(CAMPAIGN_SOURCES[campaign])
    sid = os.environ.get("LEAD_DESK_SHEET_SITE_ID")
    fp = os.environ.get("LEAD_DESK_SHEET_PATH")
    if sid and fp:
        return {"site_id": sid, "file_path": fp}
    raise KeyError(f"no source configured for campaign '{campaign}'")


def set_source(store: ContactStore, campaign: str, site_id: str,
               file_path: str, now: str) -> None:
    """Point a campaign at a different master sheet at runtime (no redeploy)."""
    store.set_state(f"source:{campaign}",
                    json.dumps({"site_id": site_id, "file_path": file_path}), now)


def configured_campaigns() -> list[str]:
    return sorted(CAMPAIGN_SOURCES)


def download_master(dest: Path, *, site_id: str, file_path: str,
                    token: str | None = None) -> dict:
    """Download a master xlsx to ``dest`` via app-only Graph. Returns drive-item
    metadata (name/size/lastModifiedDateTime)."""
    import requests

    token = token or graph_token()
    headers = {"Authorization": "Bearer " + token}
    meta = requests.get(
        f"{GRAPH}/sites/{site_id}/drive/root:{urllib.parse.quote(file_path)}",
        headers=headers, timeout=30,
    )
    meta.raise_for_status()
    m = meta.json()
    data = requests.get(m["@microsoft.graph.downloadUrl"], timeout=120)
    data.raise_for_status()
    dest.write_bytes(data.content)
    return {"name": m.get("name"), "size": m.get("size"),
            "last_modified": m.get("lastModifiedDateTime")}


def run_sync(data_dir: Path | str, *, campaign: str = "rome-2026",
             send_logs: bool = False, extras: Path | None = None) -> dict:
    """One non-destructive pass for a single campaign."""
    data_dir = Path(data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    db = data_dir / "lead-desk.sqlite"
    tmp = data_dir / f"_sync-{campaign}.xlsx"
    report: dict = {"campaign": campaign}
    with ContactStore(db) as store:
        src = source_for(campaign, store)
        report["source"] = download_master(tmp, site_id=src["site_id"],
                                            file_path=src["file_path"])
        email_index = import_workbook(store, tmp, campaign, report,
                                      preserve_app_fields=True)
        if send_logs and extras is not None:
            fold_send_logs(store, email_index, campaign, extras, report)
        rows = store.board_rows(campaign)
        report["total_contacts"] = len(rows)
        report["suppressed"] = sum(1 for r in rows if r["suppressed"])
        report["stages"] = dict(Counter(r["stage"] for r in rows))
    try:
        tmp.unlink()
    except OSError:
        pass
    return report


def run_all(data_dir: Path | str, campaigns: list[str] | None = None) -> list[dict]:
    """Sync every configured campaign (used by the daily scheduler)."""
    return [run_sync(data_dir, campaign=c)
            for c in (campaigns or configured_campaigns())]


def _print(report: dict) -> None:
    src = report.get("source", {})
    print(f"[{report.get('campaign')}] from {src.get('name')} "
          f"({src.get('size')} b, modified {src.get('last_modified')}) -> "
          f"contacts={report.get('contacts')} suppressed={report.get('suppressed')} "
          f"events={report.get('events_from_sheet')} stages={report.get('stages')}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-sync")
    p.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    p.add_argument("--campaign", default="", help="one campaign; blank = all configured")
    p.add_argument("--loop", type=int, default=0,
                   help="seconds between passes; 0 = one pass and exit (86400 = daily).")
    args = p.parse_args(argv)

    def once() -> int:
        try:
            reps = ([run_sync(Path(args.data), campaign=args.campaign)]
                    if args.campaign else run_all(Path(args.data)))
            for r in reps:
                _print(r)
            return 0
        except Exception as exc:  # noqa: BLE001 - a scheduled loop must survive a bad pass
            print(f"SYNC ERROR: {exc}")
            return 1

    if args.loop <= 0:
        return once()
    print(f"lead-desk-sync loop every {args.loop}s (Ctrl-C to stop)")
    while True:
        once()
        time.sleep(args.loop)


if __name__ == "__main__":
    raise SystemExit(main())
