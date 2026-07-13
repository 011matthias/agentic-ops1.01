"""Worker configuration: env file + state paths + kill switch.

The home dir (``LEAD_DESK_WORKER_HOME`` or ``--home``) is a gitignored
directory (canonically ``workspace/clients/brisken/context/lead-desk-worker``
in the MAIN clone, not the pinned code worktree) holding:

    worker.env          LEAD_DESK_URL / LEAD_DESK_WORKER_SECRET /
                        LEAD_DESK_INGEST_SECRET / ALERT_TO / RESEND_API_KEY
    journal.jsonl       per-send write-ahead journal (crash reconcile)
    capture-state.json  inbox watermarks per mailbox
    runs/               per-day run audit logs
    KILL                presence = worker refuses to run (local kill switch)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

SEND_FROM = "matthias.silva@brisken.com"
DIRK_SMTP = "dirk.neumann@brisken.com"
WORKER_ID = "leaddesk-worker-win"
MAILBOXES = (SEND_FROM, DIRK_SMTP)


@dataclass
class WorkerConfig:
    home: Path
    base_url: str
    worker_secret: str
    ingest_secret: str
    alert_to: str | None = None
    resend_api_key: str | None = None
    worker_id: str = WORKER_ID
    extra: dict = field(default_factory=dict)

    @property
    def journal_path(self) -> Path:
        return self.home / "journal.jsonl"

    @property
    def capture_state_path(self) -> Path:
        return self.home / "capture-state.json"

    @property
    def runs_dir(self) -> Path:
        return self.home / "runs"

    @property
    def kill_file(self) -> Path:
        return self.home / "KILL"

    def kill_engaged(self) -> bool:
        return self.kill_file.exists() or \
            os.environ.get("LEAD_DESK_WORKER_DISABLED", "") == "1"


def _read_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def load_config(home: str | Path | None = None) -> WorkerConfig:
    home_path = Path(
        home or os.environ.get("LEAD_DESK_WORKER_HOME", "lead-desk-worker")
    ).expanduser().resolve()
    home_path.mkdir(parents=True, exist_ok=True)
    env = _read_env_file(home_path / "worker.env")

    def get(key: str, default: str = "") -> str:
        return os.environ.get(key, env.get(key, default)).strip()

    return WorkerConfig(
        home=home_path,
        base_url=get("LEAD_DESK_URL", "https://brisken-lead-desk.fly.dev").rstrip("/"),
        worker_secret=get("LEAD_DESK_WORKER_SECRET"),
        ingest_secret=get("LEAD_DESK_INGEST_SECRET"),
        alert_to=get("ALERT_TO") or None,
        resend_api_key=get("RESEND_API_KEY") or None,
        worker_id=get("LEAD_DESK_WORKER_ID", WORKER_ID),
        extra=env,
    )


def load_capture_state(cfg: WorkerConfig) -> dict:
    try:
        return json.loads(cfg.capture_state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_capture_state(cfg: WorkerConfig, state: dict) -> None:
    cfg.capture_state_path.write_text(json.dumps(state, indent=1), encoding="utf-8")
