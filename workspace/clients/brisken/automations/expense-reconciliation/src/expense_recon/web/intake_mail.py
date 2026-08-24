"""Mail-intake core: the app's own mailbox (expenses.brisken.com).

Faculty (or Criss forwarding on their behalf) mail receipts to the intake
address; the SMTP listener (`smtp_server.py`) drives this module:

  1. `parse_inbound` reads the MIME (attachments incl. inline images;
     body-only detected; zips REFUSED at this boundary — the authenticated
     operator upload is the zip path; a mailed zip would count as one file
     against the spend budget while expanding to up to 80 vision calls),
  2. anyone may submit (owner directive 2026-08-23: the sender allowlist is
     gone — a faculty member mailing from a private address, a hotel
     mailing an invoice on their behalf, and a supplier's billing robot all
     have to land). What holds the door is downstream, not at the sender:
     the recipient must be an address at our own domain (no relaying), the
     day budget caps the vision spend, zips are refused, and every ingested
     file still passes quarantine + operator review before it is money,
  3. `archive_incoming` writes the raw message + parts under
     ``/data/inbound/<stamp>/`` and the acceptance log row BEFORE the SMTP
     250 is answered (the ack means custody: a crash after 250 can no
     longer lose acknowledged mail),
  4. `route_archived` resolves WHO submitted it (To-alias beats
     From-sender), reads the receipts' PRINTED dates at arrival (full
     `parse_receipt_file` extraction, so the content-addressed cache is
     already warm when the batch ingests the same bytes), and routes BY
     MONTH (owner directive 2026-08-24): the mail ingests into the open
     batch whose label names its month, else it rests in the pool
     (status ``pooled``) until that month is opened — it never lands in
     "whatever month happens to be open". `claim_pooled` is the pull
     half: it drains matching pooled mail when a month batch is created
     or renamed, at startup, and on the replay endpoint. The archive's
     status flips to ``ingested`` only when the job actually succeeded,
     else ``held_failed`` so replay can drain it,
  5. spend/abuse guards: an in-memory day budget reserved at acceptance
     time (raceproof within the process), an in-flight route ceiling, and
     a free-disk floor — each refusal is a 4xx/5xx SMTP answer, never a
     silent drop.

Held mail (body-only, no valid files, failed/interrupted jobs) and
pooled mail are archived + visible via ``GET /api/inbound/log``;
``POST /api/inbound/replay-held`` re-routes held mail and claims
pooled mail whose month is open now.

Decision logic is pure/sync (testable without asyncio); only the SMTP
transport in `smtp_server.py` is async.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import logging
import os
import re
import shutil
import threading
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from pathlib import Path

from ..batch_period import month_from_label
from . import graph_notify
from .service import (
    FOLDER_RECEIPT_SUFFIXES,
    MODE_EXPENSE_GENERATION,
    add_receipts_to_expense_batch,
    has_statement,
)
from .store import JOB_DONE, JOB_ERROR, RunStore

log = logging.getLogger("expense_recon.intake")

# ---------------------------------------------------------------- config --

DEFAULT_INTAKE_DOMAIN = "expenses.brisken.com"
# Cost guard on the vision spend a runaway/compromised sender could cause.
# Units = max(1, attachment count) per accepted message, so zero-file spam
# consumes budget too. Since the allowlist was dropped (2026-08-23) the
# per-sender cap is only a courtesy — From is forgeable, so a determined
# abuser rotates it — and the GLOBAL cap is the real ceiling on a day's
# spend. Keep that in mind before raising it.
DEFAULT_SENDER_DAILY_CAP = 40
DEFAULT_GLOBAL_DAILY_CAP = 200
DEFAULT_ALERT_RECIPIENTS = ("matthias.silva@brisken.com",)
# German AO paragraph 147 keeps accounting records (Belege) 10 years; the
# archive IS the system of record for mailed receipts, so that is the
# default floor. Owner-adjustable via settings intake.retention_years.
DEFAULT_RETENTION_YEARS = 10
MAX_ATTACHMENTS_PER_MAIL = 30
MAX_INFLIGHT_ROUTES = 8
MIN_FREE_DISK_BYTES = 500 * 1024 * 1024

# Archive statuses. "received" = custody taken, routing pending;
# a stale "received" (crashed router) is replayable like held_no_batch.
STATUS_RECEIVED = "received"
STATUS_INGESTED = "ingested"
STATUS_REPLAYED = "replayed"
HELD_NO_BATCH = "held_no_batch"        # legacy (pre-pool); replayable
HELD_FAILED = "held_failed"            # job errored/interrupted; replayable
HELD_BODY_ONLY = "held_body_only"      # needs body->PDF rendering (round 2)
HELD_NO_VALID_FILES = "held_no_valid_files"
STATUS_DISMISSED = "dismissed"         # operator judged it junk; terminal
STATUS_RENDERING = "rendering"         # body->PDF ingest in flight (C2)
STATUS_REINGESTING = "re_ingesting"    # stranded-mail re-ingest in flight
# The month pool (owner directive 2026-08-24). "pooled" is a RESTING state,
# deliberately not held_*: nothing is wrong with the mail, its month just
# is not open yet. "routing"/"claiming" are transient CAS states that make
# arrival routing and pool claiming single-winner.
STATUS_POOLED = "pooled"
STATUS_ROUTING = "routing"
STATUS_CLAIMING = "claiming"
REPLAYABLE = {HELD_NO_BATCH, HELD_FAILED}
STALE_RECEIVED_SECONDS = 600

# Plausibility clamp on a receipt's printed date (owner ruling 2026-08-24):
# older than ~12 months before arrival, or in the future, counts as
# unreadable and the mail files under its ARRIVAL month instead. One day of
# future grace absorbs timezone skew on a same-day receipt.
_IMPLAUSIBLE_PAST_DAYS = 366
_FUTURE_GRACE_DAYS = 1


@dataclass(frozen=True)
class IntakeConfig:
    domain: str = DEFAULT_INTAKE_DOMAIN
    aliases: dict = field(default_factory=dict)  # local-part -> person name
    sender_daily_cap: int = DEFAULT_SENDER_DAILY_CAP
    global_daily_cap: int = DEFAULT_GLOBAL_DAILY_CAP
    auto_ack: bool = True
    alert_recipients: tuple[str, ...] = DEFAULT_ALERT_RECIPIENTS
    retention_years: int = DEFAULT_RETENTION_YEARS

    @classmethod
    def from_settings(cls, settings: dict | None) -> "IntakeConfig":
        """Settings key ``intake``: {domain, aliases: {...},
        sender_daily_cap, global_daily_cap, auto_ack, alert_recipients,
        retention_years}. Env overrides the domain
        (EXPENSE_RECON_INTAKE_DOMAIN) so fly.toml stays the deploy truth.
        A legacy ``senders`` key is ignored: submission is open."""
        raw = (settings or {}).get("intake") or {}
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

        # Alert recipients keep only internal-looking addresses; the Graph
        # layer re-asserts @brisken.com per send regardless.
        alerts = tuple(
            a.strip().lower()
            for a in (raw.get("alert_recipients") or DEFAULT_ALERT_RECIPIENTS)
            if isinstance(a, str) and "@" in a.strip()
        ) or DEFAULT_ALERT_RECIPIENTS

        return cls(
            domain=domain,
            aliases=aliases,
            sender_daily_cap=_cap("sender_daily_cap", DEFAULT_SENDER_DAILY_CAP),
            global_daily_cap=_cap("global_daily_cap", DEFAULT_GLOBAL_DAILY_CAP),
            auto_ack=bool(raw.get("auto_ack", True)),
            alert_recipients=alerts,
            retention_years=_cap("retention_years", DEFAULT_RETENTION_YEARS),
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
    # ``senders`` (the retired allowlist) is dropped rather than rejected: a
    # stored settings blob or an older client may still carry it, and a 400
    # on a key that no longer does anything would block edits to the keys
    # that do.
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
    for cap in ("sender_daily_cap", "global_daily_cap", "retention_years"):
        if cap in raw:
            try:
                v = int(raw[cap])
            except (TypeError, ValueError):
                raise ValueError(f"intake.{cap} must be a positive integer")
            if v <= 0:
                raise ValueError(f"intake.{cap} must be a positive integer")
            cleaned[cap] = v
    if "auto_ack" in raw:
        if not isinstance(raw["auto_ack"], bool):
            raise ValueError("intake.auto_ack must be true or false")
        cleaned["auto_ack"] = raw["auto_ack"]
    alerts = raw.get("alert_recipients")
    if alerts is not None:
        if not isinstance(alerts, list) or not all(
            isinstance(a, str) and a.strip().lower().endswith("@brisken.com")
            and a.strip().count("@") == 1
            for a in alerts
        ):
            raise ValueError(
                "intake.alert_recipients must be @brisken.com addresses"
            )
        cleaned["alert_recipients"] = [a.strip().lower() for a in alerts]
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


def _locals_from_addrs(addrs, domain: str, out: list[str]) -> None:
    for addr in addrs:
        addr = (addr or "").strip().lower()
        if addr.endswith("@" + domain):
            local = addr.split("@", 1)[0]
            # plus-addressing: receipts+dirk@ -> tag "dirk" is the signal
            if "+" in local:
                local = local.split("+", 1)[1]
            if local and local not in out:
                out.append(local)


def parse_inbound(
    raw: bytes, domain: str, envelope_rcpts: list[str] | None = None
) -> InboundMessage:
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    from_addr = parseaddr(str(msg.get("From", "")))[1].strip().lower()
    to_locals: list[str] = []
    # Envelope recipients first: our own listener IS the receiving MTA, so
    # they are authoritative and cover Bcc'd aliases the headers never show.
    _locals_from_addrs(envelope_rcpts or [], domain, to_locals)
    # NOTE: 3.12's strict getaddresses (CVE-2023-27043 fix) answers the
    # WHOLE call with the [('','')] failure sentinel if ANY element is
    # unparseable — an empty string from an absent header poisons it.
    header_values = [str(msg.get(h, "")) for h in ("To", "Cc")]
    _locals_from_addrs(
        (a for _l, a in getaddresses([v for v in header_values if v.strip()])),
        domain, to_locals,
    )

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
        }
        # Inline receipt images (cid-embedded) count too; plain text/html
        # bodies and signature furniture (tiny images) do not. Zips are
        # refused here by design (see module docstring).
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
            }.get(ctype, "")
            if not ext:
                continue
            fname = f"inline-{len(attachments) + 1}{ext}"
        suffix = Path(fname).suffix.lower()
        if suffix not in FOLDER_RECEIPT_SUFFIXES or suffix == ".zip":
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


def resolve_person(
    to_locals: list[str], from_addr: str, cfg: IntakeConfig
) -> dict:
    """To-alias beats From-sender: the alias survives Criss forwarding on
    someone's behalf, where From degrades to the forwarder. The alias is a
    routing CLAIM, not authentication — `address` always records the real
    sender, and the reviewer sees both."""
    for local in to_locals:
        person = cfg.aliases.get(local)
        if person:
            return {"person": person, "source": "alias", "address": from_addr}
    return {"person": from_addr, "source": "sender", "address": from_addr}


# ------------------------------------------------------- abuse guards ----

class DayBudget:
    """In-memory per-day spend budget, reserved at acceptance time BEFORE
    the SMTP 250, so concurrent connections cannot race past the caps the
    way a read-the-log-later design would. Seeded from the acceptance log
    once per process (restart forgiveness is bounded by the log)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = ""
        self._per_sender: dict[str, int] = {}
        self._global = 0
        self._seeded_from: Path | None = None

    def _roll(self, data_root: Path) -> None:
        today = _now_iso()[:10]
        if self._day != today:
            self._day = today
            self._per_sender = {}
            self._global = 0
            self._seeded_from = None
        if self._seeded_from != data_root:
            self._seeded_from = data_root
            for row in read_log(data_root, limit=5000, overlay=False):
                if str(row.get("at", ""))[:10] != today:
                    continue
                units = max(1, int(row.get("n_files") or 0))
                sender = str(row.get("from", ""))
                self._per_sender[sender] = self._per_sender.get(sender, 0) + units
                self._global += units

    def reserve(self, data_root: Path, sender: str, units: int,
                cfg: IntakeConfig) -> bool:
        units = max(1, units)
        with self._lock:
            self._roll(data_root)
            if self._per_sender.get(sender, 0) + units > cfg.sender_daily_cap:
                return False
            if self._global + units > cfg.global_daily_cap:
                return False
            self._per_sender[sender] = self._per_sender.get(sender, 0) + units
            self._global += units
            return True


DAY_BUDGET = DayBudget()

_INFLIGHT_LOCK = threading.Lock()
_INFLIGHT = 0


def try_begin_route() -> bool:
    global _INFLIGHT
    with _INFLIGHT_LOCK:
        if _INFLIGHT >= MAX_INFLIGHT_ROUTES:
            return False
        _INFLIGHT += 1
        return True


def end_route() -> None:
    global _INFLIGHT
    with _INFLIGHT_LOCK:
        _INFLIGHT = max(0, _INFLIGHT - 1)


def disk_low(data_root: Path) -> bool:
    try:
        return shutil.disk_usage(str(data_root)).free < MIN_FREE_DISK_BYTES
    except OSError:
        return False


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


def read_log(data_root: Path, limit: int = 100, overlay: bool = True) -> list[dict]:
    """Acceptance log rows, oldest->newest. With `overlay` (the default)
    each row's status is replaced by the archive meta's CURRENT status, so
    readers see the truth after routing/replay, not the acceptance-time
    snapshot."""
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
    rows = rows[-limit:]
    if overlay:
        for row in rows:
            arch = row.get("archive")
            if not arch:
                continue
            arch_dir = inbound_root(data_root) / str(arch)
            try:
                meta = json.loads(
                    (arch_dir / "meta.json").read_text(encoding="utf-8")
                )
            except Exception:  # noqa: BLE001 - overlay is best-effort
                continue
            row["status"] = meta.get("status", row.get("status"))
            person = meta.get("person")
            if isinstance(person, dict) and person.get("person"):
                row["person"] = person["person"]
            if meta.get("batch_id"):
                row["batch_id"] = meta["batch_id"]
            if meta.get("batch_deleted"):
                row["batch_deleted"] = True
            if meta.get("documents") is not None:
                row["documents"] = meta["documents"]
            files = meta.get("files")
            if files is None:
                # Legacy archive (pre files-in-meta): the delivered names
                # live only as sanitized parts/ copies — derive, no rewrite.
                files = _files_from_parts(arch_dir)
            if files is not None:
                row["files"] = files
            if meta.get("skipped"):
                row["skipped"] = meta["skipped"]
            if meta.get("error"):
                row["error"] = meta["error"]
            # Month-pool stamps (2026-08-24): which month this mail's
            # receipts belong to, and how that month was decided.
            if meta.get("receipt_month"):
                row["pool_month"] = meta["receipt_month"]
            if meta.get("receipt_month_source"):
                row["receipt_month_source"] = meta["receipt_month_source"]
            if meta.get("mixed_months"):
                row["mixed_months"] = True
    return rows


def _files_from_parts(arch_dir: Path) -> list[str] | None:
    """Delivered filenames for a legacy archive, from the parts/ listing
    (``NNN__`` prefix stripped, so the sender's sanitized name remains).
    None when there is no parts dir (body-only or pre-parts archive)."""
    parts = arch_dir / "parts"
    if not parts.is_dir():
        return None
    try:
        return [
            re.sub(r"^\d{3}__", "", p.name)
            for p in sorted(parts.iterdir())
            if p.is_file()
        ]
    except OSError:
        return None


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
        # The delivered filenames as the sender named them (the parts/
        # copies get sanitized names); the intake log's Files column.
        "files": [name for name, _ in parsed.attachments],
        "skipped": parsed.skipped,
        **(extra or {}),
    }
    (arch / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return arch


def _read_meta(arch: Path) -> dict:
    try:
        return json.loads((arch / "meta.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - corrupt meta reads as empty
        return {}


# Meta patches come from several threads at once (SMTP router, ingest
# jobs, replay, and the delete-month sweep): serialize the read-merge-
# write and land it atomically so patches never clobber each other and a
# crash mid-write cannot tear the custody meta.
_META_LOCK = threading.Lock()


def _update_meta(arch: Path, patch: dict) -> None:
    with _META_LOCK:
        meta = _read_meta(arch)
        meta.update(patch)
        tmp = arch / "meta.json.tmp"
        tmp.write_text(
            json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        os.replace(tmp, arch / "meta.json")


def _transition_meta(
    arch: Path, allowed, patch: dict,
) -> tuple[bool, dict]:
    """Compare-and-set on the archive status: under the meta lock, apply
    ``patch`` only when the CURRENT status satisfies ``allowed`` (a callable
    over the meta). Returns (applied, meta-as-read). This is what keeps
    dismiss/render/replay from racing each other into contradictory
    terminal states (adversarial review 2026-08-21 finding 2)."""
    with _META_LOCK:
        meta = _read_meta(arch)
        if not allowed(meta):
            return False, meta
        meta.update(patch)
        tmp = arch / "meta.json.tmp"
        tmp.write_text(
            json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        os.replace(tmp, arch / "meta.json")
        return True, meta


# Archive dir names are our own stamp-digest shape; anything else in the
# URL path segment (traversal, weird casing) resolves to nothing.
_ARCHIVE_NAME_RE = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{8}$")


def _archive_dir(data_root: Path, name: str) -> Path | None:
    if not _ARCHIVE_NAME_RE.fullmatch(str(name or "")):
        return None
    d = inbound_root(data_root) / str(name)
    return d if d.is_dir() else None


def _archive_attachments(arch: Path) -> list[tuple[str, bytes]]:
    """The archive's ingestable files: parts/ as delivered (``NNN__``
    prefix stripped), else the rendered body PDF when that is what the
    mail's content became (a pooled body-only mail claims with it)."""
    parts_dir = arch / "parts"
    out = [
        (re.sub(r"^\d{3}__", "", p.name), p.read_bytes())
        for p in sorted(parts_dir.iterdir())
        if p.is_file()
    ] if parts_dir.is_dir() else []
    if not out and (arch / "rendered-body.pdf").is_file():
        out = [("rendered-body.pdf", (arch / "rendered-body.pdf").read_bytes())]
    return out


def pool_deleted_batch(data_root: Path, batch_id: str) -> tuple[int, int]:
    """Delete-month cascade, pool-aware (2026-08-24). The mail archives
    themselves are NEVER deleted — custody and retention hold regardless
    of what happens to the month.

    Mail that carries a ``receipt_month`` stamp returns to the POOL:
    re-creating the month re-claims it automatically, which supersedes the
    item-19 manual re-ingest path for month-stamped mail. The moment the
    month was deleted stays recorded (``batch_deleted_at``) but the row
    does not say "month deleted" — the mail is simply waiting again.

    Legacy mail (routed before month stamps existed) keeps the
    ``batch_deleted`` stamp and the explicit re-ingest path. Returns
    ``(pooled_back, stamped)``."""
    root = inbound_root(data_root)
    if not root.is_dir():
        return 0, 0
    pooled_back = stamped = 0
    for arch in root.iterdir():
        if not arch.is_dir():
            continue
        meta = _read_meta(arch)
        if str(meta.get("batch_id") or "") != str(batch_id):
            continue
        if meta.get("receipt_month") and _archive_attachments(arch):
            applied, _meta = _transition_meta(
                arch,
                lambda m: str(m.get("status", "")) in {
                    STATUS_INGESTED, STATUS_REPLAYED, HELD_FAILED,
                },
                {
                    "status": STATUS_POOLED, "batch_id": "",
                    "batch_deleted": False, "batch_deleted_at": _now_iso(),
                    # The rows this mail created went with the month; the
                    # next claim writes the new ones.
                    "documents": [],
                },
            )
            if applied:
                pooled_back += 1
                continue
            # Mid-flight states (rendering/claiming/...) fall through to
            # the legacy stamp; their own job's delete guard flips them.
        if meta.get("batch_deleted"):
            continue
        _update_meta(arch, {
            "batch_deleted": True,
            "batch_deleted_at": _now_iso(),
        })
        stamped += 1
    return pooled_back, stamped


def archive_incoming(
    data_root: Path, raw: bytes, parsed: InboundMessage, peer: str = "",
) -> Path:
    """Custody step: archive + acceptance log row, called INLINE in the
    SMTP DATA handler before the 250 goes out. Raises on failure (the
    caller answers 451 so the sender's MTA retries)."""
    arch = archive_message(
        data_root, raw, parsed, STATUS_RECEIVED, extra={"peer": peer}
    )
    _append_log(data_root, {
        "at": _now_iso(),
        "from": parsed.from_addr,
        "subject": parsed.subject,
        "n_files": len(parsed.attachments),
        "status": STATUS_RECEIVED,
        "archive": arch.name,
    })
    return arch


# ---------------------------------------------------------- notifications --
# Acks + held alerts ride graph_notify (internal-only, hard-guarded).
# Both are best-effort side effects: a failed notification never changes
# an archive's status or breaks ingest, and both are idempotent per
# archive via meta stamps (ack_at / alert_at).

_NO_REPLY_LOCALS = ("no-reply", "noreply", "do-not-reply", "postmaster",
                    "mailer-daemon", "bounce")


def _inbound_is_auto_generated(arch: Path) -> bool:
    """True when the archived mail is itself an automatic message (OOF,
    bounce, list mail) — acking those risks loops, so we never do."""
    try:
        msg = BytesParser(policy=policy.default).parsebytes(
            (arch / "message.eml").read_bytes(), headersonly=True
        )
    except Exception:  # noqa: BLE001 - unreadable => be safe, treat as auto
        return True
    auto = str(msg.get("Auto-Submitted", "")).strip().lower()
    if auto and auto != "no":
        return True
    if msg.get("X-Auto-Response-Suppress"):
        return True
    if str(msg.get("Precedence", "")).strip().lower() in ("bulk", "junk", "list"):
        return True
    local = parseaddr(str(msg.get("From", "")))[1].split("@")[0].lower()
    return any(t in local for t in _NO_REPLY_LOCALS)


def _month_human(month: str) -> str:
    """"2026-04" -> "April 2026"; the raw string when malformed."""
    ym = _ym(month)
    if ym is None:
        return month
    return f"{calendar.month_name[ym[1]]} {ym[0]}"


def _maybe_ack(db_path: Path, arch: Path) -> None:
    """Confirmation to the submitting sender once the mail reached a good
    resting place: ingested into its month, or pooled for a month that is
    not open yet. Outcome-aware (2026-08-24): the ack NAMES the month, and
    a pooled ack says the receipt joins that month automatically — so a
    sender never reads "received" as "someone still has to file this".
    Idempotent per archive via ``ack_at`` — a pooled mail that is claimed
    later is not acked twice. Recipient = the real envelope/header sender
    recorded at custody time (never the alias).

    Since submission opened to any sender (2026-08-23), that address can be
    external and forged — so `graph_notify.send_mail`'s own @brisken.com
    recipient guard is what keeps this from becoming a backscatter source:
    an outside submitter simply gets no ack. Do not "fix" that as a missing
    confirmation; replying to unverified strangers as Brisken is the bug."""
    try:
        with RunStore(db_path) as store:
            cfg = IntakeConfig.from_settings(store.get_settings())
            meta = _read_meta(arch)
            batch_label = ""
            if meta.get("batch_id"):
                run = store.get_run(str(meta["batch_id"]))
                if run is not None:
                    batch_label = (run.label or "").strip()
        if not cfg.auto_ack or not graph_notify.enabled():
            return
        if meta.get("ack_at") or _inbound_is_auto_generated(arch):
            return
        recipient = str(meta.get("from", "")).strip().lower()
        n = int(meta.get("n_files") or 0)
        subject = str(meta.get("subject") or "").strip()
        month = str(meta.get("receipt_month") or "")
        if meta.get("status") == STATUS_POOLED:
            verb = "are" if n > 1 else "is"
            landed = (
                f" {verb} stored for {_month_human(month)} in the Brisken "
                "expense tool, and will join that month's expense run "
                "automatically when the month is opened."
            )
        elif batch_label:
            landed = (
                f' landed in the "{batch_label}" expense month in the '
                "Brisken expense tool."
            )
        else:
            landed = (
                " landed in the open expense month in the Brisken "
                "expense tool."
            )
        # A rendered body-only mail delivered no file, so counting files
        # would tell its sender "0 file(s) ... landed", about work that
        # did happen. Name the email itself instead.
        lead = (
            f"{n} file(s) from your email" if n
            else "Your email"
        )
        body = (
            lead
            + (f' "{subject}"' if subject else "")
            + landed
            + " Nothing else to do; Criss reviews them with the "
            "monthly run.\n\nAutomated confirmation from "
            f"receipts@{cfg.domain}."
        )
        if graph_notify.send_mail(
            recipient, "Receipt received" + (f": {subject}" if subject else ""),
            body,
        ):
            _update_meta(arch, {"ack_at": _now_iso()})
    except Exception as exc:  # noqa: BLE001 - notifications never break ingest
        log.warning("ack skipped for %s: %s", arch.name, exc)


def _maybe_alert(db_path: Path, arch: Path, status: str) -> None:
    """Operator alert the first time an archive lands in a held status.
    Without this, held mail is only visible when someone opens the app."""
    try:
        with RunStore(db_path) as store:
            cfg = IntakeConfig.from_settings(store.get_settings())
        if not graph_notify.enabled():
            return
        meta = _read_meta(arch)
        if meta.get("alert_at"):
            return
        body = (
            f"Inbound mail is held ({status}).\n"
            f"From: {meta.get('from', '?')}\n"
            f"Subject: {meta.get('subject', '')}\n"
            f"Archive: {arch.name}\n"
            f"Error: {meta.get('error', '-')}\n\n"
            "Open the tool and use 'Retry held emails' once the cause is "
            "fixed (a held_no_batch drains itself when a month is open)."
        )
        sent = False
        for rcpt in cfg.alert_recipients:
            sent = graph_notify.send_mail(
                rcpt, f"Expense intake: mail held ({status})", body
            ) or sent
        if sent:
            _update_meta(arch, {"alert_at": _now_iso()})
    except Exception as exc:  # noqa: BLE001 - notifications never break ingest
        log.warning("held alert skipped for %s: %s", arch.name, exc)


# ---------------------------------------------------------------- routing --

def open_batch(store: RunStore):
    """Newest expense batch without a statement attached, else None.

    LEGACY selector: month routing (2026-08-24) replaced it for mail, but
    it still answers "where would work land now" for the delete-month
    response and remains the target of the item-19 re-ingest path."""
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if not has_statement(run):
            return run
    return None


# The pool's arbiter. Arrival routing, claiming, replay re-routing and the
# render path all ask the same question — "is this month's batch open?" —
# and then act on the answer. Holding this lock across the QUESTION and the
# status CAS is what makes the answer still true when the CAS lands, so a
# batch created mid-arrival cannot produce both an ingest and a pooled row.
# Ingest itself (vision, minutes) always runs OUTSIDE the hold.
_POOL_LOCK = threading.Lock()


def _ym(month: str) -> tuple[int, int] | None:
    """"YYYY-MM" -> (year, month), else None."""
    m = re.fullmatch(r"(20\d{2})-(0[1-9]|1[0-2])", str(month or "").strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _open_batch_for_month(store: RunStore, ym: tuple[int, int] | None):
    """Newest OPEN expense batch whose label names exactly this month.

    A batch whose label names no month (the default full-date label, a
    free-text name) can never receive pooled mail — the batch-create
    response carries an advisory for that, and a rename claims. A
    statement-bearing batch does not count as open (PR 2 lifts this)."""
    if ym is None:
        return None
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if has_statement(run):
            continue
        if month_from_label(run.label) == ym:
            return run
    return None


def month_batch_states(store: RunStore) -> dict[tuple[int, int], str]:
    """month -> "open" | "closed" over the month-labelled expense batches
    (closed = statement attached). An open batch wins a same-month tie."""
    out: dict[tuple[int, int], str] = {}
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        ym = month_from_label(run.label)
        if ym is None:
            continue
        state = "closed" if has_statement(run) else "open"
        if out.get(ym) != "open":
            out[ym] = state
    return out


def annotate_pool_state(store: RunStore, rows: list[dict]) -> int:
    """Stamp ``pool_month_state`` ("no_batch" | "open" | "closed") on the
    pooled rows of a read_log listing; returns the pooled count. "open" is
    transient — an open month claims its pool on the next trigger."""
    states = month_batch_states(store)
    n = 0
    for row in rows:
        if str(row.get("status", "")) != STATUS_POOLED:
            continue
        n += 1
        ym = _ym(str(row.get("pool_month") or ""))
        row["pool_month_state"] = (
            states.get(ym, "no_batch") if ym else "no_batch"
        )
    return n


def _arrival_llm_client(settings: dict | None):
    """LLM client for arrival-time extraction, composed EXACTLY the way a
    batch config snapshots its client (same llm block incl. vision model,
    same card list) — so the content-addressed extraction cache warmed
    here answers the batch ingest of the same bytes for free. None when
    no key is configured (the caller falls back to the arrival month)."""
    from ..cards import cards_to_setting, effective_cards
    from ..cards_provision import load_cards
    from .service import VISION_MODEL, _batch_llm_client

    cfg: dict = {
        "llm": {
            "provider": "openai", "model": "gpt-4o-mini",
            "vision_model": VISION_MODEL,
        },
        "expense": {},
    }
    try:
        composed = effective_cards(settings, load_cards())
        if composed:
            cfg["expense"]["cards"] = cards_to_setting(composed)
    except Exception:  # noqa: BLE001 - cards salt the cache key; no gate
        pass
    client, _tracker, _source = _batch_llm_client(cfg)
    return client


def _extract_receipt_dates(files: list[Path], client) -> list[str]:
    """ISO dates read off the delivered files via the FULL extraction
    pipeline (not a date-only prompt: a second prompt would be a second
    cache namespace and every mail would pay vision twice). A file that
    fails to extract contributes no date."""
    from ..ingest.receipts_folder import parse_receipt_file

    dates: list[str] = []
    for path in files:
        try:
            receipt = parse_receipt_file(path, "", client)
        except Exception as exc:  # noqa: BLE001 - per-file, keep reading
            log.warning("arrival extraction failed for %s: %s",
                        path.name, exc)
            continue
        if receipt.detected_date is not None:
            dates.append(receipt.detected_date.isoformat())
    return dates


def resolve_receipt_month(
    dates: list[str], arrival_iso: str,
) -> tuple[str, str, bool]:
    """(month "YYYY-MM", source, mixed) per the 2026-08-24 ruling.

    The receipt's own printed date decides its month; for a multi-receipt
    mail the EARLIEST plausible date wins (the whole mail routes as one —
    an April+May mail routes to April, no worse than the old
    newest-open-batch routing). A printed date outside the plausibility
    window counts as unreadable; with no plausible date the mail files
    under its arrival month, source "implausible-receipt" when a clamp
    fired and "arrival" when nothing was readable at all."""
    try:
        arrival = date.fromisoformat(str(arrival_iso)[:10])
    except ValueError:
        # A legacy or corrupt `at` stamp. The arrival is only the yardstick
        # the clamp measures against, so today is a safe substitute — far
        # better than raising through a sweep over every archive.
        arrival = datetime.now(timezone.utc).date()
    plausible: list[date] = []
    clamped = False
    for raw in dates:
        try:
            value = date.fromisoformat(str(raw)[:10])
        except ValueError:
            continue
        if (arrival - value).days > _IMPLAUSIBLE_PAST_DAYS or \
                (value - arrival).days > _FUTURE_GRACE_DAYS:
            clamped = True
            continue
        plausible.append(value)
    if not plausible:
        return (
            f"{arrival.year:04d}-{arrival.month:02d}",
            "implausible-receipt" if clamped else "arrival",
            False,
        )
    earliest = min(plausible)
    months = {(v.year, v.month) for v in plausible}
    return (
        f"{earliest.year:04d}-{earliest.month:02d}",
        "receipt",
        len(months) > 1,
    )


_UNSET = object()


def _month_stamps(
    arch: Path, settings: dict | None, arrival_iso: str, *, client=_UNSET,
) -> dict:
    """Read the archive's parts (rendered body PDF as fallback) and return
    the month-pool meta stamps. Uses the parts already on disk so the
    bytes are read once and the sanitized names keep their suffixes.

    Pass ``client`` to reuse one extraction client across a sweep of
    archives (an explicit ``None`` means "no client, fall back to the
    arrival month"); omit it and one is built per call."""
    parts_dir = arch / "parts"
    files = sorted(
        p for p in parts_dir.iterdir() if p.is_file()
    ) if parts_dir.is_dir() else []
    if not files and (arch / "rendered-body.pdf").is_file():
        files = [arch / "rendered-body.pdf"]
    if client is _UNSET:
        client = _arrival_llm_client(settings)
    dates = _extract_receipt_dates(files, client) if client is not None else []
    month, source, mixed = resolve_receipt_month(dates, arrival_iso)
    return {
        "receipt_month": month,
        "receipt_month_source": source,
        "receipt_dates": dates,
        "mixed_months": mixed,
    }


def _ingest_job(
    db_path: Path, job_id: str, run_id: str, staging: Path,
    learning_db_path: Path | None, provenance: dict[str, dict],
    arch: Path | None,
) -> None:
    try:
        with RunStore(db_path) as store:
            run = store.get_run(run_id)
            if run is None:
                store.set_job_status(
                    job_id, JOB_ERROR, error="run not found",
                    updated_at=_now_iso(),
                )
                if arch is not None:
                    _update_meta(arch, {"status": HELD_FAILED,
                                        "error": "run not found"})
                return
            summary = add_receipts_to_expense_batch(
                store, run, staging, _now_iso(),
                learning_db_path=learning_db_path,
                on_stage=lambda s: store.set_job_stage(job_id, s, _now_iso()),
                provenance_by_digest=provenance,
            )
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id, updated_at=_now_iso()
            )
            # The month can be deleted between our locked write and this
            # stamp (the delete cascade purges jobs by run_id, which was
            # NULL until now). Re-check: if it is gone, flip the job to
            # error and hold the mail — replayable into the next open
            # month — instead of acking receipts into a deleted batch.
            # If the delete lands after this check instead, its cascade
            # removes the row we just stamped.
            batch_gone = store.get_run(run_id) is None
            if batch_gone:
                store.set_job_status(
                    job_id, JOB_ERROR, error="batch deleted",
                    updated_at=_now_iso(),
                )
        # Status truth: "ingested" only after the job ACTUALLY succeeded.
        if arch is not None:
            if batch_gone:
                _update_meta(arch, {"status": HELD_FAILED,
                                    "error": "batch deleted"})
            else:
                # documents = the expense rows THIS mail created (empty when
                # every file was a duplicate) — the intake overview joins
                # on it.
                _update_meta(arch, {
                    "status": STATUS_INGESTED,
                    "documents": list((summary or {}).get("documents") or []),
                })
                _maybe_ack(db_path, arch)
    except Exception as exc:  # noqa: BLE001 - job errors surface via meta+log
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc), updated_at=_now_iso()
            )
        if arch is not None:
            _update_meta(arch, {"status": HELD_FAILED, "error": str(exc)[:400]})
            _maybe_alert(db_path, arch, HELD_FAILED)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _start_ingest(
    db_path: Path,
    learning_db_path: Path | None,
    run,
    attachments: list[tuple[str, bytes]],
    person: dict,
    received_at: str,
    arch: Path | None,
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
                    learning_db_path, provenance, arch)
    else:
        threading.Thread(
            target=_ingest_job,
            args=(db_path, job_id, run.run_id, staging,
                  learning_db_path, provenance, arch),
            daemon=True,
        ).start()
    return job_id


def route_archived(
    db_path: Path,
    learning_db_path: Path | None,
    data_root: Path,
    arch: Path,
    parsed: InboundMessage,
    *,
    synchronous: bool = False,
) -> dict:
    """Routing step for an archived message: resolve person, read the
    receipts' printed dates, and route BY MONTH (2026-08-24) — into the
    open batch whose label names that month, else into the pool.

    The month decision is the whole point of this function now. Mail no
    longer files into "whatever month happens to be open"; a July receipt
    mailed in August waits for July and joins it the moment July opens.
    The ingest job still owns the ingested/held_failed flip; every other
    outcome lands in meta here (held_* for mail we cannot use, ``pooled``
    for mail that is perfectly fine and simply early)."""
    with RunStore(db_path) as store:
        settings = store.get_settings()
    cfg = IntakeConfig.from_settings(settings)
    person = resolve_person(parsed.to_locals, parsed.from_addr, cfg)
    received_at = _now_iso()

    # Single-winner: CAS received -> routing before doing anything. A
    # second router (the replay sweep picking up a stale `received`, a
    # redelivery) sees the transient status and stands down, which also
    # closes the pre-existing double-route window on stale receiveds.
    applied, meta = _transition_meta(
        arch,
        lambda m: str(m.get("status", "")) == STATUS_RECEIVED,
        {"status": STATUS_ROUTING, "person": person},
    )
    if not applied:
        return {
            "status": str(meta.get("status", "")),
            "archive": arch.name,
            "person": meta.get("person") or person,
            "skipped": "already routed",
        }
    arrival_iso = str(meta.get("at") or received_at)

    try:
        # Mail we cannot read as receipts never pays for extraction.
        if parsed.body_only or not parsed.attachments:
            held = HELD_BODY_ONLY if parsed.body_only else HELD_NO_VALID_FILES
            _update_meta(arch, {"status": held})
            _maybe_alert(db_path, arch, held)
            return {"status": held, "archive": arch.name, "person": person}

        # Every attachment mail gets stamped, direct-ingest included: the
        # stamp is what lets a deleted month hand its mail back to the
        # pool instead of stranding it.
        stamps = _month_stamps(arch, settings, arrival_iso)
        _update_meta(arch, stamps)
        month = str(stamps["receipt_month"])

        # Decide atomically: ask whether the month is open and commit the
        # answer under one hold, so a batch created between the two cannot
        # leave this mail both ingested and pooled.
        with _POOL_LOCK:
            with RunStore(db_path) as store:
                run = _open_batch_for_month(store, _ym(month))
            if run is None:
                _transition_meta(
                    arch,
                    lambda m: str(m.get("status", "")) == STATUS_ROUTING,
                    {"status": STATUS_POOLED, "batch_id": "",
                     "batch_deleted": False},
                )
            else:
                # batch_deleted: False clears a stale delete stamp when
                # mail re-routes into a live batch — without it the row
                # would keep saying "month deleted" about live receipts.
                _update_meta(arch, {
                    "batch_id": run.run_id, "batch_deleted": False,
                })

        if run is None:
            _maybe_ack(db_path, arch)
            return {
                "status": STATUS_POOLED, "archive": arch.name,
                "person": person, "pool_month": month,
                "receipt_month_source": stamps["receipt_month_source"],
            }

        job_id = _start_ingest(
            db_path, learning_db_path, run, parsed.attachments, person,
            received_at, arch, synchronous=synchronous,
        )
        _update_meta(arch, {"job_id": job_id})
        final = _read_meta(arch).get("status", STATUS_ROUTING)
        return {
            "status": final if synchronous else STATUS_INGESTED,
            "archive": arch.name, "person": person, "pool_month": month,
            "batch_id": run.run_id, "job_id": job_id,
        }
    except Exception as exc:  # noqa: BLE001 - never raise past the router
        # The SMTP transport already answered 250 and only logs what comes
        # back; an unhandled raise here would leave the mail stuck in the
        # transient `routing` until the next boot sweep. Hold it instead,
        # where replay can drain it.
        err = str(exc)[:400]
        log.warning("routing failed for %s: %s", arch.name, exc)
        held, current = _transition_meta(
            arch,
            lambda m: str(m.get("status", "")) == STATUS_ROUTING,
            {"status": HELD_FAILED, "error": err},
        )
        if held:
            _maybe_alert(db_path, arch, HELD_FAILED)
        return {
            "status": HELD_FAILED if held else str(current.get("status", "")),
            "archive": arch.name, "person": person, "error": err,
        }


def _archive_person(meta: dict) -> dict:
    """The submitter recorded at custody time, or the bare sender when an
    archive predates person resolution."""
    person = meta.get("person")
    if isinstance(person, dict) and person.get("person"):
        return person
    return {
        "person": meta.get("from", ""), "source": "sender",
        "address": meta.get("from", ""),
    }


def has_pooled_mail(data_root: Path) -> bool:
    """Is ANY mail resting in the pool? A meta-only scan, so the boot path
    can decide whether a claim sweep is worth starting at all: a machine
    with an empty pool must not spin up a vision-capable thread to learn
    that it has nothing to do."""
    root = inbound_root(data_root)
    if not root.is_dir():
        return False
    for arch in root.iterdir():
        if str(_read_meta(arch).get("status", "")) == STATUS_POOLED:
            return True
    return False


def claim_pooled(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
) -> dict:
    """The pull half of the pool: drain every pooled mail whose month is
    open now into that month's batch.

    Fires wherever a month can become open — batch create, rename, the
    startup sweep, and the replay endpoint — so a month claims its waiting
    receipts without anyone clicking anything.

    Exactly-once rests on three things: `_POOL_LOCK` held across the "is
    the month open" question and the status CAS, the status itself as
    arbiter (only one caller can move an archive out of ``pooled``), and
    `add_receipts_to_expense_batch`'s content dedupe as the backstop. A
    claim that fails goes BACK to the pool rather than to a held status:
    the pool is the truthful resting place for a receipt whose month
    exists, and the next trigger retries it."""
    root = inbound_root(data_root)
    if not root.is_dir():
        return {"claimed": 0, "still_pooled": 0, "failed": 0}
    claimed = still_pooled = failed = 0
    for arch in sorted(root.iterdir()):
        if not (arch / "meta.json").is_file():
            continue
        meta = _read_meta(arch)
        if str(meta.get("status", "")) != STATUS_POOLED:
            continue
        ym = _ym(str(meta.get("receipt_month") or ""))
        # No month stamp = nothing to match a batch against. Leave it
        # resting and visible rather than guessing a month for it.
        if ym is None or not (
            (arch / "parts").is_dir() or (arch / "rendered-body.pdf").is_file()
        ):
            still_pooled += 1
            continue
        applied = False
        with _POOL_LOCK:
            with RunStore(db_path) as store:
                run = _open_batch_for_month(store, ym)
            if run is not None:
                applied, meta = _transition_meta(
                    arch,
                    lambda m: str(m.get("status", "")) == STATUS_POOLED,
                    {"status": STATUS_CLAIMING, "batch_id": run.run_id,
                     "batch_deleted": False},
                )
        if run is None or not applied:
            # The month is not open, or another claimer moved it first.
            still_pooled += 1
            continue
        # Vision runs outside the pool hold: a claim can take minutes and
        # arrival routing must not queue behind it.
        try:
            attachments = _archive_attachments(arch)
            person = _archive_person(meta)
            job_id = _start_ingest(
                db_path, learning_db_path, run, attachments, person,
                _now_iso(), arch, synchronous=True,
            )
            with RunStore(db_path) as store:
                job = store.get_job(job_id) or {}
        except Exception as exc:  # noqa: BLE001 - one archive, not the sweep
            # A failure before the job existed (staging, disk) leaves the
            # archive in the transient `claiming`. Put it back in the pool
            # here rather than waiting for the next boot sweep to find it.
            log.warning("claim failed for %s: %s", arch.name, exc)
            _transition_meta(
                arch,
                lambda m: str(m.get("status", "")) == STATUS_CLAIMING,
                {"status": STATUS_POOLED, "batch_id": "",
                 "batch_deleted": False, "error": str(exc)[:400]},
            )
            failed += 1
            continue
        if job.get("status") == JOB_DONE:
            # _ingest_job already stamped `ingested` + the documents.
            _update_meta(arch, {"job_id": job_id, "batch_id": run.run_id,
                                "batch_deleted": False})
            _append_log(data_root, {
                "at": _now_iso(), "from": meta.get("from", ""),
                "person": person.get("person"),
                "subject": meta.get("subject", ""),
                "n_files": len(attachments), "status": STATUS_INGESTED,
                "archive": arch.name, "batch_id": run.run_id,
                "job_id": job_id,
            })
            claimed += 1
        else:
            # _ingest_job stamped held_failed + the error; the error stays
            # in meta as the record, but the RESTING state is the pool.
            _transition_meta(
                arch,
                lambda m: str(m.get("status", "")) == HELD_FAILED,
                {"status": STATUS_POOLED, "batch_id": "",
                 "batch_deleted": False},
            )
            failed += 1
    return {
        "claimed": claimed, "still_pooled": still_pooled, "failed": failed,
    }


def process_message(
    db_path: Path,
    learning_db_path: Path | None,
    data_root: Path,
    raw: bytes,
    *,
    peer: str = "",
    synchronous: bool = False,
) -> dict:
    """Archive + route in one call (tests, and any non-SMTP intake). The
    SMTP handler calls the two halves separately so the archive happens
    before the 250."""
    with RunStore(db_path) as store:
        cfg = IntakeConfig.from_settings(store.get_settings())
    parsed = parse_inbound(raw, cfg.domain)
    arch = archive_incoming(data_root, raw, parsed, peer=peer)
    return route_archived(
        db_path, learning_db_path, data_root, arch, parsed,
        synchronous=synchronous,
    )


def _is_replayable(meta: dict, now: datetime) -> bool:
    status = str(meta.get("status", ""))
    if status in REPLAYABLE:
        return True
    if status in {STATUS_RECEIVED, STATUS_ROUTING, STATUS_CLAIMING}:
        # A mail stuck in a transient state = the thread that owned the
        # flip died (crash, scale-to-zero stop) before reaching a resting
        # status. Old enough => replayable.
        try:
            at = datetime.fromisoformat(str(meta.get("at", "")))
        except ValueError:
            return True
        age = (now - at).total_seconds()
        return age > STALE_RECEIVED_SECONDS
    return False


def replay_held(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
) -> dict:
    """Re-route archived mail that is held (legacy no-batch holds, failed
    or interrupted jobs, stale never-routed receipts) BY MONTH: into the
    open batch whose label names the mail's month, else into the pool.

    Body-only holds stay held (they need the round-2 body renderer). An
    archive counts as replayed ONLY when its ingest job reported done.
    Held mail that predates the month stamps is extracted lazily here —
    in the sweep an operator asked for, never at boot."""
    root = inbound_root(data_root)
    if not root.exists():
        return {"replayed": 0, "pooled": 0, "still_held": 0, "failed": 0}
    now = datetime.now(timezone.utc)
    replayed = pooled = still_held = failed = 0
    settings: dict | None = None
    client = _UNSET
    for arch in sorted(root.iterdir()):
        if not (arch / "meta.json").is_file():
            continue
        meta = _read_meta(arch)
        if not _is_replayable(meta, now):
            continue
        # parts/ ONLY here, deliberately: a partless archive must keep
        # flipping to the renderable state below, and reading a
        # rendered-body.pdf as an attachment would rob it of that path.
        parts_dir = arch / "parts"
        attachments = [
            (re.sub(r"^\d{3}__", "", p.name), p.read_bytes())
            for p in sorted(parts_dir.iterdir())
            if p.is_file()
        ] if parts_dir.is_dir() else []
        if not attachments:
            # A partless archive with a readable BODY is body-only mail
            # (router crashed before classifying it, or a failed render):
            # flip it to the renderable state, not the terminal one, or
            # the exact mail class the render path rescues would strand
            # (adversarial review 2026-08-21 finding 3).
            from .body_render import extract_body_text

            has_body = False
            eml = arch / "message.eml"
            if eml.is_file():
                has_body = bool(extract_body_text(eml.read_bytes()).strip())
            _update_meta(arch, {
                "status": HELD_BODY_ONLY if has_body else HELD_NO_VALID_FILES
            })
            still_held += 1
            continue
        # Month-route it. Held mail from before the pool existed has no
        # stamp yet; read its dates now, once, reusing one client for the
        # whole sweep.
        if not meta.get("receipt_month"):
            try:
                if settings is None:
                    with RunStore(db_path) as store:
                        settings = store.get_settings()
                if client is _UNSET:
                    client = _arrival_llm_client(settings)
                stamps = _month_stamps(
                    arch, settings, str(meta.get("at") or _now_iso()),
                    client=client,
                )
                _update_meta(arch, stamps)
                meta = {**meta, **stamps}
            except Exception as exc:  # noqa: BLE001 - skip it, not the sweep
                log.warning("month stamp failed for %s: %s", arch.name, exc)
                still_held += 1
                continue
        held_status = str(meta.get("status", ""))
        with _POOL_LOCK:
            # Re-resolve per archive INSIDE the hold: a statement attach
            # mid-drain closes the month and later archives must pool, not
            # error into the void.
            with RunStore(db_path) as store:
                run = _open_batch_for_month(
                    store, _ym(str(meta.get("receipt_month") or ""))
                )
            if run is None:
                _transition_meta(
                    arch,
                    lambda m, s=held_status: str(m.get("status", "")) == s,
                    {"status": STATUS_POOLED, "batch_id": "",
                     "batch_deleted": False},
                )
        if run is None:
            pooled += 1
            continue
        person = _archive_person(meta)
        job_id = _start_ingest(
            db_path, learning_db_path, run, attachments, person,
            _now_iso(), arch, synchronous=True,
        )
        with RunStore(db_path) as store:
            job = store.get_job(job_id) or {}
        if job.get("status") == JOB_DONE:
            _update_meta(arch, {
                "status": STATUS_REPLAYED, "job_id": job_id,
                "batch_id": run.run_id, "batch_deleted": False,
            })
            _append_log(data_root, {
                "at": _now_iso(), "from": meta.get("from", ""),
                "person": person.get("person"),
                "subject": meta.get("subject", ""),
                "n_files": len(attachments), "status": STATUS_REPLAYED,
                "archive": arch.name, "batch_id": run.run_id,
                "job_id": job_id,
            })
            replayed += 1
        else:
            # _ingest_job already stamped held_failed + the error.
            failed += 1
    return {
        "replayed": replayed, "pooled": pooled,
        "still_held": still_held, "failed": failed,
    }


def reconcile_interrupted(db_path: Path, data_root: Path) -> int:
    """Startup sweep companion: an archive whose meta says ingested but
    whose job row ended error/interrupted was killed mid-ingest (Fly stop).
    Flip it back to held_failed so replay can drain it. Returns the count."""
    root = inbound_root(data_root)
    if not root.exists():
        return 0
    flipped = 0
    with RunStore(db_path) as store:
        for arch in root.iterdir():
            meta = _read_meta(arch)
            job_id = meta.get("job_id")
            # A kill mid-ROUTE or mid-CLAIM leaves those transient states
            # behind. They differ in where the mail belongs afterwards: a
            # half-routed mail never reached a resting place, so it holds
            # (and alerts); a half-claimed one has a perfectly good one
            # already, so it simply goes back to waiting — no alert, and
            # the next claim trigger picks it up.
            if meta.get("status") in (STATUS_ROUTING, STATUS_CLAIMING):
                job = store.get_job(str(job_id)) if job_id else None
                if job is not None and job.get("status") == JOB_DONE:
                    # The ingest actually finished; the stale-state replay
                    # and the content dedupe absorb the missing flip.
                    continue
                if meta.get("status") == STATUS_ROUTING:
                    _update_meta(arch, {"status": HELD_FAILED,
                                        "error": "routing interrupted"})
                    _maybe_alert(db_path, arch, HELD_FAILED)
                else:
                    _update_meta(arch, {"status": STATUS_POOLED,
                                        "batch_id": "",
                                        "batch_deleted": False})
                flipped += 1
                continue
            # A kill mid-RENDER leaves the transient "rendering" status
            # (the sync ingest owned the flip and never got there). Flip
            # to held_failed; the rendered stamp keeps it retryable.
            if meta.get("status") == STATUS_RENDERING:
                job = store.get_job(str(job_id)) if job_id else None
                if job is None or job.get("status") != JOB_DONE:
                    _update_meta(arch, {"status": HELD_FAILED,
                                        "error": "render interrupted"})
                    _maybe_alert(db_path, arch, HELD_FAILED)
                    flipped += 1
                continue
            # A kill mid-ingest leaves status "received" (the job owns the
            # flip and never got there) with the job row marked interrupted
            # by the startup sweep; "ingested" with a bad job is belt+braces.
            if not job_id or meta.get("status") not in (
                STATUS_RECEIVED, STATUS_INGESTED
            ):
                continue
            job = store.get_job(str(job_id))
            if job is None:
                continue
            if job.get("status") != JOB_DONE:
                _update_meta(arch, {"status": HELD_FAILED,
                                    "error": "job interrupted"})
                _maybe_alert(db_path, arch, HELD_FAILED)
                flipped += 1
    return flipped


def sweep_retention(db_path: Path, data_root: Path) -> int:
    """Delete inbound archives older than the configured retention floor
    (settings intake.retention_years, default 10 per AO paragraph 147).
    Runs at startup, fail-open; the archive-name stamp is the age source
    so nothing outside the inbound naming pattern is ever touched."""
    root = inbound_root(data_root)
    if not root.exists():
        return 0
    with RunStore(db_path) as store:
        cfg = IntakeConfig.from_settings(store.get_settings())
    cutoff = datetime.now(timezone.utc).timestamp() - (
        cfg.retention_years * 365.25 * 86400
    )
    removed = 0
    for arch in list(root.iterdir()):
        m = re.match(r"^(\d{8}T\d{6})-[0-9a-f]{8}$", arch.name)
        if not m or not arch.is_dir():
            continue
        try:
            stamp = datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        if stamp.timestamp() < cutoff:
            shutil.rmtree(arch, ignore_errors=True)
            removed += 1
    if removed:
        log.info("retention sweep removed %d expired inbound archives", removed)
    return removed


# ------------------------------------------- body-only mail handling (C2) --
# held_body_only was terminal: no view, no ingest path, no way to clear
# the held strip. Three per-archive actions fix that: read the body
# (sanitized text off the custody eml), render it to a PDF and run the
# NORMAL ingest path (vision + quarantine judge it like any scanned
# receipt), or dismiss it as junk.


def read_body_view(data_root: Path, archive: str) -> dict | None:
    """Sanitized body view of an archived mail: plain text (HTML stripped),
    never the raw archive. None when the archive does not exist."""
    from .body_render import extract_body_text

    arch = _archive_dir(data_root, archive)
    if arch is None or not (arch / "message.eml").exists():
        return None
    meta = _read_meta(arch)
    text = extract_body_text((arch / "message.eml").read_bytes())
    return {
        "archive": arch.name,
        "from": meta.get("from", ""),
        "subject": meta.get("subject", ""),
        "at": meta.get("at", ""),
        "status": meta.get("status", ""),
        "text": text,
    }


def render_ingest(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
    archive: str, operator: str | None = None,
) -> dict:
    """Render a held body-only mail's body to a PDF and month-route it via
    the normal path (document-type quarantine and vision extraction apply
    unchanged): into the batch for the date the rendered PDF prints, else
    into the pool. Deny-by-default guards; the rendered PDF is kept at the
    archive ROOT (parts/ stays exactly what was delivered, so the Files
    column never lists a derived artifact).

    "No open month" is no longer a refusal. The render always happens and
    the result always lands somewhere — a month or the pool — because
    telling an operator "try again later" about work already done is how
    body-only mail used to strand."""
    from .body_render import extract_body_text, render_body_pdf

    arch = _archive_dir(data_root, archive)
    if arch is None or not (arch / "message.eml").exists():
        return {"error": "not found", "code": 404}
    text = extract_body_text((arch / "message.eml").read_bytes())
    if not text.strip():
        return {"error": "no readable body in this mail", "code": 409}

    def _renderable(meta: dict) -> bool:
        status = meta.get("status")
        # Body-only held mail, plus RETRY after a failed render ingest
        # (the failure flipped it to held_failed; a replay pass with no
        # parts/ flips that to held_no_valid_files — the `rendered` stamp
        # marks both as render history, not a delivery state).
        return status == HELD_BODY_ONLY or (
            bool(meta.get("rendered"))
            and status in {HELD_FAILED, HELD_NO_VALID_FILES}
        )

    # CAS to the transient "rendering" status: a concurrent second render,
    # a dismiss, or a replay pass all see it and refuse — no interleaving
    # can reverse an acknowledged action or double-start the ingest.
    # No batch_id in this patch: which month this mail belongs to is not
    # known until the rendered PDF has been read.
    applied, meta = _transition_meta(arch, _renderable, {
        "status": STATUS_RENDERING,
        "rendered": True, "rendered_at": _now_iso(),
        "rendered_by": operator or "",
    })
    if not applied:
        return {"error": "only body-only held mail can be rendered "
                         f"(status: {meta.get('status', '')})", "code": 409}

    header = [
        f"From: {meta.get('from', '')}",
        f"Subject: {meta.get('subject', '')}",
        f"Received: {meta.get('at', '')}",
        "Rendered from e-mail body (no attachment was delivered)",
    ]
    created = None
    try:
        created = datetime.strptime(
            arch.name.split("-", 1)[0], "%Y%m%dT%H%M%S"
        ).timetuple()
    except ValueError:
        pass
    try:
        pdf = render_body_pdf(header, text, created=created)
        (arch / "rendered-body.pdf").write_bytes(pdf)
        # The rendered PDF IS this mail's content, so it is what decides
        # the month — same reader, same cache, as a delivered attachment.
        with RunStore(db_path) as store:
            settings = store.get_settings()
        stamps = _month_stamps(
            arch, settings, str(meta.get("at") or _now_iso())
        )
        _update_meta(arch, stamps)
    except Exception as exc:  # noqa: BLE001 - hold it, keep it retryable
        # The `rendered` stamp survives, so _renderable admits a retry
        # exactly as it does after a failed ingest.
        _transition_meta(
            arch,
            lambda m: str(m.get("status", "")) == STATUS_RENDERING,
            {"status": HELD_FAILED, "error": str(exc)[:400]},
        )
        log.warning("render failed for %s: %s", arch.name, exc)
        return {"error": f"render failed: {exc}", "code": 500}

    month = str(stamps["receipt_month"])
    with _POOL_LOCK:
        with RunStore(db_path) as store:
            run = _open_batch_for_month(store, _ym(month))
        if run is None:
            _transition_meta(
                arch,
                lambda m: str(m.get("status", "")) == STATUS_RENDERING,
                {"status": STATUS_POOLED, "batch_id": "",
                 "batch_deleted": False},
            )
        else:
            _update_meta(arch, {
                "batch_id": run.run_id, "batch_deleted": False,
            })
    if run is None:
        _maybe_ack(db_path, arch)
        return {
            "status": STATUS_POOLED, "archive": arch.name,
            "pool_month": month,
        }

    person = _archive_person(meta)
    job_id = _start_ingest(
        db_path, learning_db_path, run, [("rendered-body.pdf", pdf)],
        person, _now_iso(), arch, synchronous=True,
    )
    final = _read_meta(arch)
    return {
        "status": final.get("status", ""),
        "archive": arch.name,
        "batch_id": run.run_id,
        "pool_month": month,
        "job_id": job_id,
        "documents": final.get("documents", []),
    }


def re_ingest(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
    archive: str, operator: str | None = None,
) -> dict:
    """Re-ingest ONE archive's delivered attachments into the month that is
    open now (backlog item 19, owner-approved 2026-08-22).

    The gap: a mail whose attachments were already ingested into a month that
    is later deleted has no way back. Replay skips it (status `ingested` is
    not replayable, and rightly so), the expenses went with the month, and the
    bytes sit in the custody archive unreachable from the app. This is the
    explicit way back, one archive at a time, so receipts can never drain into
    a month nobody chose.

    LEGACY as of 2026-08-24: month-stamped mail no longer strands, because
    deleting a month returns it to the POOL and re-creating the month
    re-claims it. This path remains for mail that predates the stamps,
    which is the only mail the delete cascade still marks `batch_deleted`.

    Deny-by-default: only mail carrying the `batch_deleted` stamp qualifies.
    A mail whose month is alive is refused, which is what keeps this from
    becoming a way to copy one month's receipts into another. Dismissed mail
    and anything mid-flight are refused too. Re-ingesting a second time hits
    the live-month refusal, because the first call cleared the stamp.
    """
    arch = _archive_dir(data_root, archive)
    if arch is None:
        return {"error": "not found", "code": 404}
    parts_dir = arch / "parts"
    attachments = [
        (re.sub(r"^\d{3}__", "", f.name), f.read_bytes())
        for f in sorted(parts_dir.iterdir())
        if f.is_file()
    ] if parts_dir.is_dir() else []
    if not attachments:
        return {
            "error": "this mail delivered no attachment to re-ingest; a "
                     "body-only mail is recovered with render-ingest",
            "code": 409,
        }
    with RunStore(db_path) as store:
        run = open_batch(store)
    if run is None:
        return {"error": "no open month to ingest into", "code": 409}

    def _stranded(meta: dict) -> bool:
        if not meta.get("batch_deleted"):
            return False
        return str(meta.get("status", "")) not in {
            STATUS_DISMISSED, STATUS_RENDERING, STATUS_REINGESTING,
        }

    # CAS to a transient status for the same reason render-ingest has one: a
    # second click, a dismiss, or a replay pass all see it and refuse rather
    # than interleaving into a double ingest.
    applied, meta = _transition_meta(arch, _stranded, {
        "status": STATUS_REINGESTING,
        "re_ingested": True, "re_ingested_at": _now_iso(),
        "re_ingested_by": operator or "",
        "batch_id": run.run_id, "batch_deleted": False,
    })
    if not applied:
        status = str(meta.get("status", ""))
        if not meta.get("batch_deleted"):
            return {
                "error": "this mail still belongs to a live month; re-ingest "
                         "exists for mail stranded by a deleted month",
                "code": 409,
            }
        return {
            "error": f"cannot re-ingest mail in state {status!r}",
            "code": 409,
        }

    person = meta.get("person") or {
        "person": meta.get("from", ""), "source": "sender",
        "address": meta.get("from", ""),
    }
    job_id = _start_ingest(
        db_path, learning_db_path, run, attachments, person,
        _now_iso(), arch, synchronous=True,
    )
    final = _read_meta(arch)
    return {
        "status": final.get("status", ""),
        "archive": arch.name,
        "batch_id": run.run_id,
        "job_id": job_id,
        "documents": final.get("documents", []),
    }


def dismiss_archive(
    data_root: Path, archive: str, operator: str | None = None,
) -> dict:
    """Mark a held or pooled mail dismissed (operator judged it junk).
    Terminal by design: not replayable, not renderable, not claimable,
    drops out of n_held / n_pooled. The custody archive is untouched.

    Pooled mail is dismissable for the same reason held mail is: junk
    with an attachment now RESTS in the pool waiting for a month that may
    never come, and without this it would wait there undismissably."""
    arch = _archive_dir(data_root, archive)
    if arch is None:
        return {"error": "not found", "code": 404}
    applied, meta = _transition_meta(
        arch,
        lambda m: (
            str(m.get("status", "")).startswith("held_")
            or str(m.get("status", "")) == STATUS_POOLED
        ),
        {
            "status": STATUS_DISMISSED,
            "dismissed_at": _now_iso(),
            "dismissed_by": operator or "",
        },
    )
    if not applied:
        return {"error": "only held or pooled mail can be dismissed "
                         f"(status: {meta.get('status', '')})", "code": 409}
    return {"status": STATUS_DISMISSED, "archive": arch.name}
