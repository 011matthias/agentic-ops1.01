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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from pathlib import Path

from ..batch_period import month_from_label
from ..error_codes import CodedValueError
from .. import untrusted
from . import graph_notify
from .service import (
    BATCH_TYPE_TRIP,
    FOLDER_RECEIPT_SUFFIXES,
    MODE_EXPENSE_GENERATION,
    RunInputError,
    add_receipts_to_expense_batch,
    claim_trip_batch_slot,
    create_expense_batch,
    execute_expense_batch,
    find_trip_batch,
    has_statement,
    is_trip_batch,
    release_trip_batch_slot,
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
# The known-sender list is meant to stay a handful of private addresses
# our own people mail from, not a second allowlist for submission (that
# one is gone). A ceiling keeps it that way.
MAX_KNOWN_SENDERS = 25
# `rendered_by` on mail the arrival path rendered without a human.
AUTO_RENDER_OPERATOR = "auto"
MAX_INFLIGHT_ROUTES = 8
# Free-disk floor (backlog item 122). It used to be a flat 500 MiB, which
# on the 1 GB volume meant the mailbox turned EVERY receipt away once the
# disk was half full — Dirk's mail bouncing mid-close would have been the
# first sign. The floor is now read from the actual volume: a share of it,
# never below 200 MB, and never more than half of a small disk (so a tiny
# test volume does not refuse from empty). On 1 GB that is 200 MB, on 5 GB
# 256 MB, and the same code is correct on both without a redeploy.
MIN_FREE_DISK_FLOOR_BYTES = 200 * 1024 * 1024
MIN_FREE_DISK_FRACTION = 0.05
# A stranger's message is capped far below the listener's 25 MB ceiling,
# and all unrecognised senders together get a daily byte budget. Anyone
# may submit (owner directive 2026-08-23) and From is forgeable, so the
# budget is deliberately GLOBAL rather than per-sender: a rotating From
# walks straight past a per-sender one, which is the same reasoning the
# file caps above already carry. Our own people (inside @brisken.com or
# listed in intake.known_senders) are subject to neither.
DEFAULT_UNKNOWN_MAX_MESSAGE_BYTES = 5 * 1024 * 1024
DEFAULT_UNKNOWN_DAILY_BYTES = 50 * 1024 * 1024
# Purge for archives the operator judged junk (item 122). Days since the
# DISMISSAL, not since arrival. 0 = never, which is the default: deleting
# Brisken's mail is the owner's call, so the sweep ships inert and one
# settings write (intake.dismissed_purge_days) turns it on.
DEFAULT_DISMISSED_PURGE_DAYS = 0

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
# Arrival-time duplicate detection (owner directive 2026-08-25: "sort
# duplicates out before they are ingested"). A RESTING state, not held_*
# and not dismissed: nothing is wrong with the mail and nobody has to act,
# we simply already hold this receipt. Terminal unless an operator says it
# is not a duplicate, which is why the mail is parked rather than dropped.
STATUS_DUPLICATE = "duplicate"
REPLAYABLE = {HELD_NO_BATCH, HELD_FAILED}

# Only a mail that actually ENTERED the workflow owns its content. A
# dismissed or still-held archive does not: if the first copy was judged
# junk or never got past a hold, the tool does NOT hold that receipt, and
# calling the next copy a duplicate would hide a receipt nobody ingested.
OWNS_CONTENT = {
    STATUS_INGESTED, STATUS_REPLAYED, STATUS_POOLED,
    STATUS_ROUTING, STATUS_CLAIMING,
}
STALE_RECEIVED_SECONDS = 600

# How a status READS, shipped beside it (2026-08-24). `status` is an
# enum-ish field that has grown three times; each time an un-updated SPA
# mapped the new value onto whatever its own map fell through to, and on
# 2026-08-24 that made six of Dirk's resting receipts announce
# "Arriving" indefinitely. A confident wrong label is worse than a raw
# one, so every row now also carries a KIND (how to treat it) and a
# composed English LABEL (what to say), and an unrecognised status
# degrades to kind "unknown" plus the raw value rather than to somebody
# else's copy. Same shape as issues + issue_details: prose in English,
# a stable code beside it for the SPA to localize.
KIND_RESTING = "resting"    # fine, and waiting on something scheduled
KIND_HELD = "held"          # needs a human
KIND_WORKING = "working"    # in flight, resolves on its own in seconds
KIND_DONE = "done"          # finished, nothing owed
KIND_UNKNOWN = "unknown"    # a status this build does not know

_STATUS_VIEW: dict[str, tuple[str, str]] = {
    STATUS_RECEIVED: (KIND_WORKING, "Arriving"),
    STATUS_ROUTING: (KIND_WORKING, "Filing"),
    STATUS_CLAIMING: (KIND_WORKING, "Joining its month"),
    STATUS_RENDERING: (KIND_WORKING, "Reading the email"),
    STATUS_REINGESTING: (KIND_WORKING, "Re-filing"),
    STATUS_INGESTED: (KIND_DONE, "Added"),
    STATUS_REPLAYED: (KIND_DONE, "Added"),
    STATUS_DISMISSED: (KIND_DONE, "Dismissed"),
    HELD_NO_BATCH: (KIND_HELD, "Waiting for a month to open"),
    HELD_FAILED: (KIND_HELD, "Needs a retry"),
    HELD_BODY_ONLY: (KIND_HELD, "Needs one click to read"),
    HELD_NO_VALID_FILES: (KIND_HELD, "No receipt file in this email"),
    # `pooled` composes its month into the label; see annotate_status_view.
    STATUS_POOLED: (KIND_RESTING, "Waiting for its month"),
    # `duplicate` composes the original's subject in; see annotate_status_view.
    STATUS_DUPLICATE: (KIND_RESTING, "Already have this"),
}

# The refusal ledger (backlog item 30 b). A refused RCPT or a guard that
# turns mail away at DATA is the one intake outcome that left no trace
# anywhere: no archive, no log row, no counter. Bounded on disk by a
# rewrite that keeps the newest rows, so a scanner hammering the listener
# cannot fill the volume.
REFUSAL_LOG_MAX_BYTES = 512 * 1024
REFUSAL_KEEP_ROWS = 200
REFUSAL_WINDOW_DAYS = 7

# Plausibility clamp on a receipt's printed date (owner ruling 2026-08-24):
# older than ~12 months before arrival, or in the future, counts as
# unreadable and the mail files under its ARRIVAL month instead. One day of
# future grace absorbs timezone skew on a same-day receipt.
_IMPLAUSIBLE_PAST_DAYS = 366
_FUTURE_GRACE_DAYS = 1


def auto_materialize_enabled() -> bool:
    """Item 39 (owner directive 2026-09-06): mailed receipts become
    expenses on their own, creating their month batch when the printed
    month is confidently known. Default OFF — with the flag unset, arrival
    routing behaves exactly as before (the pool waits)."""
    return os.environ.get("EXPENSE_RECON_AUTO_MATERIALIZE") == "1"


# Month creation is single-winner: two same-month arrivals racing the
# no-open-batch branch must produce ONE batch. A separate lock from
# _POOL_LOCK on purpose — creation runs vision (minutes on a cold cache)
# and must not stall arrival routing of every other mail; the re-check
# under this lock makes a lost race land in the batch the winner created.
_MATERIALIZE_LOCK = threading.Lock()

# A mail local-part as the travel alias uses it (lowercased). The alias
# matches the BASE local of a recipient, before any "+tag".
_TRAVEL_ALIAS_RE = re.compile(r"[a-z0-9._-]{1,64}")


def _is_plain_address(value) -> bool:
    """One bare e-mail address: no display name, no second address hiding
    behind a separator, no header-injection characters."""
    if not isinstance(value, str):
        return False
    addr = value.strip().lower()
    if addr.count("@") != 1 or any(c in addr for c in " \t,;<>\r\n"):
        return False
    local, _, domain = addr.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") \
        and not domain.endswith(".")


@dataclass(frozen=True)
class IntakeConfig:
    domain: str = DEFAULT_INTAKE_DOMAIN
    aliases: dict = field(default_factory=dict)  # local-part -> person name
    sender_daily_cap: int = DEFAULT_SENDER_DAILY_CAP
    global_daily_cap: int = DEFAULT_GLOBAL_DAILY_CAP
    # Item 122: what an unrecognised sender may spend in disk.
    unknown_max_message_bytes: int = DEFAULT_UNKNOWN_MAX_MESSAGE_BYTES
    unknown_daily_bytes: int = DEFAULT_UNKNOWN_DAILY_BYTES
    dismissed_purge_days: int = DEFAULT_DISMISSED_PURGE_DAYS
    auto_ack: bool = True
    alert_recipients: tuple[str, ...] = DEFAULT_ALERT_RECIPIENTS
    retention_years: int = DEFAULT_RETENTION_YEARS
    known_senders: tuple[str, ...] = ()   # outside addresses that are OURS
    # Item 38: the local-part that routes mail to the TRAVEL pool.
    # Configurable because the owner has not picked the name yet; ""
    # means unset, and with it unset every mail routes exactly as before
    # (the receipts@ behavior is regression-pinned on that).
    travel_alias: str = ""

    @classmethod
    def from_settings(cls, settings: dict | None) -> "IntakeConfig":
        """Settings key ``intake``: {domain, aliases: {...},
        sender_daily_cap, global_daily_cap, auto_ack, alert_recipients,
        retention_years, known_senders}. Env overrides the domain
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

        def _count(key: str, default: int) -> int:
            """Like _cap but 0 is a legal value meaning "off"."""
            try:
                v = int(raw.get(key, default))
                return v if v >= 0 else default
            except (TypeError, ValueError):
                return default

        # Alert recipients keep only internal-looking addresses; the Graph
        # layer re-asserts @brisken.com per send regardless.
        alerts = tuple(
            a.strip().lower()
            for a in (raw.get("alert_recipients") or DEFAULT_ALERT_RECIPIENTS)
            if isinstance(a, str) and "@" in a.strip()
        ) or DEFAULT_ALERT_RECIPIENTS

        # Malformed entries are dropped rather than raising: the PUT edge
        # (`normalize_intake_setting`) is where a bad list is refused, and
        # a settings blob edited by hand must never take the mailbox down.
        known = tuple(dict.fromkeys(
            a.strip().lower()
            for a in (raw.get("known_senders") or ())
            if _is_plain_address(a)
        ))[:MAX_KNOWN_SENDERS]

        # Same drop-don't-raise posture as known_senders: a hand-edited
        # blob must never take the mailbox down. A travel alias that
        # collides with a person alias or the canonical receipts local is
        # ignored (the PUT edge refuses it; this is the belt).
        travel = str(raw.get("travel_alias") or "").strip().lower()
        if not _TRAVEL_ALIAS_RE.fullmatch(travel) or travel == "receipts" \
                or travel in aliases:
            travel = ""

        return cls(
            domain=domain,
            aliases=aliases,
            sender_daily_cap=_cap("sender_daily_cap", DEFAULT_SENDER_DAILY_CAP),
            global_daily_cap=_cap("global_daily_cap", DEFAULT_GLOBAL_DAILY_CAP),
            unknown_max_message_bytes=_cap(
                "unknown_max_message_bytes", DEFAULT_UNKNOWN_MAX_MESSAGE_BYTES
            ),
            unknown_daily_bytes=_cap(
                "unknown_daily_bytes", DEFAULT_UNKNOWN_DAILY_BYTES
            ),
            dismissed_purge_days=_count(
                "dismissed_purge_days", DEFAULT_DISMISSED_PURGE_DAYS
            ),
            auto_ack=bool(raw.get("auto_ack", True)),
            alert_recipients=alerts,
            retention_years=_cap("retention_years", DEFAULT_RETENTION_YEARS),
            known_senders=known,
            travel_alias=travel,
        )


def normalize_intake_setting(raw) -> dict:
    """Validate the settings["intake"] payload at the PUT edge. Returns the
    cleaned dict; raises ValueError on a malformed shape."""
    if not isinstance(raw, dict):
        raise CodedValueError(
            "intake must be an object", code="invalid_body"
        )
    cleaned: dict = {}
    domain = raw.get("domain")
    if domain is not None:
        if not isinstance(domain, str) or "@" in domain or not domain.strip():
            raise CodedValueError(
                "intake.domain must be a bare domain name",
                code="intake_domain_invalid",
            )
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
            raise CodedValueError(
                "intake.aliases must map address local-parts to person names",
                code="intake_aliases_invalid",
            )
        cleaned["aliases"] = {
            k.strip().lower(): v.strip() for k, v in aliases.items()
        }
    for cap in ("sender_daily_cap", "global_daily_cap", "retention_years",
                "unknown_max_message_bytes", "unknown_daily_bytes"):
        if cap in raw:
            try:
                v = int(raw[cap])
            except (TypeError, ValueError):
                raise CodedValueError(
                    f"intake.{cap} must be a positive integer",
                    code="intake_number_invalid", field=cap,
                )
            if v <= 0:
                raise CodedValueError(
                    f"intake.{cap} must be a positive integer",
                    code="intake_number_invalid", field=cap,
                )
            cleaned[cap] = v
    # Item 122: days an archive stays after the operator dismissed it as
    # junk. 0 is legal and means "never delete", which is why it is not in
    # the positive-integer loop above.
    if "dismissed_purge_days" in raw:
        try:
            days = int(raw["dismissed_purge_days"])
        except (TypeError, ValueError):
            raise CodedValueError(
                "intake.dismissed_purge_days must be 0 (never) or a "
                "positive number of days",
                code="invalid_body", field="dismissed_purge_days",
            )
        if days < 0:
            raise CodedValueError(
                "intake.dismissed_purge_days must be 0 (never) or a "
                "positive number of days",
                code="invalid_body", field="dismissed_purge_days",
            )
        cleaned["dismissed_purge_days"] = days
    if "auto_ack" in raw:
        if not isinstance(raw["auto_ack"], bool):
            raise CodedValueError(
                "intake.auto_ack must be true or false",
                code="invalid_body", field="auto_ack",
            )
        cleaned["auto_ack"] = raw["auto_ack"]
    alerts = raw.get("alert_recipients")
    if alerts is not None:
        if not isinstance(alerts, list) or not all(
            isinstance(a, str) and a.strip().lower().endswith("@brisken.com")
            and a.strip().count("@") == 1
            for a in alerts
        ):
            raise CodedValueError(
                "intake.alert_recipients must be @brisken.com addresses",
                code="intake_alert_recipients_invalid",
            )
        cleaned["alert_recipients"] = [a.strip().lower() for a in alerts]
    known = raw.get("known_senders")
    if known is not None:
        if not isinstance(known, list) or not all(
            _is_plain_address(a) for a in known
        ):
            raise CodedValueError(
                "intake.known_senders must be a list of plain e-mail "
                "addresses",
                code="intake_known_senders_invalid",
            )
        deduped = list(dict.fromkeys(a.strip().lower() for a in known))
        if len(deduped) > MAX_KNOWN_SENDERS:
            raise CodedValueError(
                f"intake.known_senders holds at most {MAX_KNOWN_SENDERS} "
                "addresses",
                code="intake_known_senders_too_many",
                limit=MAX_KNOWN_SENDERS,
            )
        cleaned["known_senders"] = deduped
    # Item 38: the travel-pool local-part. "" stores as unset (the owner
    # has not picked the name yet; the feature activates when they do).
    # Collisions are refused HERE, against the aliases of THIS payload,
    # because the intake object is stored exactly as sent: "receipts"
    # would swallow the company intake wholesale, and a person alias
    # would stop routing that person's mail.
    if "travel_alias" in raw:
        travel = raw["travel_alias"]
        if not isinstance(travel, str):
            raise CodedValueError(
                "intake.travel_alias must be a string",
                code="invalid_body", field="travel_alias",
            )
        travel = travel.strip().lower()
        if travel and not _TRAVEL_ALIAS_RE.fullmatch(travel):
            raise CodedValueError(
                "intake.travel_alias must be a bare address local-part "
                "(letters, digits, . _ -)",
                code="intake_travel_alias_invalid",
            )
        if travel == "receipts":
            raise CodedValueError(
                "intake.travel_alias cannot be 'receipts' - that is the "
                "company intake address",
                code="intake_travel_alias_reserved",
            )
        if travel and travel in cleaned.get("aliases", {}):
            raise CodedValueError(
                f"intake.travel_alias {travel!r} collides with a person "
                "alias",
                code="intake_travel_alias_collision",
                alias=travel,
            )
        cleaned["travel_alias"] = travel
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
    # The BASE local of each recipient (the part before any "+tag"), in
    # the same order. `to_locals` carries the plus-TAG because that is
    # the person-alias signal (receipts+dirk@ -> "dirk"); the travel
    # split keys on the base instead, so travel+rome@ is travel and
    # receipts+travel@ stays the company intake's tag convention
    # (adversarial review 2026-09-06, finding 4).
    to_base_locals: list[str] = field(default_factory=list)


def _locals_from_addrs(
    addrs, domain: str, out: list[str],
    base_out: list[str] | None = None,
) -> None:
    for addr in addrs:
        addr = (addr or "").strip().lower()
        if addr.endswith("@" + domain):
            local = addr.split("@", 1)[0]
            base = local.split("+", 1)[0]
            if base_out is not None and base and base not in base_out:
                base_out.append(base)
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
    to_base_locals: list[str] = []
    # Envelope recipients first: our own listener IS the receiving MTA, so
    # they are authoritative and cover Bcc'd aliases the headers never show.
    _locals_from_addrs(envelope_rcpts or [], domain, to_locals, to_base_locals)
    # NOTE: 3.12's strict getaddresses (CVE-2023-27043 fix) answers the
    # WHOLE call with the [('','')] failure sentinel if ANY element is
    # unparseable — an empty string from an absent header poisons it.
    header_values = [str(msg.get(h, "")) for h in ("To", "Cc")]
    _locals_from_addrs(
        (a for _l, a in getaddresses([v for v in header_values if v.strip()])),
        domain, to_locals, to_base_locals,
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
        to_base_locals=to_base_locals,
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


def is_travel_mail(base_locals: list[str], cfg: IntakeConfig) -> bool:
    """Was this mail addressed to the travel alias? Address-only, per
    item 38 ruling 1: the split routes by the To-address the sender
    picked, never by content classification. With no alias configured
    (the owner has not chosen the name) nothing is ever travel.

    Matches the BASE local (before any "+tag"): travel+rome@ is travel
    mail, while receipts+travel@ is the company intake's person-tag
    convention and stays month mail. A mail addressed to BOTH intakes
    (To receipts@, Cc travel@) counts as travel: resting in the travel
    pool is recoverable with one click, auto-ingesting into a month
    against the sender's travel flag is the worse error."""
    return bool(cfg.travel_alias) and cfg.travel_alias in (base_locals or [])


def is_known_sender(from_addr: str, cfg: IntakeConfig) -> bool:
    """Is this submitter one of OUR people rather than a stranger?

    Two ways to be known, both operator-controlled: the address is inside
    the Brisken tenant, or it sits on ``intake.known_senders`` (Dirk mails
    receipts from a private mailbox as well as his work one). Deliberately
    NOT the To-alias: an alias is a routing claim anybody can address, so
    treating it as identity would let a stranger nominate who we believe
    they are.

    Two things hang off the answer. A known submitter gets the acceptance
    ack even at an outside address, and their body-only mail is rendered
    on arrival instead of waiting for a click. Both are things we do for
    someone a human listed on purpose and not for a stranger whose From
    header we cannot check. From IS forgeable, so this is a courtesy
    boundary, not a security one; what it bounds is a reply to a listed
    address and one vision call, both already capped.
    """
    addr = (from_addr or "").strip().lower()
    if not _is_plain_address(addr):
        return False
    if addr.endswith(graph_notify.RECIPIENT_SUFFIX):
        return True
    return addr in cfg.known_senders


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
        self._unknown_bytes = 0
        self._seeded_from: Path | None = None

    def _roll(self, data_root: Path) -> None:
        today = _now_iso()[:10]
        if self._day != today:
            self._day = today
            self._per_sender = {}
            self._global = 0
            self._unknown_bytes = 0
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
                # Rows written before item 122 carry neither field. A
                # missing `known_sender` reads as known (charges nothing):
                # over-charging the byte budget from archaeology would
                # refuse today's real receipts after a restart, which is
                # the failure this item exists to remove.
                if row.get("known_sender") is False:
                    self._unknown_bytes += max(0, int(row.get("n_bytes") or 0))

    def reserve(self, data_root: Path, sender: str, units: int,
                cfg: IntakeConfig, *, known: bool = False,
                n_bytes: int = 0) -> bool:
        """Reserve one message's spend. All-or-nothing under one lock, so
        a refused message consumes no budget at all.

        ``known`` is item 122: our own people (inside @brisken.com, or an
        address an operator listed) are not held to the per-sender file
        cap — a month-end backfill legitimately exceeds 40 files, and the
        cap was never a security boundary anyway since From is forgeable.
        The GLOBAL file cap still binds everyone; it is the real ceiling
        on a day's vision spend. A stranger additionally spends against a
        shared daily byte budget, which is what stops one afternoon of
        junk from filling the volume."""
        units = max(1, units)
        n_bytes = max(0, n_bytes)
        with self._lock:
            self._roll(data_root)
            if not known and (
                self._per_sender.get(sender, 0) + units > cfg.sender_daily_cap
            ):
                return False
            if self._global + units > cfg.global_daily_cap:
                return False
            if not known and (
                self._unknown_bytes + n_bytes > cfg.unknown_daily_bytes
            ):
                return False
            self._per_sender[sender] = self._per_sender.get(sender, 0) + units
            self._global += units
            if not known:
                self._unknown_bytes += n_bytes
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


def free_disk_floor(total_bytes: int) -> int:
    """How much free space the mailbox insists on, for a volume of this
    size (item 122).

    A share of the disk, floored at 200 MB so a bigger volume never
    lowers the guard, and capped at half the disk so a small one cannot
    refuse mail from empty. The old flat 500 MiB was 51% of the 1 GB
    volume, which is why refusals were due to start in early 2027 with no
    warning; the same code now leaves 800 MB usable on 1 GB and 4.75 GB
    on 5 GB, and neither number is written down anywhere."""
    total = max(0, int(total_bytes))
    share = int(total * MIN_FREE_DISK_FRACTION)
    return min(max(share, MIN_FREE_DISK_FLOOR_BYTES), total // 2)


def disk_snapshot(data_root: Path) -> dict:
    """Free space on the volume the archive lives on, as /healthz reports
    it (item 122). ``available`` is False when the volume cannot be read,
    so a monitor can tell "cannot say" from "nothing free"."""
    try:
        usage = shutil.disk_usage(str(data_root))
    except OSError:
        return {"available": False}
    floor = free_disk_floor(usage.total)
    pct = round(usage.free * 100.0 / usage.total, 1) if usage.total else 0.0
    return {
        "available": True,
        "total_bytes": usage.total,
        "free_bytes": usage.free,
        "used_bytes": usage.used,
        "free_pct": pct,
        "floor_bytes": floor,
        # The question a monitor actually asks: is the mailbox about to
        # start turning receipts away?
        "intake_refusing": usage.free < floor,
    }


def disk_low(data_root: Path) -> bool:
    snap = disk_snapshot(data_root)
    # Unreadable volume: never refuse mail on a failed measurement (the
    # pre-item-122 posture, kept deliberately).
    return bool(snap.get("intake_refusing"))


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


_REFUSAL_LOCK = threading.Lock()


def _refusal_log_path(data_root: Path) -> Path:
    return inbound_root(data_root) / "refusals.jsonl"


def record_refusal(
    data_root: Path, *, stage: str, reason: str,
    sender: str = "", recipient: str = "", peer: str = "",
) -> None:
    """Write down that mail was turned away.

    Refusals are answered in-protocol (the sender's own MTA generates the
    bounce, we send nothing), which is correct and also completely silent
    on our side: until this ledger, "is anything being refused?" had no
    answer anywhere in the system, and that is exactly the question an
    owner asked on 2026-08-24 about receipts that never appeared.

    Never raises: the caller is mid-SMTP and still has to answer its error
    line. A refusal we could not write down must not become a refusal we
    could not make.
    """
    row = {
        "at": _now_iso(), "stage": stage, "reason": str(reason)[:200],
        "from": str(sender or "")[:320], "to": str(recipient or "")[:320],
        "peer": str(peer or "")[:64],
    }
    try:
        with _REFUSAL_LOCK:
            path = _refusal_log_path(data_root)
            path.parent.mkdir(parents=True, exist_ok=True)
            # Trim BEFORE appending, and trim hard: after a rewrite the
            # file sits well under the cap, so a sustained flood rewrites
            # once every few hundred rows rather than on every refusal.
            try:
                if path.exists() and path.stat().st_size > REFUSAL_LOG_MAX_BYTES:
                    kept = path.read_text(
                        encoding="utf-8"
                    ).splitlines()[-REFUSAL_KEEP_ROWS:]
                    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
            except OSError:
                pass
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - a ledger write never blocks a refusal
        log.warning("could not record intake refusal (%s)", stage)


def _refusal_rows(data_root: Path) -> list[dict]:
    """Every retained refusal row, oldest->newest. One read of the file."""
    path = _refusal_log_path(data_root)
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _window_rows(rows: list[dict], days: int) -> list[dict]:
    # Same timespec on both sides, or a row stamped in the cutoff SECOND
    # compares against a microsecond tail and falls out of its own window.
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=max(1, days))
    ).isoformat(timespec="seconds")
    return [r for r in rows if str(r.get("at", "")) >= cutoff]


def _within_days(rows: list[dict], days: int) -> int:
    return len(_window_rows(rows, days))


def is_probe_refusal(row: dict) -> bool:
    """A relay probe: rcpt-stage, recipient outside the intake domain.

    The reason line IS the encoding of that check — `rcpt_decision` answers
    "550 5.7.1 relay not permitted" exactly when the recipient is not ours —
    so the split cannot drift from the refusal it describes. The other
    rcpt-stage refusal ("too many recipients") is real mail addressed to us
    and is deliberately NEITHER bucket: it stays in `n_refused` alone.
    """
    return (
        str(row.get("stage", "")) == "rcpt"
        and "relay not permitted" in str(row.get("reason", ""))
    )


def _annotate_refusal_rows(rows: list[dict]) -> None:
    """Stamp ``probe`` + ``kind_label`` on refusal rows (parallel fields).

    The label is prose per api-contract rule 5, so an SPA that has never
    heard of the split still renders correct text instead of guessing from
    the SMTP reason line.
    """
    for row in rows:
        probe = is_probe_refusal(row)
        row["probe"] = probe
        if probe:
            row["kind_label"] = "Relay probe, not our mail"
        elif str(row.get("stage", "")) == "data":
            row["kind_label"] = "A real submission, turned away"
        else:
            row["kind_label"] = "Refused at the envelope"


def read_refusals(data_root: Path, limit: int = 20) -> list[dict]:
    """Refusal rows, oldest->newest, newest `limit` retained."""
    return _refusal_rows(data_root)[-max(1, limit):]


def count_refusals(data_root: Path, days: int = REFUSAL_WINDOW_DAYS) -> int:
    """How many refusals the ledger still holds from the last `days`.

    A count over a WINDOW rather than over the file: the ledger is trimmed
    at a size cap, so "every row we kept" would answer a question about
    our own retention instead of about this week's mail.
    """
    return _within_days(_refusal_rows(data_root), days)


def refusal_view(
    data_root: Path, limit: int = 20, days: int = REFUSAL_WINDOW_DAYS,
) -> tuple[dict, list[dict]]:
    """(window counts, newest annotated rows) from ONE read of the ledger.

    The intake log is polled; reading a capped-but-not-tiny file twice per
    poll to answer two questions about the same rows is waste.

    Counts (item 42): ``total`` keeps `n_refused`'s exact meaning; beside
    it, ``ours`` counts data-stage refusals (real submissions we accepted
    the envelope for and then turned away) and ``probes`` counts rcpt-stage
    relay probes. The 2026-09-06 audit measured all 55 window rows as
    `*@flyio.net` relay probes — with a permanent probe floor, a REAL
    refused submission is invisible in the single number.
    """
    rows = _refusal_rows(data_root)
    window = _window_rows(rows, days)
    counts = {
        "total": len(window),
        "ours": sum(1 for r in window if str(r.get("stage", "")) == "data"),
        "probes": sum(1 for r in window if is_probe_refusal(r)),
    }
    newest = rows[-max(1, limit):]
    _annotate_refusal_rows(newest)
    return counts, newest


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
            # Item 106: why this mail's other files created no expense.
            if meta.get("not_added"):
                row["not_added"] = meta["not_added"]
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
            # Travel stamp (item 38): parallel field, absent on month
            # mail. The trip suggestion is computed at read time in
            # `annotate_travel_pool` (trips open and close; a suggestion
            # stamped at arrival would go stale).
            if meta.get("pool_kind"):
                row["pool_kind"] = meta["pool_kind"]
            # Duplicate stamps (2026-08-25): which earlier mail already
            # carried this content, so the row can point at it instead of
            # just refusing to explain itself.
            if meta.get("duplicate_of"):
                row["duplicate_of"] = meta["duplicate_of"]
            if meta.get("duplicate_of_subject"):
                row["duplicate_of_subject"] = meta["duplicate_of_subject"]
            if meta.get("duplicate_of_at"):
                row["duplicate_of_at"] = meta["duplicate_of_at"]
            # Item 39: this mail created its month itself; the label reads
            # "Filed into July 2026" instead of "Added".
            if meta.get("materialized"):
                row["materialized"] = True
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
        # The base locals too, so a router that died BEFORE the routing
        # CAS leaves enough behind for replay to re-derive the travel
        # answer (finding 3): the stamp is only written at routing.
        "to_base_locals": parsed.to_base_locals,
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


_DEDUPE_LOCK = threading.Lock()

_WHITESPACE = re.compile(r"\s+")


def _body_fingerprint(text: str) -> str:
    """Fingerprint for a mail whose receipt IS its body.

    Whitespace-collapsed and casefolded, because a forward re-wraps lines
    and mail clients disagree about capitalisation of headers they inject.
    Nothing cleverer: a near-miss here MISSES, and a missed duplicate is
    the old behavior, while a false match would hide a real receipt.
    """
    return "body:" + hashlib.sha1(
        _WHITESPACE.sub(" ", (text or "")).strip().casefold().encode("utf-8")
    ).hexdigest()[:16]


def content_fingerprints(attachments, body_text: str = "") -> list[str]:
    """What this mail's receipt payload IS, as content, in file order.

    Attachment digests use the SAME `sha1(bytes)[:16]` shape as the
    receipt-pool dedupe in `service._add_receipts_locked`, deliberately:
    the two layers must agree about what "the same file" means, or a mail
    could be called a duplicate here and still add a row there.

    A body-only mail has no attachment to hash at arrival (its PDF does
    not exist until something renders it), so its body stands in.
    """
    digests = [
        hashlib.sha1(data).hexdigest()[:16] for _name, data in (attachments or [])
    ]
    if digests:
        return digests
    return [_body_fingerprint(body_text)] if (body_text or "").strip() else []


def _untrusted_flags(arch: Path | None) -> list[dict]:
    """Agent-directed text this mail carried, as stamped by route_archived.
    Data for a human (rule_untrusted_inbound): it raises a review flag and
    suppresses the auto-ack, and decides nothing else."""
    if arch is None:
        return []
    flags = _read_meta(arch).get("untrusted_instructions") or []
    return [dict(f) for f in flags if isinstance(f, dict)]


def _provenance_entry(person: dict, received_at: str, arch: Path | None) -> dict:
    """One per-file provenance record. Carries the mail's untrusted-text
    flags, so a receipt created from an injected mail shows the flag on its
    grid row exactly where `submitted_by` already shows."""
    entry = {**person, "received_at": received_at}
    meta = _read_meta(arch)  # {} for arch is None (item 106 / 125 both read it)
    if arch is not None:
        # Item 106: which mail stored this file, so a replay of the same
        # mail recognises its own receipt instead of calling it a copy.
        entry["archive"] = arch.name
    # Item 125: whether this mail's SMTP session was encrypted, carried from
    # the archive meta (stamped in archive_incoming) onto the receipt, so
    # the operator sees on the grid who still delivers in the clear. Present
    # ONLY when the intake recorded it (every real SMTP arrival does); a
    # non-SMTP caller and a pre-2026-09-18 archive leave the key absent, so
    # "not recorded" reads apart from "delivered in the clear" (False).
    if "transport_tls" in meta:
        entry["transport_tls"] = bool(meta.get("transport_tls"))
    flags = _untrusted_flags(arch)
    if flags:
        entry["untrusted_instructions"] = flags
    # Item 155: the sender's own prose above the forward - the filing
    # instruction that exists nowhere in the attached PDF. Parallel and
    # ABSENT when the mail carried none (56 of the 86 readable live
    # bodies), never "". DISPLAY ONLY (rule_untrusted_inbound): it is
    # shown to the reviewer and routes nothing.
    #
    # Recorded for a RENDERED body-only mail too, deliberately. The
    # caution against double-recording guards against a second copy of
    # the invoice, and the boundary rule cannot produce one: it keeps
    # only what sits ABOVE the forward, and the invoice is always below.
    # What it keeps on those mails is the 1-3 lines of instruction, which
    # on a body-only mail are otherwise buried inside a rendered image the
    # reviewer has to open - 13 of the 30 live notes arrive that way.
    note = _archive_operator_note(arch)
    if note:
        entry["operator_note"] = note
    return entry


def _archive_operator_note(arch: Path | None) -> str:
    """The operator's note above the forward in this mail's body, or ""."""
    if arch is None:
        return ""
    from .body_render import operator_note

    try:
        return operator_note(_archive_body_text(arch))
    except Exception:  # noqa: BLE001 - a display note is never worth a crash
        return ""


def _archive_body_text(arch: Path) -> str:
    """Readable body of the custody message, or "" when unreadable."""
    from .body_render import extract_body_text

    eml = arch / "message.eml"
    if not eml.is_file():
        return ""
    try:
        return extract_body_text(eml.read_bytes())
    except Exception:  # noqa: BLE001 - a fingerprint is never worth a crash
        return ""


def _fingerprint_owners(data_root: Path, exclude: str = "") -> dict[str, dict]:
    """`fingerprint -> the archive that already holds that content`.

    Built by walking the archives rather than kept as an index file, for
    the reason the working notes give about the log: the volume is the
    system of record, and a derived index can disagree with it. At this
    mailbox's volume that is a few dozen small reads on the worker thread
    that already runs after the SMTP 250, so nothing a sender waits on.
    If the archive count ever reaches the thousands, add a cache HERE and
    rebuild it from the archives; do not move the truth.

    Only statuses in `OWNS_CONTENT` claim anything. Earliest archive wins,
    so the original keeps ownership when a copy is later dismissed.
    """
    owners: dict[str, dict] = {}
    root = inbound_root(data_root)
    if not root.is_dir():
        return owners
    for arch in sorted(root.iterdir()):
        if not arch.is_dir() or arch.name == exclude:
            continue
        if not _ARCHIVE_NAME_RE.fullmatch(arch.name):
            continue
        meta = _read_meta(arch)
        if str(meta.get("status") or "") not in OWNS_CONTENT:
            continue
        for fp in meta.get("fingerprints") or []:
            owners.setdefault(str(fp), {
                "archive": arch.name,
                "at": str(meta.get("at") or ""),
                "subject": str(meta.get("subject") or ""),
            })
    return owners


def classify_duplicate(
    data_root: Path, arch: Path, fingerprints: list[str],
) -> dict | None:
    """The original this mail duplicates, or None to carry on.

    A mail counts as a duplicate only when EVERY piece of content it
    carries is already held. A two-attachment mail where one file is new
    is not a duplicate: it carries a receipt the tool does not have, and
    the pool's own content dedupe drops the repeat at add time.

    Known edge, deliberately not swept: a copy parked against an original
    that LATER fails to ingest points at a mail that never landed. The
    original shows as "Needs a retry" and the copy names it in its label,
    so the pair is legible on one screen, and retrying the original or
    clearing the copy with `unmark_duplicate` resolves it either way. A
    background re-evaluation would be the alternative, and it would have
    to re-open settled rows to earn its keep.
    """
    if not fingerprints:
        return None
    owners = _fingerprint_owners(data_root, exclude=arch.name)
    hits = [owners.get(fp) for fp in fingerprints]
    if not all(hits):
        return None
    first = min(hits, key=lambda h: h["at"] or "")
    return dict(first)


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
                    # Item 39 rollback: the month this mail materialized is
                    # gone. Without clearing the stamp, a later NORMAL claim
                    # into an operator-created month would still read
                    # "Filed into ..." about a mail that did not file itself.
                    "materialized": False,
                    # And no job_id from the previous life: the boot sweep
                    # reads a done job as "this transient episode finished"
                    # (reconcile_interrupted), so a stale one would strand a
                    # later mid-claim death in `claiming` forever.
                    "job_id": "",
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
    known_sender: bool = True, transport_tls: bool | None = None,
) -> Path:
    """Custody step: archive + acceptance log row, called INLINE in the
    SMTP DATA handler before the 250 goes out. Raises on failure (the
    caller answers 451 so the sender's MTA retries).

    The row records the message's SIZE and whether we recognised the
    sender (item 122), which is what lets the day budget re-seed the
    unknown-sender byte spend after a restart instead of forgiving it.

    `transport_tls` (item 125) is whether the SMTP session had completed
    STARTTLS before DATA; the listener always knows and always passes a
    bool. It lands on the archive meta and the log row, and from the meta
    onto every receipt the mail produces (`_provenance_entry`). Left None
    by a non-SMTP caller, the key is ABSENT (never null), so a reader
    tells "not recorded" from "delivered in the clear"; archives written
    before 2026-09-18 read the same way."""
    extra: dict = {"peer": peer}
    if transport_tls is not None:
        extra["transport_tls"] = bool(transport_tls)
    arch = archive_message(
        data_root, raw, parsed, STATUS_RECEIVED, extra=extra
    )
    row = {
        "at": _now_iso(),
        "from": parsed.from_addr,
        "subject": parsed.subject,
        "n_files": len(parsed.attachments),
        "n_bytes": len(raw or b""),
        "known_sender": bool(known_sender),
        "status": STATUS_RECEIVED,
        "archive": arch.name,
    }
    if transport_tls is not None:
        row["transport_tls"] = bool(transport_tls)
    _append_log(data_root, row)
    return arch


# ---------------------------------------------------------- notifications --
# Acks, held alerts and held-sender notices ride graph_notify (internal-only
# plus operator-listed senders, hard-guarded). All are best-effort side
# effects: a failed notification never changes an archive's status or
# breaks ingest, and each is idempotent per archive via its own meta stamp
# (ack_at / alert_at / held_notice_at).

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

    Since submission opened to any sender (2026-08-23), that address can
    be external and forged, so the ack cannot simply go wherever the mail
    came from: replying to unverified strangers as Brisken is backscatter,
    not a confirmation. The rule (2026-08-24) is that an outside address
    is acked only when an operator has LISTED it in
    ``intake.known_senders`` — Dirk mails receipts from his private
    mailbox too, and until that list existed his private sends and a lost
    mail looked identical from his chair. Everyone else still gets
    nothing, and `graph_notify.send_mail` re-asserts the whole rule per
    call."""
    try:
        with RunStore(db_path) as store:
            cfg = IntakeConfig.from_settings(store.get_settings())
            meta = _read_meta(arch)
            batch_label = ""
            batch_is_trip = False
            if meta.get("batch_id"):
                run = store.get_run(str(meta["batch_id"]))
                if run is not None:
                    batch_label = (run.label or "").strip()
                    batch_is_trip = is_trip_batch(run)
        if not cfg.auto_ack or not graph_notify.enabled():
            return
        # Item 106: a mail acked earlier (pooled: "will join that month
        # automatically") that then added nothing gets ONE correction.
        corrective = (
            mail_added_nothing(meta) and not meta.get("no_expense_ack_at")
        )
        if (meta.get("ack_at") and not corrective) or _inbound_is_auto_generated(arch):
            return
        if _untrusted_flags(arch):
            # The mail carried text aimed at an assistant, and the ack echoes
            # its subject back into the tenant. An injected mail never
            # triggers an outbound message: its receipts are flagged for a
            # human instead (rule_untrusted_inbound).
            _update_meta(arch, {"ack_suppressed": "untrusted_instructions"})
            return
        recipient = str(meta.get("from", "")).strip().lower()
        n = int(meta.get("n_files") or 0)
        subject = str(meta.get("subject") or "").strip()
        month = str(meta.get("receipt_month") or "")
        if meta.get("status") == STATUS_DUPLICATE:
            # Say plainly that nothing was added, and that this is fine.
            # A sender who forwards the same receipt twice needs to know
            # the tool is not now holding it twice.
            landed = (
                " was already in the Brisken expense tool, so nothing was "
                "added a second time. No action needed."
            )
        elif meta.get("status") == STATUS_POOLED:
            verb = "are" if n > 1 else "is"
            if str(meta.get("pool_kind") or "") == "travel":
                # Travel mail waits for a human to put it on its trip, so
                # the ack must not promise the month pool's automatic
                # join — that would be a claim about behavior that
                # deliberately does not happen (deny-by-default).
                landed = (
                    f" {verb} stored as travel receipts in the Brisken "
                    "expense tool, and will be added to the right trip "
                    "with the next review."
                )
            else:
                landed = (
                    f" {verb} stored for {_month_human(month)} in the "
                    "Brisken expense tool, and will join that month's "
                    "expense run automatically when the month is opened."
                )
        elif meta.get("materialized") and month:
            # Item 39: the mail opened its month itself, so the ack states
            # a finished fact — "filed into", never "waiting for".
            verb = "were" if n > 1 else "was"
            landed = (
                f" {verb} filed into {_month_human(month)} in the Brisken "
                "expense tool (the month was opened automatically)."
            )
        elif batch_label:
            landed = (
                f' landed in the "{batch_label}" '
                + ("trip" if batch_is_trip else "expense month")
                + " in the Brisken expense tool."
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
        # Travel mail is reviewed per trip and was sent to the travel
        # address; promising "the monthly run" and signing as receipts@
        # would both be wrong about it (finding 7).
        is_travel = (
            str(meta.get("pool_kind") or "") == "travel" or batch_is_trip
        )
        review_note = (
            " Nothing else to do; Criss reviews them with the trip's "
            "expenses." if is_travel else
            " Nothing else to do; Criss reviews them with the monthly "
            "run."
        )
        sender_local = (
            cfg.travel_alias if is_travel and cfg.travel_alias
            else "receipts"
        )
        body = (
            lead
            + (f' "{subject}"' if subject else "")
            + landed
            + review_note
            + "\n\nAutomated confirmation from "
            f"{sender_local}@{cfg.domain}."
        )
        ack_subject = "Receipt received" + (f": {subject}" if subject else "")
        if mail_added_nothing(meta):
            # Item 106: a forward that created no expense (every file set
            # aside, already on file, or unreadable) must not be told it
            # "landed". Say what happened per file and what would help.
            ack_subject = "No expense added" + (f": {subject}" if subject else "")
            body = _no_expense_ack_body(
                meta, subject=subject, month=month, batch_label=batch_label,
                batch_is_trip=batch_is_trip,
                signature=f"{sender_local}@{cfg.domain}",
            )
        if graph_notify.send_mail(
            recipient, ack_subject,
            body, allow_external=cfg.known_senders,
        ):
            stamp = {"ack_at": _now_iso()}
            if mail_added_nothing(meta):
                stamp["no_expense_ack_at"] = stamp["ack_at"]
            _update_meta(arch, stamp)
    except Exception as exc:  # noqa: BLE001 - notifications never break ingest
        log.warning("ack skipped for %s: %s", arch.name, exc)


def _maybe_alert(db_path: Path, arch: Path, status: str) -> None:
    """Operator alert the first time an archive lands in a held status.
    Without this, held mail is only visible when someone opens the app.

    The same moment also tells the SENDER (item 121, owner ruling
    2026-09-17): until then a held mail left the person who sent it with
    no signal at all. Two separate facts with separate stamps (``alert_at``
    and ``held_notice_at``), each best-effort on its own, so a failed
    operator send never suppresses the sender notice, or the reverse."""
    _alert_operator(db_path, arch, status)
    _maybe_notify_held_sender(db_path, arch, status)


def _alert_operator(db_path: Path, arch: Path, status: str) -> None:
    """The operator half of `_maybe_alert`: recipients, subject and body
    exactly as they were before the sender notice existed."""
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


# What a held mail's sender reads, per held status: (why it is not filed and
# what happens next, whether "the team has been told" belongs beside it).
# Every sentence states only what the code does next. Nothing retries a held
# mail on its own: held_failed waits for an operator's "Retry held emails",
# and the other holds are resolved by a click or by the sender re-sending.
_HELD_NOTICE_TEXT: dict[str, tuple[str, bool]] = {
    HELD_FAILED: (
        " reached the Brisken expense tool, but something went wrong on our"
        " side while filing it, so it has not been filed yet. The email is"
        " saved in full and can be retried from there, so there is no need"
        " to send it again.",
        True,
    ),
    HELD_NO_VALID_FILES: (
        " reached the Brisken expense tool, but nothing in it was a file the"
        " tool can read as a receipt, so nothing was filed. Sending the"
        " receipt again as a PDF or a photo (JPG, PNG or WEBP) attachment"
        " lets the tool pick it up.",
        False,
    ),
    HELD_BODY_ONLY: (
        " reached the Brisken expense tool without a receipt file attached,"
        " and its text could not be read as a receipt automatically, so it"
        " has not been filed yet. The email is saved. If you have the"
        " receipt as a PDF or a photo, sending it again as an attachment is"
        " the surest way for the tool to pick it up.",
        True,
    ),
}
_HELD_NOTICE_FALLBACK = (
    " reached the Brisken expense tool but has not been filed yet. The email"
    " is saved.",
    True,
)


def _maybe_notify_held_sender(db_path: Path, arch: Path, status: str) -> None:
    """Tell the address a held mail came from that it was not filed, once.

    The guards are exactly `_maybe_ack`'s, because the recipient is the same
    untrusted From header (rule_untrusted_inbound: inbound mail never decides
    who we send to on its own). Off with ``intake.auto_ack``; never for
    auto-generated inbound mail; never for mail that carried agent-directed
    text (stamped, like the ack); and `graph_notify.send_mail` only lets the
    address through when it is inside @brisken.com or an operator listed it
    in ``intake.known_senders``. A stranger gets nothing.

    Idempotent per archive via ``held_notice_at``, independent of the
    operator's ``alert_at``. The text carries no archive name, no error
    string and nothing the operator alert carries beyond the sender's own
    subject line."""
    try:
        with RunStore(db_path) as store:
            cfg = IntakeConfig.from_settings(store.get_settings())
        if not cfg.auto_ack or not graph_notify.enabled():
            return
        meta = _read_meta(arch)
        if meta.get("held_notice_at") or _inbound_is_auto_generated(arch):
            return
        if _untrusted_flags(arch):
            # Same reason the ack holds back: the notice echoes the subject,
            # and an injected mail never triggers an outbound message.
            _update_meta(
                arch, {"held_notice_suppressed": "untrusted_instructions"}
            )
            return
        recipient = str(meta.get("from", "")).strip().lower()
        subject = str(meta.get("subject") or "").strip()
        reason, mention_team = _HELD_NOTICE_TEXT.get(
            status, _HELD_NOTICE_FALLBACK
        )
        # "Told" only when the operator alert really went out; the two sends
        # are independent, so the notice must not claim the other one.
        told = (
            " The team running the tool has been told."
            if mention_team and meta.get("alert_at") else ""
        )
        sender_local = (
            cfg.travel_alias
            if str(meta.get("pool_kind") or "") == "travel" and cfg.travel_alias
            else "receipts"
        )
        body = (
            "Your email"
            + (f' "{subject}"' if subject else "")
            + reason
            + told
            + "\n\nAutomated notice from "
            f"{sender_local}@{cfg.domain}."
        )
        if graph_notify.send_mail(
            recipient,
            "Receipt not filed yet" + (f": {subject}" if subject else ""),
            body, allow_external=cfg.known_senders,
        ):
            _update_meta(arch, {"held_notice_at": _now_iso()})
    except Exception as exc:  # noqa: BLE001 - notifications never break ingest
        log.warning("held notice skipped for %s: %s", arch.name, exc)


# ---------------------------------------------------------------- routing --

def open_batch(store: RunStore):
    """Newest expense batch without a statement attached, else None.

    LEGACY selector: month routing (2026-08-24) replaced it for mail, but
    it still answers "where would work land now" for the delete-month
    response and remains the target of the item-19 re-ingest path."""
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if is_trip_batch(run):
            # A trip is not a month: legacy re-ingest and the
            # delete-month "next open" answer both mean company months.
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
    reconciling = None
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if is_trip_batch(run):
            # Item 38: month routing NEVER lands mail in a trip, even
            # when the trip's name happens to parse as a month. Travel
            # mail joins a trip only by an operator's click.
            continue
        if month_from_label(run.label) != ym:
            continue
        if not has_statement(run):
            return run
        # 2b-2 lifted the statement refusal, so a month that is already
        # reconciling DOES claim its pooled mail; it just loses a
        # same-month tie to a statement-less batch, which is the
        # preference `month_batch_states` reports.
        if reconciling is None:
            reconciling = run
    return reconciling


def month_batch_states(store: RunStore) -> dict[tuple[int, int], str]:
    """month -> "open" | "closed" over the month-labelled expense batches
    (closed = statement attached). An open batch wins a same-month tie."""
    out: dict[tuple[int, int], str] = {}
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if is_trip_batch(run):
            continue
        ym = month_from_label(run.label)
        if ym is None:
            continue
        state = "reconciling" if has_statement(run) else "open"
        if out.get(ym) != "open":
            out[ym] = state
    return out


def count_archives(rows: list[dict], match) -> int:
    """How many distinct MAILS among ``rows`` match.

    The intake log holds more than one row per archive by design: one
    written at acceptance, another when a replay or a claim ingests it
    later. Counting rows therefore double-counts every mail that has been
    through a claim, which is exactly the mail a delete returns to the
    pool. The live drill on 2026-08-24 read "2 waiting" for one waiting
    receipt. Count the archive, not the row. A row with no archive name
    cannot be deduped and counts on its own."""
    seen: set[str] = set()
    anonymous = 0
    for row in rows:
        if not match(row):
            continue
        name = str(row.get("archive") or "")
        if name:
            seen.add(name)
        else:
            anonymous += 1
    return len(seen) + anonymous


def annotate_pool_state(store: RunStore, rows: list[dict]) -> int:
    """Stamp ``pool_month_state`` ("no_batch" | "open" | "closed") on the
    pooled rows of a read_log listing; returns how many distinct mails are
    waiting. "open" is transient — an open month claims its pool on the
    next trigger.

    Travel rows (``pool_kind: "travel"``) get NO month state: they are
    not waiting on a month, and a state that says "a claim is imminent"
    would be a false promise about mail the month pool deliberately
    skips. The returned count still includes them — ``n_pooled`` answers
    "how many mails are resting", whichever pool they rest in."""
    states = month_batch_states(store)
    for row in rows:
        if str(row.get("status", "")) != STATUS_POOLED:
            continue
        if str(row.get("pool_kind") or "") == "travel":
            continue
        ym = _ym(str(row.get("pool_month") or ""))
        row["pool_month_state"] = (
            states.get(ym, "no_batch") if ym else "no_batch"
        )
    return count_archives(
        rows, lambda r: str(r.get("status", "")) == STATUS_POOLED
    )


def annotate_travel_pool(
    db_path: Path, data_root: Path, rows: list[dict],
) -> int:
    """Stamp ``trip_suggestion`` on travel-pooled rows and return how
    many distinct travel mails are resting.

    The suggestion fires only when the mail's receipt dates fall inside
    EXACTLY ONE trip's range (item 38 design call): zero covering trips
    is an honest blank, two is ambiguity that must surface as absence,
    never as a guess. Joining stays a click either way. Computed at read
    time against the live trips list, so opening or deleting a trip
    moves the suggestion without touching the archive."""
    from .service import covering_trips

    travel_rows = [
        r for r in rows
        if str(r.get("status", "")) == STATUS_POOLED
        and str(r.get("pool_kind") or "") == "travel"
    ]
    if travel_rows:
        with RunStore(db_path) as store:
            trips = store.list_trips()
        for row in travel_rows:
            arch = _archive_dir(data_root, str(row.get("archive") or ""))
            dates = (
                _read_meta(arch).get("receipt_dates") or []
                if arch is not None else []
            )
            covering = covering_trips(trips, dates)
            if len(covering) == 1:
                trip = covering[0]
                row["trip_suggestion"] = {
                    "trip_id": trip.trip_id,
                    "name": trip.name,
                    "start": trip.start_date,
                    "end": trip.end_date,
                }
    return count_archives(
        rows,
        lambda r: str(r.get("status", "")) == STATUS_POOLED
        and str(r.get("pool_kind") or "") == "travel",
    )


def annotate_status_view(rows: list[dict]) -> None:
    """Stamp ``status_kind`` + ``status_label`` on every row.

    Call LAST, after `annotate_pool_state` and after the endpoint has
    resolved batch labels: the pooled label names its month and its
    waiting reason, and a row whose month was deleted says so.

    Both fields are PARALLEL (api-contract rule 1). Nothing existing
    changes, so a stale SPA renders exactly what it rendered before; a
    current one renders text it does not have to know the enum for. The
    label is English prose, like `issues` / `upload_issues`, and
    `status_kind` is the stable code an SPA localizes from.
    """
    for row in rows:
        status = str(row.get("status", ""))
        kind, label = _STATUS_VIEW.get(status, (KIND_UNKNOWN, status or "?"))
        if status == STATUS_POOLED and str(
            row.get("pool_kind") or ""
        ) == "travel":
            # Travel rows wait on a HUMAN's click, not on a month opening;
            # the label must never borrow the month pool's promise. With
            # exactly one covering trip the suggestion is named — as a
            # reading, not a decision.
            suggestion = row.get("trip_suggestion")
            if isinstance(suggestion, dict) and suggestion.get("name"):
                label = f'Travel; reads as "{suggestion["name"]}"'
            else:
                label = "Travel, waiting for its trip"
        elif status == STATUS_POOLED:
            month = _month_human(str(row.get("pool_month") or ""))
            state = str(row.get("pool_month_state") or "no_batch")
            if not row.get("pool_month"):
                label = "Waiting for its month"
            elif state == "open":
                label = f"Joining {month}"
            elif state == "reconciling":
                # 2b-2: a month with a statement stays open and claims, so
                # this is a normal wait, not the dead end "closed" was. The
                # label says the month is further along, because a reviewer
                # who already reconciled it should know a late receipt is
                # about to re-open the numbers.
                label = f"Joining {month}, which is already reconciling"
            elif state == "closed":
                # No longer produced; kept so a row written by an older
                # build still reads correctly.
                label = f"{month} is already reconciled"
                kind = KIND_HELD
            else:
                label = f"Waiting for {month}"
        elif status == STATUS_DUPLICATE:
            subject = str(row.get("duplicate_of_subject") or "").strip()
            label = (
                f'Already have this, from "{subject}"' if subject
                else "Already have this"
            )
        elif mail_added_nothing(row):
            # Item 106: finished, but no expense came of it. Same status
            # and kind (the held count keys on status; a sixth kind value
            # is the enum growth this view exists to avoid), honest label.
            label = no_expense_label(row.get("not_added"))
        elif (
            row.get("materialized")
            and status in (STATUS_INGESTED, STATUS_REPLAYED)
            # A deleted month outranks the origin story: without this a
            # materialized mail stranded by a delete would read done /
            # "Filed into ..." and hide lost receipts behind a finished
            # claim (the batch_deleted downgrade below must win).
            and not row.get("batch_deleted")
        ):
            # Item 39: this mail opened its month itself. Composed like
            # the pooled label (no new STATUS_* constant, per rule 5 the
            # existing kind/label pair carries the new meaning).
            month = _month_human(str(row.get("pool_month") or ""))
            if month:
                label = f"Filed into {month}"
        elif (
            row.get("batch_deleted")
            and kind == KIND_DONE
            # A DISMISSED mail is terminal: an operator judged it junk, and
            # that decision outranks where it used to live. Saying "the
            # month it was added to was deleted" about it puts a task back
            # on a row nobody owes anything for (live, 2026-08-24: two
            # dismissed archives read as held with the Held badge at 0).
            and str(row.get("status", "")) != STATUS_DISMISSED
        ):
            kind, label = KIND_HELD, "The month it was added to was deleted"
        row["status_kind"] = kind
        row["status_label"] = label


# ------------------------------------------- a mail that added nothing --
# Item 106 (2026-09-17 voids audit). A forward whose every file was set
# aside (a statement page, a bill notice rendered from the email text), was
# already on file, or could not be read used to finish as "ingested" with
# `documents: []`, read "Added" on the intake page, and tell its sender the
# files "landed in the July 2026 expense month". Live: Dirk's two AWS
# "billing statement available" forwards and Criss's AT&T bill notice and
# card summary, none of which put a receipt anywhere.

_SET_ASIDE_READS = {
    "statement": "a bank or card statement page",
    "report_summary": "a summary page",
    "other": "not a receipt",
}
_RENDERED_BODY = "rendered-body.pdf"


def mail_added_nothing(record: dict) -> bool:
    """A finished mail (ingested/replayed) that created no expense.

    `documents` must be PRESENT and empty: an archive written before the
    ingest stamped its documents is never claimed to be empty, and a mail
    whose month was deleted keeps the deleted-month story."""
    docs = record.get("documents")
    return (
        str(record.get("status", "")) in (STATUS_INGESTED, STATUS_REPLAYED)
        and isinstance(docs, list)
        and not docs
        and not record.get("batch_deleted")
    )


def no_expense_label(not_added) -> str:
    """The intake row's label for a mail that added nothing."""
    entries = [e for e in (not_added or []) if isinstance(e, dict)]
    whys = {str(e.get("why") or "") for e in entries}
    if not whys:
        # Stamped before item 106, or nothing reached the month at all.
        return "Nothing added"
    if whys == {"already_on_file"}:
        return "Nothing added: already on file"
    if whys == {"set_aside"}:
        reasons = {str(e.get("reason") or "") for e in entries}
        if reasons == {"statement"}:
            return "Nothing added: read as a statement page"
        if reasons == {"report_summary"}:
            return "Nothing added: read as a summary page"
        return "Nothing added: not read as a receipt"
    if whys <= {"set_aside", "already_on_file"}:
        return "Nothing added: set aside or already on file"
    return "Nothing added: a file could not be read"


def _created_batch_not_added(run) -> list[dict]:
    """`not_added` for a batch this mail CREATED (month materialization,
    trip creation): every set-aside entry and every upload rejection in a
    fresh batch is this mail's."""
    if run is None:
        return []
    from .service import set_aside_entries

    out = [
        {"file": str(e.get("display") or e.get("file") or ""),
         "why": "set_aside", "reason": str(e.get("reason") or ""),
         "document_id": str(e.get("file") or "")}
        for e in set_aside_entries(run.snapshot or {})
    ]
    for d in (run.summary or {}).get("upload_issue_details") or []:
        if isinstance(d, dict) and d.get("code"):
            out.append({"file": str(d.get("file") or ""), "why": str(d["code"])})
    return out


def _own_outcome(run, arch: Path | None, summary: dict | None) -> tuple[list[str], list[dict]]:
    """(documents, not_added) for one ingest of this mail.

    A replay after a crash that struck AFTER the batch stored this mail's
    receipts (a re-match that raised, a machine stop before the meta stamp)
    finds its own files already on file. Those are this mail's expenses,
    not copies: the stored file's provenance names this archive. Never
    raises; on any doubt the add's own summary stands."""
    documents = list((summary or {}).get("documents") or [])
    not_added = list((summary or {}).get("not_added") or [])
    if run is None or arch is None:
        return documents, not_added
    try:
        snap = run.snapshot or {}
        prov = snap.get("intake_provenance") or {}
        pool = {
            str(r.get("document_id")) for r in snap.get("receipts") or []
            if isinstance(r, dict)
        }
        kept: list[dict] = []
        for e in not_added:
            doc = str(e.get("document_id") or "") if isinstance(e, dict) else ""
            if (
                isinstance(e, dict) and e.get("why") == "already_on_file"
                and doc in pool
                and (prov.get(doc) or {}).get("archive") == arch.name
            ):
                if doc not in documents:
                    documents.append(doc)
                continue
            kept.append(e)
        return documents, kept
    except Exception:  # noqa: BLE001 - the plain summary is still true
        return (
            list((summary or {}).get("documents") or []),
            list((summary or {}).get("not_added") or []),
        )


def apply_restored_set_aside(rows: list[dict], run) -> None:
    """Read-time overlay for one batch: a set-aside file an operator has
    since RESTORED is an expense of the mail that brought it, so the row
    stops reading "Nothing added" without rewriting the archive."""
    restored = {
        str(e.get("file") or "")
        for e in (run.snapshot or {}).get("set_aside") or []
        if isinstance(e, dict) and e.get("restored")
    }
    if not restored:
        return
    for row in rows:
        if str(row.get("batch_id") or "") != run.run_id:
            continue
        entries = row.get("not_added")
        if not isinstance(entries, list):
            continue
        back = [
            e for e in entries
            if isinstance(e, dict) and e.get("why") == "set_aside"
            and str(e.get("document_id") or "") in restored
        ]
        if not back:
            continue
        docs = list(row.get("documents") or [])
        for e in back:
            if e["document_id"] not in docs:
                docs.append(e["document_id"])
        row["documents"] = docs
        left = [e for e in entries if e not in back]
        if left:
            row["not_added"] = left
        else:
            row.pop("not_added", None)


def _safe_echo(name: str) -> str:
    """A sender-supplied file name, flattened before it is echoed into a
    mail from receipts@: no line breaks, no URL punctuation, bounded."""
    flat = re.sub(r"[^A-Za-z0-9._ ()-]", "_", str(name or ""))
    return flat[:80] or "file"


def _no_expense_ack_body(
    meta: dict, *, subject: str, month: str, batch_label: str,
    batch_is_trip: bool, signature: str,
) -> str:
    """Acknowledgement for a mail that created no expense: what happened
    to each file and what would help. File names and the subject are the
    sender's own words echoed back to the sender; nothing here is decided
    by the mail's content (rule_untrusted_inbound)."""
    if batch_label:
        where = f'the "{batch_label}" ' + ("trip" if batch_is_trip else "expense month")
    elif month:
        where = _month_human(month)
    else:
        where = "its expense month"
    lead = f'Your email "{subject}"' if subject else "Your email"
    lines = [
        f"{lead} reached the Brisken expense tool, but no expense was "
        f"added to {where}."
    ]
    entries = [e for e in (meta.get("not_added") or []) if isinstance(e, dict)]
    set_aside = unreadable = False
    for e in entries:
        file = str(e.get("file") or "")
        name = "The email text" if file == _RENDERED_BODY else f'"{_safe_echo(file)}"'
        why = str(e.get("why") or "")
        if why == "set_aside":
            set_aside = True
            reading = _SET_ASIDE_READS.get(str(e.get("reason") or ""), "not a receipt")
            lines.append(f"- {name} read as {reading}, so it was set aside.")
        elif why == "already_on_file":
            lines.append(
                f"- {name} was already on file, so it was not added a "
                "second time."
            )
        else:
            unreadable = True
            lines.append(f"- {name} could not be read.")
    for skipped in meta.get("skipped") or []:
        # Only a file TYPE the tool cannot read; a signature logo (a tiny
        # image of a readable type) is not worth the sender's attention.
        if Path(str(skipped)).suffix.lower() not in FOLDER_RECEIPT_SUFFIXES:
            unreadable = True
            lines.append(
                f'- "{_safe_echo(skipped)}" was not read (the tool reads PDF, '
                "PNG, JPEG and WebP files)."
            )
    if set_aside or unreadable or not entries:
        lines.append(
            "If the receipt or invoice is behind a link in the email, or in "
            "a file that was not read, please forward it as a PDF or a photo."
        )
    if set_aside:
        lines.append(
            "If a set-aside file is a receipt after all, it can be restored "
            "from the month's set-aside list in the expense tool."
        )
    if not (set_aside or unreadable) and entries:
        lines.append("No action needed.")
    return "\n".join(lines) + f"\n\nAutomated confirmation from {signature}."


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
            documents, not_added = _own_outcome(
                None if batch_gone or arch is None else store.get_run(run_id),
                arch, summary,
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
                    "documents": documents,
                    # Item 106: why each other file created no expense.
                    "not_added": not_added,
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
        provenance[digest] = _provenance_entry(person, received_at, arch)
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


def _auto_render(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
    arch: Path, person: dict,
) -> dict:
    """Read a known submitter's body-only mail on arrival instead of
    holding it for a click.

    A forwarded vendor receipt IS the email body far more often than it is
    an attachment: every one of the six mails held on 2026-08-24 (AWS,
    OpenAI twice, an OpenAI credits confirmation, the CIC card ticket,
    Hostinger) delivered no file at all. Holding each of them made the
    NORMAL shape of a forwarded receipt read as a fault, and left the
    sender with no signal either way. This reuses the operator's render
    path unchanged — same CAS, same month stamps, same pool — so an
    auto-rendered receipt still reaches a month only through the review
    every other receipt passes.

    Known senders only: the mailbox takes mail from anyone, and paying a
    vision call to render every stranger's newsletter is exactly the spend
    the click was holding back. A stranger's body-only mail still holds,
    and still alerts.
    """
    try:
        result = render_ingest(
            db_path, learning_db_path, data_root, arch.name,
            operator=AUTO_RENDER_OPERATOR,
        )
    except Exception as exc:  # noqa: BLE001 - never raise past the router
        log.warning("auto-render failed for %s: %s", arch.name, exc)
        result = {"error": f"auto-render failed: {exc}"[:400]}
    status = str(_read_meta(arch).get("status", ""))
    if status == STATUS_RENDERING:
        # `rendering` is transient and only `reconcile_interrupted` clears
        # it, so an exception that escaped the render path would strand
        # the mail there until the next boot — and the CAS would refuse a
        # manual retry meanwhile. Hand it to held_failed, which replay and
        # the render endpoint can both reach (the `rendered` stamp set on
        # the way in is what keeps it retryable).
        _transition_meta(
            arch,
            lambda m: str(m.get("status", "")) == STATUS_RENDERING,
            {"status": HELD_FAILED,
             "error": str(result.get("error") or "auto-render interrupted")},
        )
        status = HELD_FAILED
    if status.startswith("held_"):
        # Nobody is watching an automatic render, so this alert is the
        # only thing that says it did not work.
        _maybe_alert(db_path, arch, status)
    return {
        **result, "status": status, "archive": arch.name,
        "person": person, "auto_rendered": True,
    }


class MonthOpenedMeanwhile(Exception):
    """Another creator committed this month between our re-check and our
    commit. `_MATERIALIZE_LOCK` makes mail-vs-mail creation single-winner,
    but the operator upload path (`POST /api/expense-batches`) takes no
    lock and its own execute runs for minutes, so its row can land
    mid-create. The pre-commit re-check turns that from two same-month
    batches into a clean abort."""


def _create_month_from_mail(
    db_path: Path,
    learning_db_path: Path | None,
    data_root: Path,
    arch: Path,
    attachments: list[tuple[str, bytes]],
    person: dict,
    month: str,
    received_at: str,
    *,
    owned_status: str,
):
    """Create ``month``'s batch FROM this mail's receipts (item 39) and
    stamp the archive ingested. Returns ``(run, job_id, stamped)``.

    Create-with-receipt, not create-then-add: `create_expense_batch`
    refuses an empty batch, and that refusal is this path's floor too — a
    mail whose every file the upload validation rejects raises
    `RunInputError` here and the caller pools the mail instead. A month is
    never created without a receipt in it.

    The label is `_month_human` ("July 2026"), which `month_from_label`
    parses back to the same month — that round-trip is what makes the new
    batch claimable by the rest of its pooled mail.

    Vision is cache-warm in production: arrival already read these bytes
    with an identically-composed client.

    A done JOB row is written for the create, so the ingested outcome
    carries a `job_id` like every other ingest (an SPA that polls
    `/jobs/{id}` after "not a duplicate" reads a real done job, not
    undefined).

    The final meta stamp is a CAS on ``owned_status`` (the transient the
    caller holds — `routing` on arrival, `claiming` on backfill), never an
    unconditional write: a create runs for minutes, which is longer than
    the stale-transient replay threshold, so a concurrent replay or a
    dismiss can legitimately take the archive meanwhile and must not be
    silently reversed. ``stamped`` says whether we still owned it.

    Caller holds `_MATERIALIZE_LOCK` and has re-checked the month is not
    open. Raises `MonthOpenedMeanwhile` (work dir cleaned, no run row)
    when a competing creator committed the month mid-create."""
    with RunStore(db_path) as store:
        settings = store.get_settings()
    provenance = {
        hashlib.sha1(data).hexdigest()[:16]: _provenance_entry(
            person, received_at, arch)
        for _name, data in attachments
    }
    prepared = create_expense_batch(
        Path(data_root),
        files=attachments,
        legal_entity="",
        label=_month_human(month),
        now_iso=_now_iso(),
        operator=None,
        learning_db_path=learning_db_path,
        settings=settings,
        created_by="intake",
        provenance_by_digest=provenance,
    )
    ym = _ym(month)

    def _month_still_absent(store: RunStore) -> None:
        if _open_batch_for_month(store, ym) is not None:
            raise MonthOpenedMeanwhile(month)

    try:
        with RunStore(db_path) as store:
            run_id = execute_expense_batch(
                store, prepared, pre_commit=_month_still_absent,
            )
            job_id = uuid.uuid4().hex[:12]
            store.create_job(job_id, None, _now_iso())
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id, updated_at=_now_iso()
            )
            run = store.get_run(run_id)
    except MonthOpenedMeanwhile:
        shutil.rmtree(prepared.work_dir, ignore_errors=True)
        raise
    documents = [
        str(r.get("document_id"))
        for r in ((run.snapshot or {}).get("receipts") or [])
    ] if run is not None else []
    stamped, _m = _transition_meta(
        arch,
        lambda m: str(m.get("status", "")) == owned_status,
        {"status": STATUS_INGESTED, "batch_id": run_id, "job_id": job_id,
         "batch_deleted": False, "materialized": True,
         "documents": documents,
         "not_added": _created_batch_not_added(run)},
    )
    if not stamped:
        # Someone (a stale-transient replay, a dismiss) took the archive
        # while the create ran. The batch stands — its receipts are real —
        # but their ruling on the ARCHIVE outranks our stamp.
        log.warning("materialize stamp lost for %s (status moved)",
                    arch.name)
    return run, job_id, stamped


def _ensure_month_for_arrival(
    db_path: Path,
    learning_db_path: Path | None,
    data_root: Path,
    arch: Path,
    parsed: "InboundMessage",
    person: dict,
    month: str,
    source: str,
    received_at: str,
    *,
    synchronous: bool = False,
) -> tuple[object, dict | None]:
    """The arrival half of item 39: materialize the month for a mail that
    would otherwise pool. Returns ``(run, result)``:

    - ``(created_run, ingested-result)`` — the month was created from this
      mail and the mail is already in it; the caller returns the result.
    - ``(None, pooled-result)`` — creation was refused or crashed; the
      mail is POOLED (the truthful resting place — the operator backfill
      retries it), never held.
    - ``(open_run, None)`` — lost the creation race (another arrival made
      the month first, or an operator upload committed it mid-create).
      The caller falls through to the normal ingest.
    """
    with _MATERIALIZE_LOCK:
        with RunStore(db_path) as store:
            run = _open_batch_for_month(store, _ym(month))
        if run is not None:
            return run, None
        err = ""
        try:
            run, job_id, stamped = _create_month_from_mail(
                db_path, learning_db_path, data_root, arch,
                parsed.attachments, person, month,
                received_at, owned_status=STATUS_ROUTING,
            )
        except MonthOpenedMeanwhile:
            # An operator upload committed this month while we created.
            # Their batch is the winner; join it the normal way.
            with RunStore(db_path) as store:
                run = _open_batch_for_month(store, _ym(month))
            if run is not None:
                return run, None
            # The winner vanished again (deleted immediately) — rest.
            run = None
        except Exception as exc:  # noqa: BLE001 - pool the mail, never hold
            log.warning("auto-materialize failed for %s: %s", arch.name, exc)
            err = str(exc)[:400]
            run = None
        if run is None:
            patch = {"status": STATUS_POOLED, "batch_id": "", "job_id": "",
                     "batch_deleted": False}
            if err:
                patch["error"] = err
            _transition_meta(
                arch,
                lambda m: str(m.get("status", "")) == STATUS_ROUTING,
                patch,
            )
            _maybe_ack(db_path, arch)
            return None, {
                "status": STATUS_POOLED, "archive": arch.name,
                "person": person, "pool_month": month,
                "receipt_month_source": source,
            }
    # Outside the materialize hold from here: the ack is a 20s-class Graph
    # round-trip and the claim pays vision per pooled mail; neither may
    # queue another month's creation behind it.
    if stamped:
        _maybe_ack(db_path, arch)
    # The month exists now, so its OTHER waiting mail joins the normal
    # way — the drain, not a backfill leak (item 39 protocol). Threaded on
    # a live arrival so the SMTP route slot frees; inline for replay/tests.
    if synchronous:
        try:
            claim_pooled(db_path, learning_db_path, data_root)
        except Exception:  # noqa: BLE001 - a claim never breaks its trigger
            log.warning("post-materialize pool claim failed", exc_info=True)
    else:
        threading.Thread(
            target=_claim_pooled_quiet,
            args=(db_path, learning_db_path, data_root),
            daemon=True,
        ).start()
    return run, {
        "status": STATUS_INGESTED, "archive": arch.name,
        "person": person, "pool_month": month,
        "batch_id": run.run_id, "job_id": job_id, "materialized": True,
    }


def _claim_pooled_quiet(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
) -> None:
    try:
        claim_pooled(db_path, learning_db_path, data_root)
    except Exception:  # noqa: BLE001 - a claim never breaks its trigger
        log.warning("post-materialize pool claim failed", exc_info=True)


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
    travel = is_travel_mail(parsed.to_base_locals, cfg)

    # Single-winner: CAS received -> routing before doing anything. A
    # second router (the replay sweep picking up a stale `received`, a
    # redelivery) sees the transient status and stands down, which also
    # closes the pre-existing double-route window on stale receiveds.
    # The travel stamp rides in the SAME CAS (item 38): it is decided by
    # the address alone, so it is known before any content is read, and
    # stamping it here means every later path (render, replay, claim,
    # re-ingest) reads the meta instead of re-deriving the answer. It is
    # written on EVERY route ("" when not travel), so a re-route after
    # the alias changed cannot leave a stale travel stamp behind
    # (finding 6), and an absent key means "never routed".
    applied, meta = _transition_meta(
        arch,
        lambda m: str(m.get("status", "")) == STATUS_RECEIVED,
        {"status": STATUS_ROUTING, "person": person,
         "pool_kind": "travel" if travel else ""},
    )
    if not applied:
        return {
            "status": str(meta.get("status", "")),
            "archive": arch.name,
            "person": meta.get("person") or person,
            "skipped": "already routed",
        }
    arrival_iso = str(meta.get("at") or received_at)

    # Inbound mail is DATA, never instructions (rule_untrusted_inbound).
    # Scan the subject and body for text addressed to an assistant and stamp
    # the hits on the archive: they raise a review flag on whatever receipts
    # this mail creates and hold the auto-ack back. Nothing branches on the
    # content itself, so a sender cannot steer routing by writing to us.
    try:
        _flags = untrusted.scan(
            str(meta.get("subject") or ""), _archive_body_text(arch))
    except Exception:  # noqa: BLE001 - a flag is advisory; never block intake
        _flags = ()
    if _flags:
        _update_meta(arch, {"untrusted_instructions": list(_flags)})
        _append_log(data_root, {
            "at": received_at, "archive": arch.name,
            "event": "untrusted_instructions",
            "kinds": list(untrusted.labels(_flags)),
        })

    try:
        # Mail we cannot read as receipts never pays for extraction.
        # Duplicates are sorted out BEFORE anything else happens to the
        # mail (owner directive 2026-08-25). Before the body-only branch
        # specifically: a re-send of a body-only receipt would otherwise
        # auto-render and spend a vision call reading a receipt we hold.
        fingerprints = content_fingerprints(
            parsed.attachments,
            _archive_body_text(arch) if parsed.body_only else "",
        )
        with _DEDUPE_LOCK:
            # An operator who already ruled "not a duplicate" outranks the
            # detector; without this the mail would re-park on the way
            # back in and the override would be a no-op.
            overridden = bool(_read_meta(arch).get("duplicate_override"))
            original = (
                None if overridden
                else classify_duplicate(data_root, arch, fingerprints)
            )
            if original is not None:
                _update_meta(arch, {
                    "status": STATUS_DUPLICATE,
                    "fingerprints": fingerprints,
                    "duplicate_of": original["archive"],
                    "duplicate_of_subject": original["subject"],
                    "duplicate_of_at": original["at"],
                })
                _maybe_ack(db_path, arch)
                return {
                    "status": STATUS_DUPLICATE, "archive": arch.name,
                    "person": person, "duplicate_of": original["archive"],
                }
            # Claim this content while still holding the lock, and while
            # the status is `routing` (which owns content), so two
            # identical mails racing here cannot both come out unique.
            _update_meta(arch, {"fingerprints": fingerprints})

        if parsed.body_only or not parsed.attachments:
            held = HELD_BODY_ONLY if parsed.body_only else HELD_NO_VALID_FILES
            _update_meta(arch, {"status": held})
            if held == HELD_BODY_ONLY and is_known_sender(
                parsed.from_addr, cfg
            ):
                return _auto_render(
                    db_path, learning_db_path, data_root, arch, person,
                )
            _maybe_alert(db_path, arch, held)
            return {"status": held, "archive": arch.name, "person": person}

        # Every attachment mail gets stamped, direct-ingest included: the
        # stamp is what lets a deleted month hand its mail back to the
        # pool instead of stranding it.
        stamps = _month_stamps(arch, settings, arrival_iso)
        _update_meta(arch, stamps)
        month = str(stamps["receipt_month"])

        if travel:
            # Item 38: travel mail RESTS in the pool, unconditionally —
            # deny-by-default. It never consults the month batches (a
            # trip has a name and a roster only a human knows, so
            # nothing here may pick one) and never auto-joins a trip
            # even when exactly one covers its dates; that trip is a
            # SUGGESTION on the pooled row, and joining is a click.
            # The dates were still extracted above: they feed the
            # suggestion, and the cache is warm for the eventual join.
            # DELIBERATELY ABOVE the item-39 materializer: travel mail
            # must never open a month, whatever the flag says.
            _transition_meta(
                arch,
                lambda m: str(m.get("status", "")) == STATUS_ROUTING,
                {"status": STATUS_POOLED, "batch_id": "",
                 "batch_deleted": False},
            )
            _maybe_ack(db_path, arch)
            return {
                "status": STATUS_POOLED, "archive": arch.name,
                "person": person, "pool_month": month,
                "pool_kind": "travel",
                "receipt_month_source": stamps["receipt_month_source"],
            }

        # Ensure-month (item 39) fires ONLY here — the no-open-batch branch
        # of arrival routing — and only when the month came off a RECEIPT
        # (the plausibility clamps already turned a wrong-year read into
        # "implausible-receipt", which pools). `claim_pooled` stays
        # create-free: a deploy or boot must never backfill months
        # unattended. KNOWN SENDERS only, same reason auto-render is: the
        # mailbox takes mail from anyone, and letting a stranger's dated
        # PDF decide when months exist (and when the pool drains into
        # them) hands an outsider the operator's call. A stranger's mail
        # pools exactly as before; the explicit backfill files it.
        may_materialize = (
            auto_materialize_enabled()
            and stamps["receipt_month_source"] == "receipt"
            and is_known_sender(parsed.from_addr, cfg)
        )

        # Decide atomically: ask whether the month is open and commit the
        # answer under one hold, so a batch created between the two cannot
        # leave this mail both ingested and pooled.
        with _POOL_LOCK:
            with RunStore(db_path) as store:
                run = _open_batch_for_month(store, _ym(month))
            if run is None and not may_materialize:
                _transition_meta(
                    arch,
                    lambda m: str(m.get("status", "")) == STATUS_ROUTING,
                    {"status": STATUS_POOLED, "batch_id": "",
                     "batch_deleted": False},
                )
            elif run is not None:
                # batch_deleted: False clears a stale delete stamp when
                # mail re-routes into a live batch — without it the row
                # would keep saying "month deleted" about live receipts.
                _update_meta(arch, {
                    "batch_id": run.run_id, "batch_deleted": False,
                })

        if run is None and may_materialize:
            # Status is still `routing` (ours via the CAS above) while the
            # month is created; single-winner via _MATERIALIZE_LOCK.
            run, result = _ensure_month_for_arrival(
                db_path, learning_db_path, data_root, arch, parsed,
                person, month, stamps["receipt_month_source"], received_at,
                synchronous=synchronous,
            )
            if result is not None:
                return result
            # Lost the creation race — `run` is the winner's batch; join
            # it the normal way.
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
            "error_code": "mail_routing_failed",
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
        if str(meta.get("pool_kind") or "") == "travel":
            # Travel mail is never claimed by a month, whatever its
            # receipt_month stamp says: it rests until an operator joins
            # it to a trip (item 38, deny-by-default).
            still_pooled += 1
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
                {"status": STATUS_POOLED, "batch_id": "", "job_id": "",
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
                {"status": STATUS_POOLED, "batch_id": "", "job_id": "",
                 "batch_deleted": False},
            )
            failed += 1
    return {
        "claimed": claimed, "still_pooled": still_pooled, "failed": failed,
    }


def materialize_pooled(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
) -> dict:
    """The explicit operator backfill (item 39): create month batches for
    confidently-stamped pooled mail, oldest month first. The endpoint runs
    `claim_pooled` right after, which drains each created month's other
    waiting mail.

    One creation per month: the oldest stamped mail of a month becomes the
    month's first receipt. Only ``receipt``-sourced stamps qualify — an
    arrival-stamped mail keeps resting, because its month is a guess about
    delivery, not a fact printed on a receipt. Stamps are trusted as they
    stand: this sweep never re-reads a receipt to decide a month
    (vision-free where stamps exist).

    Flag-gated like the arrival path: the endpoint checks
    `auto_materialize_enabled()` and refuses without it, so flipping the
    flag off returns the whole tool to today's behavior."""
    out: dict = {"materialized_months": [], "failed": 0}
    root = inbound_root(data_root)
    if not root.is_dir():
        return out
    by_month: dict[str, Path] = {}
    for arch in sorted(root.iterdir()):
        if not (arch / "meta.json").is_file():
            continue
        meta = _read_meta(arch)
        if str(meta.get("status", "")) != STATUS_POOLED:
            continue
        if str(meta.get("pool_kind") or "") == "travel":
            # Item 38 x item 39 (rebase interplay): travel mail is never
            # material for a MONTH — its receipt_month stamp exists only
            # to warm the cache and feed the trip suggestion. It rests
            # until an operator joins it to a trip; the backfill must not
            # seed a month batch from a travel receipt.
            continue
        if str(meta.get("receipt_month_source", "")) != "receipt":
            continue
        if _ym(str(meta.get("receipt_month") or "")) is None:
            continue
        if not (
            (arch / "parts").is_dir()
            or (arch / "rendered-body.pdf").is_file()
        ):
            continue
        # sorted() walks oldest archive first, so the first seen wins.
        by_month.setdefault(str(meta["receipt_month"]), arch)
    for month in sorted(by_month):
        arch = by_month[month]
        # Own the mail before creating anything: a concurrent claim,
        # dismiss, or replay sees `claiming` and stands down.
        applied, meta = _transition_meta(
            arch,
            lambda m: str(m.get("status", "")) == STATUS_POOLED,
            {"status": STATUS_CLAIMING},
        )
        if not applied:
            continue
        with _MATERIALIZE_LOCK:
            with RunStore(db_path) as store:
                run = _open_batch_for_month(store, _ym(month))
            if run is not None:
                # The month opened meanwhile — back to the pool; the
                # claim that follows this sweep drains it.
                _transition_meta(
                    arch,
                    lambda m: str(m.get("status", "")) == STATUS_CLAIMING,
                    {"status": STATUS_POOLED, "batch_id": "", "job_id": "",
                     "batch_deleted": False},
                )
                continue
            attachments = _archive_attachments(arch)
            person = _archive_person(meta)
            try:
                created, job_id, stamped = _create_month_from_mail(
                    db_path, learning_db_path, data_root, arch,
                    attachments, person, month, _now_iso(),
                    owned_status=STATUS_CLAIMING,
                )
            except MonthOpenedMeanwhile:
                # An operator upload committed this month mid-create: not
                # a failure — back to the pool, and the claim that follows
                # this sweep drains it into the winner.
                _transition_meta(
                    arch,
                    lambda m: str(m.get("status", "")) == STATUS_CLAIMING,
                    {"status": STATUS_POOLED, "batch_id": "", "job_id": "",
                     "batch_deleted": False},
                )
                continue
            except Exception as exc:  # noqa: BLE001 - one month, not the sweep
                log.warning("backfill materialize failed for %s: %s",
                            arch.name, exc)
                _transition_meta(
                    arch,
                    lambda m: str(m.get("status", "")) == STATUS_CLAIMING,
                    {"status": STATUS_POOLED, "batch_id": "", "job_id": "",
                     "batch_deleted": False, "error": str(exc)[:400]},
                )
                out["failed"] += 1
                continue
        # Outside the materialize hold: the ack is a Graph round-trip.
        if stamped:
            _maybe_ack(db_path, arch)
        _append_log(data_root, {
            "at": _now_iso(), "from": meta.get("from", ""),
            "person": person.get("person"),
            "subject": meta.get("subject", ""),
            "n_files": len(attachments), "status": STATUS_INGESTED,
            "archive": arch.name, "batch_id": created.run_id,
            "job_id": job_id,
        })
        out["materialized_months"].append(created.label)
    return out


def re_pool_stranded(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
) -> dict:
    """Item 39's re-pool sweep for legacy `batch_deleted` archives: lazily
    month-stamp stampable ones (the replay pre-stamp pattern) and return
    them to the POOL. Dismissed archives are excluded by `_stranded_legacy`;
    an unstampable one stays legacy (the item-19 re-ingest still reaches it
    once a month is open).

    Runs ONLY on the explicit `materialize: true` call, and the endpoint
    runs it LAST — after the backfill and the claim — so a re-pooled
    archive always RESTS for at least one full round-trip: the operator
    sees the freshly-guessed stamps before any later call may act on them.
    Keeping it out of the plain replay keeps a flag-off deploy inert (a
    routine "Retry held emails" click must not spend vision or migrate
    seven real archives)."""
    root = inbound_root(data_root)
    re_pooled = 0
    if not root.is_dir():
        return {"re_pooled": 0}
    settings: dict | None = None
    client = _UNSET
    for arch in sorted(root.iterdir()):
        if not (arch / "meta.json").is_file():
            continue
        meta = _read_meta(arch)
        if not _stranded_legacy(meta):
            continue
        if not (
            (arch / "parts").is_dir()
            or (arch / "rendered-body.pdf").is_file()
        ):
            continue
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
            except Exception as exc:  # noqa: BLE001 - stays legacy
                log.warning("re-pool stamp failed for %s: %s",
                            arch.name, exc)
                continue
        applied, _m = _transition_meta(
            arch, _stranded_legacy,
            {"status": STATUS_POOLED, "batch_id": "",
             "batch_deleted": False,
             # The rows this mail created went with the month; and no
             # stamp from a previous life may survive the trip back —
             # a stale done job_id would blind the boot sweep's
             # claiming-recovery, and a stale materialized flag would
             # relabel a later normal claim as "Filed into".
             "documents": [], "job_id": "", "materialized": False,
             "re_pooled_at": _now_iso()},
        )
        if applied:
            re_pooled += 1
    return {"re_pooled": re_pooled}


# Trip-batch creation is serialized so two simultaneous joins to a
# batch-less trip cannot each create one. Joins are operator clicks —
# rare — so holding one lock across the whole join (vision included) is
# correct and keeps "one batch per trip" a structural fact rather than a
# race outcome. Arrival routing never takes this lock.
_TRIP_JOIN_LOCK = threading.Lock()


def join_trip(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
    archive: str, trip_id: str, operator: str | None = None,
) -> dict:
    """Join ONE travel-pooled mail to a trip — the operator's click, the
    only way travel mail becomes expenses (item 38, deny-by-default; the
    suggestion on the row is a reading, this is the decision).

    The trip's batch is created WITH this mail's receipts when it does
    not exist yet (create-with-receipt, the same ordering item 39 uses
    for months: `create_expense_batch` refuses an empty batch and that
    refusal is load-bearing), else the receipts are added incrementally
    exactly like a month claim. Either way the mail's submitter rides in
    as provenance, and a failure puts the mail back to RESTING in the
    travel pool for the next click."""
    arch = _archive_dir(data_root, archive)
    if arch is None:
        return {"error": "not found", "code": 404, "error_code": "mail_not_found"}
    meta = _read_meta(arch)
    if str(meta.get("pool_kind") or "") != "travel":
        return {
            "error": "only travel mail joins a trip; month mail joins "
                     "its month automatically",
            "code": 409,
            "error_code": "mail_not_travel",
        }
    with RunStore(db_path) as store:
        trip = store.get_trip(str(trip_id))
    if trip is None:
        return {"error": "trip not found", "code": 404,
                "error_code": "trip_not_found"}
    attachments = _archive_attachments(arch)
    if not attachments:
        return {
            "error": "this mail has no ingestable file yet; render its "
                     "body first",
            "code": 409,
            "error_code": "mail_no_file_yet",
        }

    with _TRIP_JOIN_LOCK:
        with RunStore(db_path) as store:
            run = find_trip_batch(store, trip.trip_id)
        # Single-winner on the archive: pooled -> claiming, same CAS the
        # month claim uses, so a double click or a concurrent replay
        # sweep sees the transient state and stands down.
        applied, meta = _transition_meta(
            arch,
            lambda m: str(m.get("status", "")) == STATUS_POOLED,
            {"status": STATUS_CLAIMING,
             "batch_id": run.run_id if run is not None else ""},
        )
        if not applied:
            return {
                "error": "cannot join mail in state "
                         f"{str(meta.get('status', ''))!r}",
                "code": 409,
                "error_code": "mail_state_conflict",
                "status": str(meta.get("status", "")),
            }
        person = _archive_person(meta)
        received_at = str(meta.get("at") or _now_iso())

        if run is not None:
            try:
                job_id = _start_ingest(
                    db_path, learning_db_path, run, attachments, person,
                    received_at, arch, synchronous=True,
                )
                with RunStore(db_path) as store:
                    job = store.get_job(job_id) or {}
            except Exception as exc:  # noqa: BLE001 - same guard as claim_pooled
                # A failure BEFORE the job existed (staging, disk, store)
                # would otherwise strand the archive in `claiming` and
                # 409 every further click (finding 5). Back to resting.
                log.warning("trip join failed for %s: %s", arch.name, exc)
                _transition_meta(
                    arch,
                    lambda m: str(m.get("status", "")) == STATUS_CLAIMING,
                    {"status": STATUS_POOLED, "batch_id": "",
                     "batch_deleted": False, "error": str(exc)[:400]},
                )
                return {"error": f"join failed: {exc}"[:400], "code": 500,
                        "error_code": "trip_join_failed"}
            if job.get("status") != JOB_DONE:
                # _ingest_job stamped held_failed + the error; the
                # RESTING place for travel mail is the travel pool.
                _transition_meta(
                    arch,
                    lambda m: str(m.get("status", "")) == HELD_FAILED,
                    {"status": STATUS_POOLED, "batch_id": "",
                     "batch_deleted": False},
                )
                return {
                    "error": str(job.get("error") or "ingest failed"),
                    "code": 500,
                    "error_code": "mail_ingest_failed",
                }
            _update_meta(arch, {"job_id": job_id, "batch_id": run.run_id,
                                "batch_deleted": False})
            final = _read_meta(arch)
            _append_log(data_root, {
                "at": _now_iso(), "from": meta.get("from", ""),
                "person": person.get("person"),
                "subject": meta.get("subject", ""),
                "n_files": len(attachments), "status": STATUS_INGESTED,
                "archive": arch.name, "batch_id": run.run_id,
                "job_id": job_id,
            })
            return {
                "status": str(final.get("status", "")),
                "archive": arch.name, "batch_id": run.run_id,
                "trip_id": trip.trip_id, "job_id": job_id,
                "documents": final.get("documents", []),
            }

        # No batch yet: create it WITH this mail's receipts, holding the
        # trip-batch slot so a concurrent upload declaring the same trip
        # cannot create a second batch while this OCR runs (finding 1),
        # and so the trip entity cannot be deleted out from under the
        # creation (finding 2; `delete_trip_entity` shares the lock).
        with RunStore(db_path) as store:
            refused = claim_trip_batch_slot(store, trip.trip_id)
        if refused is not None:
            # A concurrent upload won the creation (or just finished).
            # Back to resting; the next click lands on the append path.
            _transition_meta(
                arch,
                lambda m: str(m.get("status", "")) == STATUS_CLAIMING,
                {"status": STATUS_POOLED, "batch_id": "",
                 "batch_deleted": False},
            )
            return dict(refused)
        prepared = None
        try:
            provenance = {
                hashlib.sha1(data).hexdigest()[:16]: _provenance_entry(
                    person, received_at, arch)
                for _name, data in attachments
            }
            with RunStore(db_path) as store:
                settings = store.get_settings()
            prepared = create_expense_batch(
                data_root,
                files=attachments,
                legal_entity="",
                label=trip.name,
                now_iso=_now_iso(),
                operator=operator,
                learning_db_path=learning_db_path,
                settings=settings,
                batch_type=BATCH_TYPE_TRIP,
                trip_id=trip.trip_id,
                provenance_by_digest=provenance,
            )
            with RunStore(db_path) as store:
                run_id = execute_expense_batch(store, prepared)
                created = store.get_run(run_id)
        except Exception as exc:  # noqa: BLE001 - pool it back, keep it clickable
            if prepared is not None:
                shutil.rmtree(prepared.work_dir, ignore_errors=True)
            _transition_meta(
                arch,
                lambda m: str(m.get("status", "")) == STATUS_CLAIMING,
                {"status": STATUS_POOLED, "batch_id": "",
                 "batch_deleted": False, "error": str(exc)[:400]},
            )
            log.warning("trip join failed for %s: %s", arch.name, exc)
            return {"error": f"join failed: {exc}"[:400], "code": 500,
                        "error_code": "trip_join_failed"}
        finally:
            release_trip_batch_slot(trip.trip_id)
        documents = [
            str(r.get("document_id"))
            for r in (created.snapshot or {}).get("receipts") or []
            if isinstance(r, dict) and r.get("document_id")
        ]
        _update_meta(arch, {
            "status": STATUS_INGESTED, "batch_id": run_id,
            "batch_deleted": False, "documents": documents,
            "not_added": _created_batch_not_added(created),
        })
        _maybe_ack(db_path, arch)
        _append_log(data_root, {
            "at": _now_iso(), "from": meta.get("from", ""),
            "person": person.get("person"),
            "subject": meta.get("subject", ""),
            "n_files": len(attachments), "status": STATUS_INGESTED,
            "archive": arch.name, "batch_id": run_id,
        })
        return {
            "status": STATUS_INGESTED, "archive": arch.name,
            "batch_id": run_id, "trip_id": trip.trip_id,
            "documents": documents, "created_batch": True,
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


def _stranded_legacy(meta: dict) -> bool:
    """Mail stranded by a deleted month, resting in a terminal status.

    These predate the month stamps (stamped mail re-pools in the delete
    cascade), so until item 39 the per-archive re-ingest was their only
    way back — and it 409s with zero months open and targets the NEWEST
    open batch, not the receipt's month. Dismissed mail stays dismissed
    (the operator's junk ruling outranks where it used to live);
    transient states belong to whoever holds them."""
    if not meta.get("batch_deleted"):
        return False
    return str(meta.get("status", "")) in {STATUS_INGESTED, STATUS_REPLAYED}


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
        if "pool_kind" not in meta:
            # A router that died BEFORE the routing CAS (custody taken,
            # 250 sent, no stamp) left an archive replay would otherwise
            # month-route blind — finding 3: a travel-addressed mail
            # ingested into a company month via the crash path. The
            # base locals were archived at custody; derive the answer
            # against the CURRENT alias, exactly as arrival would.
            if settings is None:
                with RunStore(db_path) as store:
                    settings = store.get_settings()
            locals_ = list(
                meta.get("to_base_locals") or meta.get("to_locals") or []
            )
            kind = "travel" if is_travel_mail(
                locals_, IntakeConfig.from_settings(settings)
            ) else ""
            _update_meta(arch, {"pool_kind": kind})
            meta = {**meta, "pool_kind": kind}
        held_status = str(meta.get("status", ""))
        if str(meta.get("pool_kind") or "") == "travel":
            # A stuck travel mail (failed join, crashed router) goes back
            # to RESTING in the travel pool; replay never month-routes it.
            applied, _m = _transition_meta(
                arch,
                lambda m, s=held_status: str(m.get("status", "")) == s,
                {"status": STATUS_POOLED, "batch_id": "",
                 "batch_deleted": False},
            )
            if applied:
                pooled += 1
            else:
                still_held += 1
            continue
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


def sweep_dismissed(db_path: Path, data_root: Path) -> int:
    """Delete archives the operator dismissed as junk, once they have sat
    dismissed for ``intake.dismissed_purge_days`` (item 122).

    Dismissal is a human saying "this is not a receipt", so the bytes are
    not an accounting record and nothing in AO paragraph 147 asks us to
    keep them; today they are kept forever and count against the same
    volume real receipts need. The grace period exists because a
    dismissal can be a mis-click, and it is measured from the DISMISSAL,
    not from arrival.

    Ships inert: the default is 0 = never. Deleting Brisken's mail is the
    owner's call, and turning it on is one settings write. Runs at boot
    beside the retention sweep, fail-open, and only ever touches archives
    whose status is `dismissed`."""
    root = inbound_root(data_root)
    if not root.exists():
        return 0
    with RunStore(db_path) as store:
        cfg = IntakeConfig.from_settings(store.get_settings())
    if cfg.dismissed_purge_days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc).timestamp() - (
        cfg.dismissed_purge_days * 86400
    )
    removed = 0
    for arch in list(root.iterdir()):
        if not arch.is_dir() or not _ARCHIVE_NAME_RE.fullmatch(arch.name):
            continue
        meta = _read_meta(arch)
        if str(meta.get("status", "")) != STATUS_DISMISSED:
            continue
        stamp = str(meta.get("dismissed_at") or "")
        try:
            when = datetime.fromisoformat(stamp)
        except ValueError:
            # No readable dismissal time: leave it. An archive we cannot
            # date is not one to delete.
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when.timestamp() < cutoff:
            shutil.rmtree(arch, ignore_errors=True)
            removed += 1
    if removed:
        log.info("purged %d dismissed inbound archives", removed)
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
        return {"error": "not found", "code": 404, "error_code": "mail_not_found"}
    text = extract_body_text((arch / "message.eml").read_bytes())
    if not text.strip():
        return {"error": "no readable body in this mail", "code": 409,
                "error_code": "mail_no_readable_body"}

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
                         f"(status: {meta.get('status', '')})", "code": 409,
                "error_code": "mail_not_renderable",
                "status": str(meta.get("status", ""))}

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
        return {"error": f"render failed: {exc}", "code": 500,
                "error_code": "mail_render_failed"}

    month = str(stamps["receipt_month"])
    if str(_read_meta(arch).get("pool_kind") or "") == "travel":
        # Item 38: a rendered travel mail rests in the travel pool like a
        # delivered one — it never month-routes and never auto-joins a
        # trip. The stamp was written at arrival routing, off the
        # address, so a render months later still routes by what the
        # sender addressed.
        _transition_meta(
            arch,
            lambda m: str(m.get("status", "")) == STATUS_RENDERING,
            {"status": STATUS_POOLED, "batch_id": "",
             "batch_deleted": False},
        )
        _maybe_ack(db_path, arch)
        return {
            "status": STATUS_POOLED, "archive": arch.name,
            "pool_month": month, "pool_kind": "travel",
        }
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
        return {"error": "not found", "code": 404, "error_code": "mail_not_found"}
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
            "error_code": "mail_no_attachment",
        }
    if str(_read_meta(arch).get("pool_kind") or "") == "travel":
        # Belt: travel mail joins a TRIP by an operator's click, never
        # "the newest open month". In practice a travel archive is always
        # month-stamped, so the delete cascade pools it back rather than
        # stamping batch_deleted, and this path cannot fire — but a
        # guard that costs one read keeps the invariant explicit.
        return {
            "error": "travel mail joins a trip, not a month; use the "
                     "trip join on the pooled row",
            "code": 409,
            "error_code": "mail_travel_not_month",
        }
    with RunStore(db_path) as store:
        run = open_batch(store)
    if run is None:
        return {"error": "no open month to ingest into", "code": 409,
                "error_code": "no_open_month"}

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
                "error_code": "mail_month_still_live",
            }
        return {
            "error": f"cannot re-ingest mail in state {status!r}",
            "code": 409,
            "error_code": "mail_state_conflict",
            "status": status,
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


def unmark_duplicate(
    db_path: Path,
    learning_db_path: Path | None,
    data_root: Path,
    archive: str,
) -> dict:
    """"This is not a duplicate" — route a parked mail after all.

    The detector matches byte-identical content, so a false positive means
    two genuinely different purchases produced identical bytes, which is
    rare but not impossible (a fixed-price subscription receipt with no
    invoice number, mailed two months running). Without a way out, a real
    receipt would rest as a duplicate forever, and "it silently vanished"
    is exactly the failure the intake-trust round was about.

    Deny-by-default: only a mail currently parked as `duplicate` qualifies,
    so this can never become a second, unguarded ingest path. The archive
    keeps its fingerprints, so the NEXT copy still detects against it.
    """
    arch = _archive_dir(data_root, archive)
    if arch is None:
        return {"error": "not found", "code": 404, "error_code": "mail_not_found"}
    applied, meta = _transition_meta(
        arch,
        lambda m: str(m.get("status", "")) == STATUS_DUPLICATE,
        {
            "status": STATUS_RECEIVED,
            "duplicate_cleared_at": _now_iso(),
            "duplicate_override": True,
        },
    )
    if not applied:
        return {
            "error": (
                "this mail is not parked as a duplicate"
            ),
            "code": 409,
            "error_code": "mail_not_duplicate",
            "status": str(meta.get("status", "")),
        }
    eml = arch / "message.eml"
    if not eml.is_file():
        _update_meta(arch, {"status": HELD_FAILED})
        return {"error": "custody message unreadable", "code": 409,
                "error_code": "mail_custody_unreadable"}
    with RunStore(db_path) as store:
        cfg = IntakeConfig.from_settings(store.get_settings())
    try:
        parsed = parse_inbound(eml.read_bytes(), cfg.domain)
    except Exception:  # noqa: BLE001 - unreadable custody file
        _update_meta(arch, {"status": HELD_FAILED})
        return {"error": "custody message unreadable", "code": 409,
                "error_code": "mail_custody_unreadable"}
    # Route it exactly as an arrival would, minus the detector: the
    # override rides on the meta and `route_archived` honours it.
    return route_archived(
        db_path, learning_db_path, data_root, arch, parsed, synchronous=True,
    )


def dismiss_archive(
    data_root: Path, archive: str, operator: str | None = None,
) -> dict:
    """Mark a held or pooled mail dismissed (operator judged it junk).
    Terminal by design: not replayable, not renderable, not claimable,
    drops out of n_held / n_pooled. The custody archive is untouched.

    Pooled mail is dismissable for the same reason held mail is: junk
    with an attachment now RESTS in the pool waiting for a month that may
    never come, and without this it would wait there undismissably. A
    duplicate is dismissable on the same argument: it rests forever
    otherwise, and clearing it is the normal way to finish with one."""
    arch = _archive_dir(data_root, archive)
    if arch is None:
        return {"error": "not found", "code": 404, "error_code": "mail_not_found"}
    applied, meta = _transition_meta(
        arch,
        lambda m: (
            str(m.get("status", "")).startswith("held_")
            or str(m.get("status", "")) in (STATUS_POOLED, STATUS_DUPLICATE)
        ),
        {
            "status": STATUS_DISMISSED,
            "dismissed_at": _now_iso(),
            "dismissed_by": operator or "",
        },
    )
    if not applied:
        return {"error": "only held or pooled mail can be dismissed "
                         f"(status: {meta.get('status', '')})", "code": 409,
                "error_code": "mail_not_dismissable",
                "status": str(meta.get("status", ""))}
    return {"status": STATUS_DISMISSED, "archive": arch.name}
# ------------------------------------------------------------ receipts drop --


def valid_month_key(month: str) -> bool:
    """True when ``month`` is a well-formed "YYYY-MM" key (the drop
    endpoint's override format)."""
    return _ym(month) is not None


def drop_rematch_summary(rematch: object) -> dict | None:
    """What the drop page says about the re-match an arrival ran (note #53):
    None when none ran (no statement, or every file was a duplicate),
    `{ok: false, error}` when it failed (the receipts are filed regardless
    and the month's next change retries), else `{ok: true}` with the month's
    counts after it."""
    if not isinstance(rematch, dict):
        return None
    if rematch.get("error"):
        return {"ok": False, "error": str(rematch["error"])}
    return {
        "ok": True,
        **{
            k: int(rematch.get(k) or 0)
            for k in ("n_transactions", "n_matched", "n_review", "n_unmatched_tx")
        },
    }


# How many dropped receipts are READ at once (item 148). Every worker is one
# concurrent vision round-trip for ONE operator's drop: the round-trip, not
# our CPU, is the wall clock, so a handful already collapses it, while a wide
# pool would fire a single drop at the provider as a burst and spend the
# shared key's per-minute headroom on retries. Six keeps a 40-file drop inside
# one round-trip-ish instead of forty, and leaves headroom for the mail
# intake reading on the same key at the same time.
_DROP_READ_WORKERS = 6
# Progress granularity for the read pass. Each report is a short-lived store
# connection, so a 500-file drop reporting every file would spend the saving
# on bookkeeping.
_DROP_PROGRESS_ALL_UNTIL = 20
_DROP_PROGRESS_EVERY = 5


def _drop_progress_due(done: int, total: int) -> bool:
    """Whether `reading receipts (done/total)` is worth a stage write: every
    file while each one still reads as movement, then every fifth, plus the
    last one whatever the pile size."""
    return (
        done <= _DROP_PROGRESS_ALL_UNTIL
        or done % _DROP_PROGRESS_EVERY == 0
        or done == total
    )


def route_dropped_receipts(
    db_path: Path,
    learning_db_path: Path | None,
    data_root: Path,
    staging: Path,
    month_override: str = "",
    on_stage=None,
) -> dict:
    """File manually dropped receipts by the month printed ON each receipt
    (the Receipts page, 2026-09-08 owner directive: receipt entry stops
    being coupled to month creation). The manual twin of mail routing:
    same extraction client, same `resolve_receipt_month` ruling, same
    guarded month materialization — one routing brain for every entrance.

    Unlike a MAIL (which routes as one unit by its earliest date), each
    dropped FILE is its own receipt and routes on its own dates. Only a
    ``receipt``-sourced month auto-files; a file with no readable
    plausible date is reported ``needs_month`` and NOT ingested, because
    silently guessing the arrival month is how receipts used to land in
    whatever batch was open. The release valve is ``month_override``
    ("YYYY-MM", the operator's explicit pick, validated by the caller):
    it files EVERY file in this call into that month, source
    ``operator`` — a typed month is believed, like a typed date.

    Months materialize UNCONDITIONALLY here when absent (created_by
    "drop"): the flag that gates MAIL materialization protects against a
    stranger's mail minting months, and an operator dropping a file on
    the page is the opposite of that. Creation mirrors the mail
    materializer where it matters: `_MATERIALIZE_LOCK` held across the
    create, `_open_batch_for_month` re-checked before the commit, and
    `MonthOpenedMeanwhile` falling back to the add path.

    Returns a per-file ledger (the drop job's ``result``): ``files`` rows
    with status ``filed`` / ``needs_month`` / ``rejected`` / ``failed``,
    and per-month ``months`` entries carrying ``created_batch`` and the
    add counts (``n_added`` < files means content duplicates were
    skipped, which is the dedupe working, not a loss). A month group
    larger than ``FOLDER_MAX_FILES`` has its overflow marked ``rejected``
    / ``upload-cap`` (with ``limit``) HERE, before the ingest call whose
    internal cap would otherwise skip those files while the row read
    ``filed``; re-dropping the same pile is safe because content dedupe
    skips what already landed."""
    from .service import FOLDER_RECEIPT_MAX_BYTES

    def _stage(name: str) -> None:
        if on_stage is not None:
            try:
                on_stage(name)
            except Exception:  # noqa: BLE001 - progress is best-effort
                pass

    now = _now_iso()
    staged = sorted(p for p in Path(staging).iterdir() if p.is_file())
    with RunStore(db_path) as store:
        settings = store.get_settings()

    rows: list[dict] = []
    routed: dict[str, list[tuple[dict, Path]]] = {}
    _stage("reading receipts")
    # Pass 1, in staged order: every verdict that costs nothing settles here
    # (unreadable type, empty, oversized, a typed month), and every file that
    # has to be READ is queued for the pool below. `records` stays in staged
    # order start to finish, so the ledger assembled from it at the end is
    # the one the end-to-end loop assembled.
    records: list[dict] = []
    to_read: list[int] = []
    for path in staged:
        display = re.sub(r"^\d{4}__", "", path.name)
        suffix = path.suffix.lower()
        if suffix not in FOLDER_RECEIPT_SUFFIXES:
            # Zips included, deliberately: a zip's members would each need
            # their own routing verdict, and the page is a drag-and-drop
            # of the files themselves.
            records.append({
                "row": {"file": display, "status": "rejected",
                        "reason": "unsupported-type"},
                "path": path, "month": None, "display": display,
            })
            continue
        size = path.stat().st_size
        if size == 0:
            records.append({
                "row": {"file": display, "status": "rejected",
                        "reason": "empty-file"},
                "path": path, "month": None, "display": display,
            })
            continue
        if size > FOLDER_RECEIPT_MAX_BYTES:
            records.append({
                "row": {"file": display, "status": "rejected",
                        "reason": "too-large"},
                "path": path, "month": None, "display": display,
            })
            continue
        if month_override:
            # A typed month is believed, so the file is never opened: the
            # override path pays no vision call and never enters the pool.
            row = {"file": display, "status": "filed",
                   "month": month_override, "month_source": "operator"}
            records.append({"row": row, "path": path,
                            "month": month_override, "display": display})
            continue
        records.append({"row": None, "path": path, "month": None,
                        "display": display})
        to_read.append(len(records) - 1)

    if to_read:
        client = _arrival_llm_client(settings)

        def _verdict(i: int) -> tuple[str, str, bool]:
            """One file's month verdict, on a pool thread. Reads only its own
            record and returns it; nothing shared is mutated here, so the
            assembly below stays the single writer of `rows` and `routed`.
            `_extract_receipt_dates` already swallows a per-file extraction
            failure into "no dates"; the guard here covers the rest of the
            read, so one unreadable file can never take down the pile."""
            try:
                dates = (
                    _extract_receipt_dates([records[i]["path"]], client)
                    if client is not None else []
                )
            except Exception:  # noqa: BLE001 - per file, exactly as before
                log.warning("drop routing failed for %s",
                            records[i]["display"], exc_info=True)
                dates = []
            return resolve_receipt_month(dates, now)

        # The reads ARE the wall clock of a drop: one vision round-trip each,
        # and end to end they simply added up (a 40-file drop measured 40x one
        # round-trip — the "way too long" the owner reported 2026-09-18).
        # Nothing in a file's verdict depends on its neighbours, so they run
        # on a bounded pool. A 429 stays a per-file event either way: the SDK
        # retries it inside the call, and a call that still fails leaves that
        # one file `needs_month` while the rest file.
        with ThreadPoolExecutor(
            max_workers=min(_DROP_READ_WORKERS, len(to_read)),
            thread_name_prefix="drop-read",
        ) as pool:
            futures = {i: pool.submit(_verdict, i) for i in to_read}
            done = 0
            for _ in as_completed(futures.values()):
                done += 1
                if _drop_progress_due(done, len(to_read)):
                    # One frozen "reading receipts" for minutes was the whole
                    # of the page's feedback; the count is what makes the wait
                    # legible. The SPA renders the stage string verbatim, so
                    # this needs nothing of it.
                    _stage(f"reading receipts ({done}/{len(to_read)})")

        for i in to_read:
            month, source, mixed = futures[i].result()
            rec = records[i]
            if source != "receipt":
                rec["row"] = {
                    "file": rec["display"], "status": "needs_month",
                    "reason": (
                        "implausible-date" if source == "implausible-receipt"
                        else "no-readable-date"
                    ),
                }
                continue
            row = {"file": rec["display"], "status": "filed", "month": month,
                   "month_source": "receipt"}
            if mixed:
                row["mixed_months"] = True
            rec["row"] = row
            rec["month"] = month

    # One writer, one order: the ledger and the per-month groups are built
    # from `records` in staged order, so the same staging folder yields a
    # byte-identical `rows` whether the reads ran one at a time or six.
    for rec in records:
        rows.append(rec["row"])
        if rec["month"] is not None:
            routed.setdefault(rec["month"], []).append(
                (rec["row"], rec["path"])
            )

    from .service import FOLDER_MAX_FILES as _drop_cap

    months_out: list[dict] = []
    created_any = False
    for month in sorted(routed):
        group = routed[month]
        if len(group) > _drop_cap:
            # The ingest call beneath (create or add) truncates at the same
            # cap and would skip the tail while its rows read "filed" —
            # mark the overflow honestly before it, and point at the safe
            # recovery (drop the pile again; dedupe skips what landed).
            for row, _path in group[_drop_cap:]:
                row["status"] = "rejected"
                row["reason"] = "upload-cap"
                row["limit"] = _drop_cap
            group = group[:_drop_cap]
        label = _month_human(month)
        _stage(f"filing {label}")
        entry: dict = {"month": month, "label": label,
                       "created_batch": False, "n_files": len(group)}
        target_run = None
        ym = _ym(month)
        with _MATERIALIZE_LOCK:
            with RunStore(db_path) as store:
                target_run = _open_batch_for_month(store, ym)
            if target_run is None:
                files_bytes = [
                    (row["file"], path.read_bytes()) for row, path in group
                ]

                def _month_still_absent(
                    store: RunStore, ym=ym, month=month,
                ) -> None:
                    if _open_batch_for_month(store, ym) is not None:
                        raise MonthOpenedMeanwhile(month)

                try:
                    prepared = create_expense_batch(
                        Path(data_root),
                        files=files_bytes,
                        legal_entity="",
                        label=label,
                        now_iso=_now_iso(),
                        operator=None,
                        learning_db_path=learning_db_path,
                        settings=settings,
                        created_by="drop",
                    )
                    with RunStore(db_path) as store:
                        run_id = execute_expense_batch(
                            store, prepared, pre_commit=_month_still_absent,
                        )
                    entry.update({
                        "batch_id": run_id, "created_batch": True,
                        "n_added": len(files_bytes),
                        # A month created by this drop holds no statement,
                        # so nothing was matched (note #53).
                        "has_statement": False,
                    })
                    if prepared.upload_issues:
                        entry["issues"] = list(prepared.upload_issues)
                    for row, _path in group:
                        row["batch_id"] = run_id
                    created_any = True
                    months_out.append(entry)
                    continue
                except MonthOpenedMeanwhile:
                    with RunStore(db_path) as store:
                        target_run = _open_batch_for_month(store, ym)
                except RunInputError as exc:
                    entry["error"] = str(exc)
                    for row, _path in group:
                        row["status"] = "failed"
                        row["reason"] = str(exc)
                    months_out.append(entry)
                    continue
        if target_run is None:
            entry["error"] = "month batch vanished mid-create"
            for row, _path in group:
                row["status"] = "failed"
                row["reason"] = entry["error"]
            months_out.append(entry)
            continue
        # The ADD path runs outside `_MATERIALIZE_LOCK`: it takes the batch
        # write lock itself and a statement-bearing month re-matches on the
        # arrival, which can run for minutes — mail materialization must
        # not queue behind it.
        add_staging = (
            Path(target_run.work_dir) / f"drop-add-{uuid.uuid4().hex[:8]}"
        )
        add_staging.mkdir(parents=True, exist_ok=True)
        try:
            for i, (row, path) in enumerate(group):
                safe = re.sub(r"[^A-Za-z0-9._-]", "_", row["file"]) or "file"
                (add_staging / f"{i:04d}__{safe}").write_bytes(
                    path.read_bytes()
                )
            with RunStore(db_path) as store:
                fresh = store.get_run(target_run.run_id)
                if fresh is None:
                    raise RunInputError(
                        "This batch no longer exists (it was deleted).",
                        code="batch_deleted",
                    )
                result = add_receipts_to_expense_batch(
                    store, fresh, add_staging, _now_iso(),
                    learning_db_path=learning_db_path,
                    on_stage=on_stage,
                )
            entry.update({
                "batch_id": target_run.run_id,
                "n_added": int(result.get("n_added") or 0),
                "has_statement": has_statement(fresh),
            })
            # Note #53: the arrival already re-matched a month holding a
            # statement; say so, and with what result, instead of dropping it.
            rematch = drop_rematch_summary(result.get("rematch"))
            if rematch is not None:
                entry["rematch"] = rematch
            if result.get("issues"):
                entry["issues"] = list(result["issues"])
            for row, _path in group:
                row["batch_id"] = target_run.run_id
        except RunInputError as exc:
            entry["error"] = str(exc)
            for row, _path in group:
                row["status"] = "failed"
                row["reason"] = str(exc)
        finally:
            shutil.rmtree(add_staging, ignore_errors=True)
        months_out.append(entry)

    if created_any:
        # A drop-created month claims its waiting mail the way every other
        # month creation does. Quiet: a claim failure never fails the drop.
        try:
            claimed = claim_pooled(db_path, learning_db_path, data_root)
            if claimed.get("claimed"):
                log.info("drop-created month(s) claimed %d pooled mail(s)",
                         claimed["claimed"])
        except Exception:  # noqa: BLE001 - a claim never breaks its trigger
            log.warning("pool claim after drop failed", exc_info=True)

    return {
        "files": rows,
        "months": months_out,
        "n_filed": sum(1 for r in rows if r["status"] == "filed"),
        "n_needs_month": sum(1 for r in rows if r["status"] == "needs_month"),
        "n_rejected": sum(1 for r in rows if r["status"] == "rejected"),
    }
