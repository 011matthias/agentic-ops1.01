"""Mail-intake core: the app's own mailbox (expenses.brisken.com).

Faculty (or Criss forwarding on their behalf) mail receipts to the intake
address; the SMTP listener (`smtp_server.py`) drives this module:

  1. `parse_inbound` reads the MIME (attachments incl. inline images;
     body-only detected; zips REFUSED at this boundary — the authenticated
     operator upload is the zip path; a mailed zip would count as one file
     against the spend budget while expanding to up to 80 vision calls),
  2. the sender allowlist is deny-by-default (the SMTP layer turns a
     refusal into an in-protocol 550, so the sender's own mail system
     generates the bounce and we never send anything),
  3. `archive_incoming` writes the raw message + parts under
     ``/data/inbound/<stamp>/`` and the acceptance log row BEFORE the SMTP
     250 is answered (the ack means custody: a crash after 250 can no
     longer lose acknowledged mail),
  4. `route_archived` resolves WHO submitted it (To-alias beats
     From-sender), picks the newest OPEN expense batch, and runs the
     existing incremental add (dedupe, quarantine, categorize unchanged)
     stamping per-file intake provenance; the archive's status flips to
     ``ingested`` only when the job actually succeeded, else
     ``held_failed`` so replay can drain it,
  5. spend/abuse guards: an in-memory day budget reserved at acceptance
     time (raceproof within the process), an in-flight route ceiling, and
     a free-disk floor — each refusal is a 4xx/5xx SMTP answer, never a
     silent drop.

Held mail (no open batch, body-only, no valid files, failed/interrupted
jobs) is archived + visible via ``GET /api/inbound/log``;
``POST /api/inbound/replay-held`` re-routes it once a batch exists.

Decision logic is pure/sync (testable without asyncio); only the SMTP
transport in `smtp_server.py` is async.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from pathlib import Path

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
DEFAULT_SENDER_ALLOWLIST = ("@brisken.com",)
# Cost guard on the vision spend a runaway/compromised sender could cause.
# Units = max(1, attachment count) per accepted message, so zero-file spam
# consumes budget too.
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
HELD_NO_BATCH = "held_no_batch"        # replayable
HELD_FAILED = "held_failed"            # job errored/interrupted; replayable
HELD_BODY_ONLY = "held_body_only"      # needs body->PDF rendering (round 2)
HELD_NO_VALID_FILES = "held_no_valid_files"
STATUS_DISMISSED = "dismissed"         # operator judged it junk; terminal
STATUS_RENDERING = "rendering"         # body->PDF ingest in flight (C2)
REPLAYABLE = {HELD_NO_BATCH, HELD_FAILED}
STALE_RECEIVED_SECONDS = 600


@dataclass(frozen=True)
class IntakeConfig:
    domain: str = DEFAULT_INTAKE_DOMAIN
    sender_allowlist: tuple[str, ...] = DEFAULT_SENDER_ALLOWLIST
    aliases: dict = field(default_factory=dict)  # local-part -> person name
    sender_daily_cap: int = DEFAULT_SENDER_DAILY_CAP
    global_daily_cap: int = DEFAULT_GLOBAL_DAILY_CAP
    auto_ack: bool = True
    alert_recipients: tuple[str, ...] = DEFAULT_ALERT_RECIPIENTS
    retention_years: int = DEFAULT_RETENTION_YEARS

    @classmethod
    def from_settings(cls, settings: dict | None) -> "IntakeConfig":
        """Settings key ``intake``: {domain, senders: [...], aliases: {...},
        sender_daily_cap, global_daily_cap, auto_ack, alert_recipients,
        retention_years}. Env overrides the domain
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

        # Alert recipients keep only internal-looking addresses; the Graph
        # layer re-asserts @brisken.com per send regardless.
        alerts = tuple(
            a.strip().lower()
            for a in (raw.get("alert_recipients") or DEFAULT_ALERT_RECIPIENTS)
            if isinstance(a, str) and "@" in a.strip()
        ) or DEFAULT_ALERT_RECIPIENTS

        return cls(
            domain=domain,
            sender_allowlist=senders,
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
    senders = raw.get("senders")
    if senders is not None:
        if not isinstance(senders, list) or not all(
            isinstance(s, str) and s.strip() for s in senders
        ):
            raise ValueError(
                "intake.senders must be a list of addresses or @domains"
            )
        entries = [s.strip().lower() for s in senders]
        # An entry with no '@' anywhere can never match sender_allowed and
        # would silently 550 ALL mail — refuse it at the edge instead.
        bad = [s for s in entries if "@" not in s]
        if bad:
            raise ValueError(
                "intake.senders entries must be full addresses or start "
                f"with '@' (got: {bad[0]!r})"
            )
        cleaned["senders"] = entries
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


def mark_batch_deleted(data_root: Path, batch_id: str) -> int:
    """Stamp ``batch_deleted`` on every inbound archive whose mail routed
    into ``batch_id`` (the delete-month cascade). The mail archives
    themselves are NEVER deleted — custody and retention hold regardless
    of what happens to the month; the stamp lets the intake log say "month
    deleted" instead of misreporting the mail's rows as operator-removed.
    Returns the number of archives stamped."""
    root = inbound_root(data_root)
    if not root.is_dir():
        return 0
    n = 0
    for arch in root.iterdir():
        if not arch.is_dir():
            continue
        meta = _read_meta(arch)
        if str(meta.get("batch_id") or "") != str(batch_id):
            continue
        if meta.get("batch_deleted"):
            continue
        _update_meta(arch, {
            "batch_deleted": True,
            "batch_deleted_at": _now_iso(),
        })
        n += 1
    return n


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


def _maybe_ack(db_path: Path, arch: Path) -> None:
    """Confirmation to the submitting sender after a SUCCESSFUL ingest.
    Recipient = the real envelope/header sender recorded at custody time
    (never the alias), which the allowlist already proved is internal."""
    try:
        with RunStore(db_path) as store:
            cfg = IntakeConfig.from_settings(store.get_settings())
        if not cfg.auto_ack or not graph_notify.enabled():
            return
        meta = _read_meta(arch)
        if meta.get("ack_at") or _inbound_is_auto_generated(arch):
            return
        recipient = str(meta.get("from", "")).strip().lower()
        n = int(meta.get("n_files") or 0)
        subject = str(meta.get("subject") or "").strip()
        body = (
            f"{n} file(s) from your email"
            + (f' "{subject}"' if subject else "")
            + " landed in the open expense month in the Brisken expense "
            "tool. Nothing else to do; Criss reviews them with the "
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
    """Routing step for an archived message: resolve person, pick the open
    batch, hand off to the ingest job (which owns the ingested/held_failed
    status flip). Every non-ingest outcome lands in meta as a held status."""
    with RunStore(db_path) as store:
        cfg = IntakeConfig.from_settings(store.get_settings())
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

    if status != STATUS_INGESTED:
        _update_meta(arch, {"status": status, "person": person})
        _maybe_alert(db_path, arch, status)
        return {"status": status, "archive": arch.name, "person": person}

    # The job flips the meta to ingested/held_failed when it finishes.
    # batch_deleted: False clears a stale delete stamp when a held mail
    # re-routes into a live batch — without it the row would keep saying
    # "month deleted" about receipts alive in the new month.
    _update_meta(arch, {
        "person": person, "batch_id": run.run_id, "batch_deleted": False,
    })
    job_id = _start_ingest(
        db_path, learning_db_path, run, parsed.attachments, person,
        received_at, arch, synchronous=synchronous,
    )
    _update_meta(arch, {"job_id": job_id})
    final = _read_meta(arch).get("status", STATUS_RECEIVED)
    return {
        "status": final if synchronous else STATUS_INGESTED,
        "archive": arch.name, "person": person,
        "batch_id": run.run_id, "job_id": job_id,
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
    if status == STATUS_RECEIVED:
        # A "received" that never routed = the router died before/during
        # routing (crash, scale-to-zero stop). Old enough => replayable.
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
    """Re-route archived mail that is held (no batch at arrival, failed or
    interrupted jobs, stale never-routed receipts) into the now-open batch.
    Body-only holds stay held (they need the round-2 body renderer). An
    archive counts as replayed ONLY when its ingest job reported done."""
    root = inbound_root(data_root)
    if not root.exists():
        return {"replayed": 0, "still_held": 0, "failed": 0}
    now = datetime.now(timezone.utc)
    replayed = still_held = failed = 0
    for arch in sorted(root.iterdir()):
        if not (arch / "meta.json").is_file():
            continue
        meta = _read_meta(arch)
        if not _is_replayable(meta, now):
            continue
        # Re-resolve per archive: a statement attach mid-drain closes the
        # batch and later archives must hold, not error into the void.
        with RunStore(db_path) as store:
            run = open_batch(store)
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
        person = meta.get("person") or {
            "person": meta.get("from", ""), "source": "sender",
            "address": meta.get("from", ""),
        }
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
    return {"replayed": replayed, "still_held": still_held, "failed": failed}


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
    """Render a held body-only mail's body to a PDF and ingest it into the
    open month via the normal path (document-type quarantine and vision
    extraction apply unchanged). Deny-by-default guards; the rendered PDF
    is kept at the archive ROOT (parts/ stays exactly what was delivered,
    so the Files column never lists a derived artifact)."""
    from .body_render import extract_body_text, render_body_pdf

    arch = _archive_dir(data_root, archive)
    if arch is None or not (arch / "message.eml").exists():
        return {"error": "not found", "code": 404}
    text = extract_body_text((arch / "message.eml").read_bytes())
    if not text.strip():
        return {"error": "no readable body in this mail", "code": 409}
    with RunStore(db_path) as store:
        run = open_batch(store)
    if run is None:
        return {"error": "no open month to ingest into", "code": 409}

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
    applied, meta = _transition_meta(arch, _renderable, {
        "status": STATUS_RENDERING,
        "rendered": True, "rendered_at": _now_iso(),
        "rendered_by": operator or "",
        "batch_id": run.run_id, "batch_deleted": False,
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
    pdf = render_body_pdf(header, text, created=created)
    (arch / "rendered-body.pdf").write_bytes(pdf)
    person = meta.get("person") or {
        "person": meta.get("from", ""), "source": "sender",
        "address": meta.get("from", ""),
    }
    job_id = _start_ingest(
        db_path, learning_db_path, run, [("rendered-body.pdf", pdf)],
        person, _now_iso(), arch, synchronous=True,
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
    """Mark a held mail dismissed (operator judged it junk). Terminal by
    design: not replayable, not renderable, drops out of n_held. The
    custody archive itself is untouched."""
    arch = _archive_dir(data_root, archive)
    if arch is None:
        return {"error": "not found", "code": 404}
    applied, meta = _transition_meta(
        arch,
        lambda m: str(m.get("status", "")).startswith("held_"),
        {
            "status": STATUS_DISMISSED,
            "dismissed_at": _now_iso(),
            "dismissed_by": operator or "",
        },
    )
    if not applied:
        return {"error": "only held mail can be dismissed "
                         f"(status: {meta.get('status', '')})", "code": 409}
    return {"status": STATUS_DISMISSED, "archive": arch.name}
