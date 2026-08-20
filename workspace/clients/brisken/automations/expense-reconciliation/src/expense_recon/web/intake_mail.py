"""Mail-intake core: the app's own mailbox (expenses.brisken.com).

Faculty (or Criss forwarding on their behalf) mail receipts to the intake
address; the SMTP listener (`smtp_server.py`) hands the raw RFC822 bytes to
`process_message` here, which:

  1. parses the MIME (attachments incl. inline images; body-only detected),
  2. enforces the sender allowlist (deny-by-default; the SMTP layer turns a
     refusal into an in-protocol 550, so the sender's own mail system
     generates the bounce and we never send anything),
  3. archives the raw message + parts under ``/data/inbound/<stamp>/`` (the
     app is the system of record for the original),
  4. resolves WHO submitted it (To-alias beats From-sender; the alias map
     lives in settings["intake"]["aliases"]),
  5. routes the attachments into the newest OPEN expense batch via the
     existing incremental-add machinery (dedupe, quarantine, categorize all
     unchanged) stamping per-file intake provenance,
  6. appends one line per message to ``/data/inbound/log.jsonl``.

No open batch, body-only mail, or a tripped daily cap never drops mail:
the message is archived with a held status and surfaces via
``GET /api/inbound/log``; ``POST /api/inbound/replay-held`` re-routes held
mail once a batch exists.

Decision logic is pure/sync (testable without asyncio); only the SMTP
transport in `smtp_server.py` is async.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from pathlib import Path

from .service import (
    FOLDER_RECEIPT_SUFFIXES,
    MODE_EXPENSE_GENERATION,
    add_receipts_to_expense_batch,
    has_statement,
)
from .store import JOB_DONE, JOB_ERROR, RunStore

# ---------------------------------------------------------------- config --

DEFAULT_INTAKE_DOMAIN = "expenses.brisken.com"
DEFAULT_SENDER_ALLOWLIST = ("@brisken.com",)
# Cost guard on the vision spend a runaway/compromised sender could cause.
DEFAULT_SENDER_DAILY_CAP = 40
DEFAULT_GLOBAL_DAILY_CAP = 200
MAX_ATTACHMENTS_PER_MAIL = 30

# Held statuses (archived, not ingested, replayable where noted).
HELD_NO_BATCH = "held_no_batch"        # replayable
HELD_BODY_ONLY = "held_body_only"      # needs body->PDF rendering (round 2)
HELD_NO_VALID_FILES = "held_no_valid_files"
STATUS_INGESTED = "ingested"
STATUS_REPLAYED = "replayed"


@dataclass(frozen=True)
class IntakeConfig:
    domain: str = DEFAULT_INTAKE_DOMAIN
    sender_allowlist: tuple[str, ...] = DEFAULT_SENDER_ALLOWLIST
    aliases: dict = field(default_factory=dict)  # local-part -> person name
    sender_daily_cap: int = DEFAULT_SENDER_DAILY_CAP
    global_daily_cap: int = DEFAULT_GLOBAL_DAILY_CAP

    @classmethod
    def from_settings(cls, settings: dict | None) -> "IntakeConfig":
        """Settings key ``intake``: {domain, senders: [...], aliases: {...},
        sender_daily_cap, global_daily_cap}. Env overrides the domain
        (EXPENSE_RECON_INTAKE_DOMAIN) so fly.toml stays the deploy truth."""
        raw = (settings or {}).get("intake") or {}
        senders = tuple(
            s.strip().lower()
            for s in (raw.get("senders") or DEFAULT_SENDER_ALLOWLIST)
            if isinstance(s, str) and s.strip()
        ) or DEFAULT_SENDER_ALLOWLIST
        aliases = {
            str(k).strip().lower(): str(v).strip()
            for k, v in (raw.get("aliases") or {}).items()
            if str(k).strip() and str(v).strip()
        }
        domain = (
            os.environ.get("EXPENSE_RECON_INTAKE_DOMAIN")
            or str(raw.get("domain") or DEFAULT_INTAKE_DOMAIN)
        ).strip().lower()

        def _cap(key: str, default: int) -> int:
            try:
                v = int(raw.get(key, default))
                return v if v > 0 else default
            except (TypeError, ValueError):
                return default

        return cls(
            domain=domain,
            sender_allowlist=senders,
            aliases=aliases,
            sender_daily_cap=_cap("sender_daily_cap", DEFAULT_SENDER_DAILY_CAP),
            global_daily_cap=_cap("global_daily_cap", DEFAULT_GLOBAL_DAILY_CAP),
        )


def normalize_intake_setting(raw) -> dict:
    """Validate the settings["intake"] payload at the PUT edge. Returns the
    cleaned dict; raises ValueError on a malformed shape."""
    if not isinstance(raw, dict):
        raise ValueError("intake must be an object")
    cleaned: dict = {}
    domain = raw.get("domain")
    if domain is not None:
        if not isinstance(domain, str) or "@" in domain or not domain.strip():
            raise ValueError("intake.domain must be a bare domain name")
        cleaned["domain"] = domain.strip().lower()
    senders = raw.get("senders")
    if senders is not None:
        if not isinstance(senders, list) or not all(
            isinstance(s, str) and s.strip() for s in senders
        ):
            raise ValueError(
                "intake.senders must be a list of addresses or @domains"
            )
        cleaned["senders"] = [s.strip().lower() for s in senders]
    aliases = raw.get("aliases")
    if aliases is not None:
        if not isinstance(aliases, dict) or not all(
            isinstance(k, str) and k.strip()
            and isinstance(v, str) and v.strip()
            for k, v in aliases.items()
        ):
            raise ValueError(
                "intake.aliases must map address local-parts to person names"
            )
        cleaned["aliases"] = {
            k.strip().lower(): v.strip() for k, v in aliases.items()
        }
    for cap in ("sender_daily_cap", "global_daily_cap"):
        if cap in raw:
            try:
                v = int(raw[cap])
            except (TypeError, ValueError):
                raise ValueError(f"intake.{cap} must be a positive integer")
            if v <= 0:
                raise ValueError(f"intake.{cap} must be a positive integer")
            cleaned[cap] = v
    return cleaned


# ---------------------------------------------------------------- parsing --

@dataclass
class InboundMessage:
    from_addr: str
    to_locals: list[str]          # local parts addressed at the intake domain
    subject: str
    message_id: str
    attachments: list[tuple[str, bytes]]   # (filename, bytes), receipt types
    skipped: list[str]            # attachment names dropped (type/size/count)
    body_only: bool               # no usable attachments but there IS a body


def parse_inbound(raw: bytes, domain: str) -> InboundMessage:
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    from_addr = parseaddr(str(msg.get("From", "")))[1].strip().lower()
    to_locals: list[str] = []
    # NOTE: 3.12's strict getaddresses (CVE-2023-27043 fix) answers the
    # WHOLE call with the [('','')] failure sentinel if ANY element is
    # unparseable — an empty string from an absent header poisons it.
    header_values = [
        str(msg.get(h, ""))
        for h in ("To", "Cc", "X-Original-To", "Delivered-To")
    ]
    for _label, addr in getaddresses([v for v in header_values if v.strip()]):
        addr = addr.strip().lower()
        if addr.endswith("@" + domain):
            local = addr.split("@", 1)[0]
            # plus-addressing: receipts+dirk@ -> tag "dirk" is the signal
            if "+" in local:
                local = local.split("+", 1)[1]
            if local and local not in to_locals:
                to_locals.append(local)

    attachments: list[tuple[str, bytes]] = []
    skipped: list[str] = []
    n_parts = 0
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        fname = part.get_filename() or ""
        is_attachment = part.get_content_disposition() == "attachment"
        is_receipt_media = ctype in {
            "application/pdf", "image/png", "image/jpeg", "image/webp",
            "application/zip",
        }
        # Inline receipt images (cid-embedded) count too; plain text/html
        # bodies and signature furniture (tiny images) do not.
        if not is_attachment and not is_receipt_media:
            continue
        try:
            data = part.get_payload(decode=True) or b""
        except Exception:  # noqa: BLE001 - malformed part, skip loudly
            skipped.append(fname or ctype)
            continue
        if not fname:
            ext = {
                "application/pdf": ".pdf", "image/png": ".png",
                "image/jpeg": ".jpg", "image/webp": ".webp",
                "application/zip": ".zip",
            }.get(ctype, "")
            if not ext:
                continue
            fname = f"inline-{len(attachments) + 1}{ext}"
        suffix = Path(fname).suffix.lower()
        if suffix not in FOLDER_RECEIPT_SUFFIXES and suffix != ".zip":
            skipped.append(fname)
            continue
        if len(data) < 4096 and suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            # signature logos / tracking pixels, not receipts
            skipped.append(fname)
            continue
        n_parts += 1
        if n_parts > MAX_ATTACHMENTS_PER_MAIL:
            skipped.append(fname)
            continue
        if data:
            attachments.append((fname, data))

    body_only = not attachments and bool(
        msg.get_body(preferencelist=("html", "plain"))
    )
    return InboundMessage(
        from_addr=from_addr,
        to_locals=to_locals,
        subject=str(msg.get("Subject", ""))[:300],
        message_id=str(msg.get("Message-ID", ""))[:200],
        attachments=attachments,
        skipped=skipped,
        body_only=body_only,
    )


def sender_allowed(from_addr: str, allowlist: tuple[str, ...]) -> bool:
    """Deny-by-default. Entries are exact addresses or '@domain' suffixes.
    This is a spam filter, not authentication: From is forgeable, and every
    ingested receipt still passes through quarantine + operator review."""
    addr = (from_addr or "").strip().lower()
    if not addr or "@" not in addr:
        return False
    for entry in allowlist:
        if entry.startswith("@"):
            if addr.endswith(entry):
                return True
        elif addr == entry:
            return True
    return False


def resolve_person(
    to_locals: list[str], from_addr: str, cfg: IntakeConfig
) -> dict:
    """To-alias beats From-sender: the alias survives Criss forwarding on
    someone's behalf, where From degrades to the forwarder."""
    for local in to_locals:
        person = cfg.aliases.get(local)
        if person:
            return {"person": person, "source": "alias", "address": from_addr}
    return {"person": from_addr, "source": "sender", "address": from_addr}


# ---------------------------------------------------------------- archive --

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def inbound_root(data_root: Path) -> Path:
    return Path(data_root) / "inbound"


def _log_path(data_root: Path) -> Path:
    return inbound_root(data_root) / "log.jsonl"


def _append_log(data_root: Path, entry: dict) -> None:
    root = inbound_root(data_root)
    root.mkdir(parents=True, exist_ok=True)
    with _log_path(data_root).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_log(data_root: Path, limit: int = 100) -> list[dict]:
    path = _log_path(data_root)
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows[-limit:]


def today_counts(data_root: Path) -> tuple[dict[str, int], int]:
    """(per-sender file counts today, global file count today) from the
    log — cheap at this volume, no schema."""
    today = _now_iso()[:10]
    per: dict[str, int] = {}
    total = 0
    for row in read_log(data_root, limit=2000):
        if str(row.get("at", ""))[:10] != today:
            continue
        n = int(row.get("n_files") or 0)
        sender = str(row.get("from", ""))
        per[sender] = per.get(sender, 0) + n
        total += n
    return per, total


def archive_message(
    data_root: Path, raw: bytes, parsed: InboundMessage, status: str,
    extra: dict | None = None,
) -> Path:
    digest = hashlib.sha1(raw).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    arch = inbound_root(data_root) / f"{stamp}-{digest}"
    arch.mkdir(parents=True, exist_ok=True)
    (arch / "message.eml").write_bytes(raw)
    parts = arch / "parts"
    if parsed.attachments:
        parts.mkdir(exist_ok=True)
        for i, (name, data) in enumerate(parsed.attachments):
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name) or f"part{i}"
            (parts / f"{i:03d}__{safe}").write_bytes(data)
    meta = {
        "at": _now_iso(),
        "from": parsed.from_addr,
        "to_locals": parsed.to_locals,
        "subject": parsed.subject,
        "message_id": parsed.message_id,
        "status": status,
        "n_files": len(parsed.attachments),
        "skipped": parsed.skipped,
        **(extra or {}),
    }
    (arch / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return arch


def _update_meta(arch: Path, patch: dict) -> None:
    meta_path = arch / "meta.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - a corrupt meta must not block replay
        meta = {}
    meta.update(patch)
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )


# ---------------------------------------------------------------- routing --

def open_batch(store: RunStore):
    """Newest expense batch without a statement attached, else None."""
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if not has_statement(run):
            return run
    return None


def _ingest_job(
    db_path: Path, job_id: str, run_id: str, staging: Path,
    learning_db_path: Path | None, provenance: dict[str, dict],
) -> None:
    import shutil

    try:
        with RunStore(db_path) as store:
            run = store.get_run(run_id)
            if run is None:
                store.set_job_status(
                    job_id, JOB_ERROR, error="run not found",
                    updated_at=_now_iso(),
                )
                return
            add_receipts_to_expense_batch(
                store, run, staging, _now_iso(),
                learning_db_path=learning_db_path,
                on_stage=lambda s: store.set_job_stage(job_id, s, _now_iso()),
                provenance_by_digest=provenance,
            )
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id, updated_at=_now_iso()
            )
    except Exception as exc:  # noqa: BLE001 - job errors surface via poller
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc), updated_at=_now_iso()
            )
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _start_ingest(
    db_path: Path,
    learning_db_path: Path | None,
    run,
    attachments: list[tuple[str, bytes]],
    person: dict,
    received_at: str,
    *,
    synchronous: bool = False,
) -> str:
    """Stage the mail's files into the batch and run the incremental add
    (thread by default; synchronous for replay + tests). Returns job_id."""
    job_id = uuid.uuid4().hex[:12]
    staging = Path(run.work_dir) / f"add-staging-mail-{job_id}"
    staging.mkdir(parents=True, exist_ok=True)
    provenance: dict[str, dict] = {}
    for i, (name, data) in enumerate(attachments):
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name) or "file"
        (staging / f"{i:04d}__{safe}").write_bytes(data)
        digest = hashlib.sha1(data).hexdigest()[:16]
        provenance[digest] = {**person, "received_at": received_at}
    with RunStore(db_path) as store:
        store.create_job(job_id, None, _now_iso())
    if synchronous:
        _ingest_job(db_path, job_id, run.run_id, staging,
                    learning_db_path, provenance)
    else:
        threading.Thread(
            target=_ingest_job,
            args=(db_path, job_id, run.run_id, staging,
                  learning_db_path, provenance),
            daemon=True,
        ).start()
    return job_id


def process_message(
    db_path: Path,
    learning_db_path: Path | None,
    data_root: Path,
    raw: bytes,
    *,
    peer: str = "",
    synchronous: bool = False,
) -> dict:
    """The accepted-mail pipeline (allowlist already passed at the SMTP
    layer). Archive first — nothing that reached here is ever lost — then
    route. Returns {status, ...} for the SMTP reply + log."""
    with RunStore(db_path) as store:
        cfg = IntakeConfig.from_settings(store.get_settings())
    parsed = parse_inbound(raw, cfg.domain)
    person = resolve_person(parsed.to_locals, parsed.from_addr, cfg)
    received_at = _now_iso()

    if parsed.body_only:
        status, extra = HELD_BODY_ONLY, {}
    elif not parsed.attachments:
        status, extra = HELD_NO_VALID_FILES, {}
    else:
        with RunStore(db_path) as store:
            run = open_batch(store)
        if run is None:
            status, extra = HELD_NO_BATCH, {}
        else:
            status, extra = STATUS_INGESTED, {"batch_id": run.run_id}

    arch = archive_message(
        data_root, raw, parsed, status,
        extra={**extra, "person": person, "peer": peer},
    )
    if status == STATUS_INGESTED:
        job_id = _start_ingest(
            db_path, learning_db_path, run, parsed.attachments, person,
            received_at, synchronous=synchronous,
        )
        _update_meta(arch, {"job_id": job_id})
        extra = {**extra, "job_id": job_id}

    _append_log(data_root, {
        "at": received_at,
        "from": parsed.from_addr,
        "person": person.get("person"),
        "subject": parsed.subject,
        "n_files": len(parsed.attachments),
        "status": status,
        "archive": arch.name,
        **extra,
    })
    return {"status": status, "archive": arch.name, "person": person, **extra}


def replay_held(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
) -> dict:
    """Re-route mail archived as held_no_batch into the (now) open batch.
    Body-only holds stay held (they need the round-2 body renderer)."""
    root = inbound_root(data_root)
    if not root.exists():
        return {"replayed": 0, "still_held": 0}
    with RunStore(db_path) as store:
        run = open_batch(store)
    replayed = still_held = 0
    for arch in sorted(root.iterdir()):
        meta_path = arch / "meta.json"
        if not meta_path.is_file():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - unreadable meta is not replayable
            continue
        if meta.get("status") != HELD_NO_BATCH:
            continue
        if run is None:
            still_held += 1
            continue
        parts_dir = arch / "parts"
        attachments = [
            (re.sub(r"^\d{3}__", "", p.name), p.read_bytes())
            for p in sorted(parts_dir.iterdir())
            if p.is_file()
        ] if parts_dir.is_dir() else []
        if not attachments:
            still_held += 1
            continue
        person = meta.get("person") or {
            "person": meta.get("from", ""), "source": "sender",
            "address": meta.get("from", ""),
        }
        job_id = _start_ingest(
            db_path, learning_db_path, run, attachments, person,
            _now_iso(), synchronous=True,
        )
        _update_meta(arch, {
            "status": STATUS_REPLAYED, "job_id": job_id,
            "batch_id": run.run_id,
        })
        _append_log(data_root, {
            "at": _now_iso(), "from": meta.get("from", ""),
            "person": person.get("person"), "subject": meta.get("subject", ""),
            "n_files": len(attachments), "status": STATUS_REPLAYED,
            "archive": arch.name, "batch_id": run.run_id, "job_id": job_id,
        })
        replayed += 1
    return {"replayed": replayed, "still_held": still_held}
