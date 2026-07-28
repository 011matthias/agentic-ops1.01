"""Line-item idempotency ledger + guarded journal poster — BLUEPRINT 4.8 / 4b.

The one guarantee this module exists to give: **the same journal entry is
never posted to Zoho Books twice**, no matter how many times a month is
re-run, re-exported, or re-posted, and no matter where in the batch a
crash or network failure lands. Zoho's own API offers no idempotency
(verified against the v3 journals docs 2026-07-28), so the ledger here is
the entire guarantee.

How the guarantee holds (owner directive 2026-07-28: "with memory
cross-reference before upload, we can guarantee that there are no
duplicates being imported into Zoho"):

* **Post the reviewed artifact.** Entries are parsed from the journal
  export CSV (`read_journal_csv`), grouped by ``Reference#`` — the same
  send-by-id discipline as `rule_brisken_graph_send_by_id`: an explicit,
  human-reviewed enumeration, never a rebuild that could drift from what
  was reviewed.
* **Cross-reference before upload.** `plan_post` partitions every
  candidate against the ledger: new, already-posted (skip), content
  conflict (refuse), in-flight/ambiguous (refuse until verified),
  unpostable (refuse). Deny-by-default: uncertainty always resolves to
  "post nothing".
* **Write-ahead intent.** `execute_post` records an ``inflight`` ledger
  row and commits it BEFORE each POST fires, so there is no instant at
  which a journal can reach Zoho without a ledger record. A crash
  between intent and confirmation leaves ``inflight``, which blocks
  re-posting until `verify_ambiguous` reconciles against Zoho itself.
* **Ambiguity is terminal for the batch.** A network failure or 5xx
  after the POST left this process (commit state unknown) marks the
  entry ``ambiguous`` and aborts the remaining batch. Only a clean Zoho
  rejection (4xx: Zoho answered, nothing was written) rolls the intent
  back and lets the batch continue.

Ledger privacy mirrors `runlog.py`, not `learning/store.py`: it stores
references (transaction ids), content HASHES, Zoho journal ids, and
timestamps — never amounts, vendors, or account names. The hash is
one-way; the financial content lives only in the CSV and in Zoho.

Nothing in this module reaches the network on its own: `plan_post` and
`entries_from_rows` are pure, the ledger is local SQLite, and only
`execute_post` / `verify_ambiguous` take a client — which `zoho_post_cli`
constructs solely behind the 4.8 gates (config ``zoho.post.enabled`` AND
env ``EXPENSE_RECON_ZOHO_POST=1`` AND the org allowlist AND ``--go``).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING

from ..coa_gate import CoaVerdict, classify_account
from ..output.zoho_export import (
    _CARD_ACCOUNT,
    _REIMBURSABLE_PLACEHOLDER,
    _UNCATEGORIZED,
    _UNMAPPED,
    ZOHO_COLUMNS,
)
from .client import ZohoAPIError, ZohoAuthError

if TYPE_CHECKING:
    from ..ingest.chart_of_accounts import ChartOfAccounts
    from .client import ZohoClient

__all__ = [
    "REFUSAL_CONFLICT",
    "REFUSAL_CROSS_ORG",
    "REFUSAL_UNPOSTABLE",
    "REFUSAL_UNRESOLVED",
    "ApiLine",
    "JournalEntry",
    "LedgerRow",
    "PostLedger",
    "PostPlan",
    "PostReport",
    "PostedConflictError",
    "VerifyReport",
    "entries_from_rows",
    "entry_content_hash",
    "execute_post",
    "plan_post",
    "verify_ambiguous",
]

# The two Brisken Books orgs the tool is provisioned for (Corporate
# Services / Cloud Services, verified in-container 2026-07-01). Posting
# to any org outside this set is refused outright; widening the set is a
# deliberate, PR-reviewed config change (`zoho.post.org_allowlist`),
# mirroring the hard mailbox allowlist in rule_brisken_graph_first.
DEFAULT_ORG_ALLOWLIST = frozenset({"822741658", "697686691"})

# CSV column positions derived from ZOHO_COLUMNS itself (never
# hand-numbered): a column reorder in the writer cannot silently
# desynchronize the reader, it changes these in the same import.
_COL_DATE = ZOHO_COLUMNS.index("Date")
_COL_ACCOUNT = ZOHO_COLUMNS.index("Account")
_COL_DESCRIPTION = ZOHO_COLUMNS.index("Description")
_COL_REFERENCE = ZOHO_COLUMNS.index("Reference#")
_COL_DEBIT = ZOHO_COLUMNS.index("Debit")
_COL_CREDIT = ZOHO_COLUMNS.index("Credit")

# Account-column values that are review flags, not postable accounts.
_PLACEHOLDER_ACCOUNTS = frozenset(
    {_UNCATEGORIZED, _UNMAPPED, _REIMBURSABLE_PLACEHOLDER}
)
_CARD_PLACEHOLDER_PREFIX = _CARD_ACCOUNT.split("{", 1)[0]  # "Card: "

_STATE_INFLIGHT = "inflight"
_STATE_POSTED = "posted"
_STATE_AMBIGUOUS = "ambiguous"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS posted_journals (
    org_id          TEXT NOT NULL,
    reference       TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    state           TEXT NOT NULL,
    zoho_journal_id TEXT,
    entry_number    TEXT,
    recorded_at     TEXT NOT NULL,
    posted_at       TEXT,
    source          TEXT,
    note            TEXT,
    PRIMARY KEY (org_id, reference)
);
"""


class PostedConflictError(ValueError):
    """Raised when a ledger write collides with an existing row (a
    concurrent post, or a plan gone stale). The safe outcome of any
    collision is that nothing posts."""


# ── entry model ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class ApiLine:
    """One journal line as it will be POSTed."""

    account_id: str
    account_name: str
    debit_or_credit: str  # "debit" | "credit"
    amount: Decimal
    description: str


@dataclass(frozen=True)
class JournalEntry:
    """One journal entry candidate parsed from the reviewed export CSV.
    ``blockers`` non-empty means the entry is unpostable and will only
    ever be reported, never sent."""

    reference: str
    journal_date: str
    lines: tuple[ApiLine, ...]
    blockers: tuple[str, ...]
    row_count: int

    @property
    def postable(self) -> bool:
        return not self.blockers


def entry_content_hash(entry: JournalEntry) -> str:
    """Canonical one-way hash of the entry's financial content: date,
    reference, and the sorted line set (account, side, amount,
    description). Notes and provenance columns are deliberately
    excluded — an LLM confidence string or a re-hosted receipt URL
    changing must not read as a financial conflict."""
    lines = sorted(
        (
            ln.debit_or_credit,
            ln.account_id or ln.account_name,
            f"{ln.amount:.2f}",
            ln.description,
        )
        for ln in entry.lines
    )
    payload = json.dumps(
        {"date": entry.journal_date, "reference": entry.reference, "lines": lines},
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def entries_from_rows(
    rows: list[list[str]], chart: "ChartOfAccounts"
) -> list[JournalEntry]:
    """Group journal CSV rows into entries (all rows sharing one
    ``Reference#``; first-seen order) and resolve each account name to
    its Zoho ``account_id`` via the entity chart — the same resolution
    the COA gate and the export use (`coa_gate._resolve_label`), so the
    poster can never disagree with them about what resolves.

    Every irregularity becomes a named blocker on the entry, never a
    guess and never an exception: placeholder accounts, unresolvable
    names, id-less chart entries, malformed amounts, unbalanced sums,
    date drift within an entry. Blocked entries surface in the plan's
    ``unpostable`` partition."""
    grouped: dict[str, list[list[str]]] = {}
    order: list[str] = []
    for row in rows:
        ref = row[_COL_REFERENCE].strip()
        key = ref or f"(blank reference @ row {len(order) + 1})"
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)

    entries: list[JournalEntry] = []
    for key in order:
        entry_rows = grouped[key]
        blockers: list[str] = []
        ref = entry_rows[0][_COL_REFERENCE].strip()
        if not ref:
            blockers.append("blank Reference# (cannot idempotency-key the entry)")

        dates = {r[_COL_DATE].strip() for r in entry_rows}
        journal_date = entry_rows[0][_COL_DATE].strip()
        if not journal_date:
            blockers.append("blank Date")
        elif len(dates) > 1:
            blockers.append(f"rows disagree on Date: {sorted(dates)}")

        lines: list[ApiLine] = []
        debit_total = Decimal("0")
        credit_total = Decimal("0")
        credit_rows = 0
        for row in entry_rows:
            debit_raw = row[_COL_DEBIT].strip()
            credit_raw = row[_COL_CREDIT].strip()
            if bool(debit_raw) == bool(credit_raw):
                blockers.append(
                    f"row is not exactly one of debit/credit "
                    f"(debit={debit_raw!r}, credit={credit_raw!r})"
                )
                continue
            side = "debit" if debit_raw else "credit"
            if side == "credit":
                credit_rows += 1
            try:
                amount = Decimal(debit_raw or credit_raw)
            except InvalidOperation:
                blockers.append(f"unparseable amount {(debit_raw or credit_raw)!r}")
                continue
            if amount <= 0:
                blockers.append(f"non-positive amount {amount} ({side})")
                continue

            account_ref = row[_COL_ACCOUNT].strip()
            account_id = ""
            if not account_ref:
                blockers.append("blank Account")
            elif account_ref in _PLACEHOLDER_ACCOUNTS or account_ref.startswith(
                _CARD_PLACEHOLDER_PREFIX
            ):
                blockers.append(
                    f"placeholder account {account_ref!r} (review flag, not postable)"
                )
            else:
                # The COA gate's own verdict, not bare resolution: a
                # hand-corrected CSV must not smuggle a DO-NOT-USE /
                # inactive / non-leaf account past the gate the export
                # enforced. types stays soft (the credit side is a
                # credit_card account); scope is the export's concern.
                verdict, acct = classify_account(account_ref, chart)
                if acct is None or verdict is CoaVerdict.UNKNOWN:
                    blockers.append(
                        f"account {account_ref!r} not found in the entity chart"
                    )
                elif verdict in (
                    CoaVerdict.INACTIVE,
                    CoaVerdict.DO_NOT_USE,
                    CoaVerdict.NON_LEAF,
                ):
                    blockers.append(
                        f"account {account_ref!r} is not postable: {verdict.value}"
                    )
                elif not acct.account_id:
                    blockers.append(
                        f"account {account_ref!r} resolved but carries no Zoho "
                        f"account_id (chart not sourced from the Books API?)"
                    )
                else:
                    account_id = acct.account_id

            if side == "debit":
                debit_total += amount
            else:
                credit_total += amount
            lines.append(
                ApiLine(
                    account_id=account_id,
                    account_name=account_ref,
                    debit_or_credit=side,
                    amount=amount,
                    description=row[_COL_DESCRIPTION].strip(),
                )
            )

        if not lines:
            blockers.append("no usable lines")
        if credit_rows != 1:
            blockers.append(
                f"{credit_rows} credit rows (expected exactly 1 balancing credit; "
                f"more than one suggests a duplicated transaction id)"
            )
        if debit_total != credit_total:
            blockers.append(
                f"unbalanced entry: debits {debit_total} != credits {credit_total}"
            )

        entries.append(
            JournalEntry(
                reference=ref,
                journal_date=journal_date,
                lines=tuple(lines),
                blockers=tuple(dict.fromkeys(blockers)),
                row_count=len(entry_rows),
            )
        )
    return entries


def build_journal_payload(entry: JournalEntry, *, status: str = "draft") -> dict:
    """The exact POST body for one entry. ``status`` defaults to
    ``draft`` so even a live post lands reviewable (and deletable) in
    Zoho before it can affect the books; ``published`` requires the
    explicit ``zoho.post.status`` config."""
    line_items = []
    for ln in entry.lines:
        item: dict = {
            "account_id": ln.account_id,
            "amount": float(f"{ln.amount:.2f}"),
            "debit_or_credit": ln.debit_or_credit,
        }
        if ln.description:
            item["description"] = ln.description
        line_items.append(item)
    return {
        "journal_date": entry.journal_date,
        "reference_number": entry.reference,
        "status": status,
        "line_items": line_items,
    }


# ── ledger ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LedgerRow:
    org_id: str
    reference: str
    content_hash: str
    state: str
    zoho_journal_id: str | None
    entry_number: str | None
    recorded_at: str
    posted_at: str | None
    source: str | None
    note: str | None


class PostLedger:
    """SQLite ledger of every journal this tool has (or may have)
    posted, keyed (org_id, reference). Opened per operation as a
    context manager, mirroring `runlog.RunLog`. Timestamps are
    caller-supplied ISO strings; the ledger never calls the clock."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        with closing(self._conn.cursor()) as cur:
            cur.executescript(_SCHEMA)
        self._conn.commit()

    def __enter__(self) -> "PostLedger":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    # ── writes ───────────────────────────────────────────────────────

    def mark_inflight(
        self,
        org_id: str,
        reference: str,
        content_hash: str,
        *,
        now_iso: str,
        source: str | None = None,
    ) -> None:
        """Record the write-ahead intent. Raises `PostedConflictError`
        if ANY row already exists for this (org, reference) — a stale
        plan or a concurrent poster; either way, do not post."""
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO posted_journals "
                    "(org_id, reference, content_hash, state, recorded_at, source) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (org_id, reference, content_hash, _STATE_INFLIGHT, now_iso, source),
                )
        except sqlite3.IntegrityError as exc:
            existing = self.status_for(org_id, reference)
            state = existing.state if existing else "unknown"
            raise PostedConflictError(
                f"ledger already holds {reference} for org {org_id} "
                f"(state {state}); refusing to post"
            ) from exc

    def mark_posted(
        self,
        org_id: str,
        reference: str,
        *,
        zoho_journal_id: str,
        entry_number: str | None,
        now_iso: str,
        content_hash: str,
    ) -> None:
        """UPSERT, never a bare UPDATE: the caller KNOWS a journal
        exists in Zoho, so if the row vanished meanwhile (a concurrent
        --forget / --verify clear), the record is restored rather than
        silently lost — a 0-row UPDATE here would break the "no journal
        without a ledger record" invariant."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO posted_journals "
                "(org_id, reference, content_hash, state, zoho_journal_id, "
                " entry_number, recorded_at, posted_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(org_id, reference) DO UPDATE SET "
                "state = excluded.state, zoho_journal_id = excluded.zoho_journal_id, "
                "entry_number = excluded.entry_number, posted_at = excluded.posted_at, "
                "content_hash = excluded.content_hash, note = NULL",
                (org_id, reference, content_hash, _STATE_POSTED,
                 zoho_journal_id, entry_number, now_iso, now_iso),
            )

    def mark_ambiguous(
        self,
        org_id: str,
        reference: str,
        *,
        now_iso: str,
        content_hash: str,
        note: str | None = None,
        source: str | None = None,
    ) -> None:
        """UPSERT for the same reason as `mark_posted`: the POST left
        this process, so an unresolved record MUST exist even if the
        row was concurrently deleted."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO posted_journals "
                "(org_id, reference, content_hash, state, recorded_at, "
                " posted_at, source, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(org_id, reference) DO UPDATE SET "
                "state = excluded.state, note = excluded.note, "
                "posted_at = excluded.posted_at",
                (org_id, reference, content_hash, _STATE_AMBIGUOUS,
                 now_iso, now_iso, source, note),
            )

    def remove(self, org_id: str, reference: str) -> bool:
        """Delete a row (clean-rejection rollback, or the operator
        ``--forget`` escape hatch). Returns whether a row existed."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM posted_journals WHERE org_id = ? AND reference = ?",
                (org_id, reference),
            )
        return cur.rowcount > 0

    # ── reads ────────────────────────────────────────────────────────

    def status_for(self, org_id: str, reference: str) -> LedgerRow | None:
        cur = self._conn.execute(
            "SELECT * FROM posted_journals WHERE org_id = ? AND reference = ?",
            (org_id, reference),
        )
        row = cur.fetchone()
        return _row_to_ledger(row) if row else None

    def list_rows(self, org_id: str | None = None) -> list[LedgerRow]:
        if org_id is None:
            cur = self._conn.execute(
                "SELECT * FROM posted_journals ORDER BY recorded_at, reference"
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM posted_journals WHERE org_id = ? "
                "ORDER BY recorded_at, reference",
                (org_id,),
            )
        return [_row_to_ledger(r) for r in cur.fetchall()]

    def unresolved(self, org_id: str) -> list[LedgerRow]:
        """Rows whose Zoho-side truth is unknown (inflight/ambiguous) —
        the set `verify_ambiguous` reconciles."""
        cur = self._conn.execute(
            "SELECT * FROM posted_journals WHERE org_id = ? AND state IN (?, ?) "
            "ORDER BY recorded_at, reference",
            (org_id, _STATE_INFLIGHT, _STATE_AMBIGUOUS),
        )
        return [_row_to_ledger(r) for r in cur.fetchall()]

    def other_org_rows(self, reference: str, *, exclude_org: str) -> list[LedgerRow]:
        """Rows for this reference under any OTHER org. A transaction
        belongs to exactly one legal entity, so a hit here is the
        cross-entity double-post smell `plan_post` refuses on."""
        cur = self._conn.execute(
            "SELECT * FROM posted_journals WHERE reference = ? AND org_id != ? "
            "ORDER BY org_id",
            (reference, exclude_org),
        )
        return [_row_to_ledger(r) for r in cur.fetchall()]


def _row_to_ledger(r: sqlite3.Row) -> LedgerRow:
    return LedgerRow(
        org_id=r["org_id"],
        reference=r["reference"],
        content_hash=r["content_hash"],
        state=r["state"],
        zoho_journal_id=r["zoho_journal_id"],
        entry_number=r["entry_number"],
        recorded_at=r["recorded_at"],
        posted_at=r["posted_at"],
        source=r["source"],
        note=r["note"],
    )


# ── plan / execute / verify ──────────────────────────────────────────


# Refusal kinds. The CLI keys waiver decisions on these constants,
# never on message prose (a reworded message must not change policy).
REFUSAL_CONFLICT = "conflict"
REFUSAL_UNRESOLVED = "unresolved"
REFUSAL_UNPOSTABLE = "unpostable"
REFUSAL_CROSS_ORG = "cross-org"


@dataclass(frozen=True)
class PostPlan:
    """The cross-reference-before-upload partition. Only ``to_post``
    may ever reach Zoho, and only when every refusal partition that
    blocks the batch is empty."""

    to_post: tuple[JournalEntry, ...]
    skip_posted: tuple[JournalEntry, ...]
    conflicts: tuple[tuple[JournalEntry, str], ...]
    blocked: tuple[tuple[JournalEntry, str], ...]
    unpostable: tuple[JournalEntry, ...]
    cross_org: tuple[tuple[JournalEntry, str], ...] = ()

    @property
    def batch_refusals(self) -> list[tuple[str, str]]:
        """(kind, reason) pairs the WHOLE batch must refuse on
        (deny-by-default). Skips are fine — they are idempotency
        working as intended."""
        reasons: list[tuple[str, str]] = []
        if self.conflicts:
            reasons.append((
                REFUSAL_CONFLICT,
                f"{len(self.conflicts)} entry(ies) changed since being posted "
                f"(content conflict) — resolve manually, then --forget to re-post",
            ))
        if self.blocked:
            reasons.append((
                REFUSAL_UNRESOLVED,
                f"{len(self.blocked)} entry(ies) in an unresolved ledger state "
                f"(inflight/ambiguous) — run --verify first",
            ))
        if self.cross_org:
            reasons.append((
                REFUSAL_CROSS_ORG,
                f"{len(self.cross_org)} entry(ies) already in the ledger under a "
                f"DIFFERENT org (cross-entity duplicate?) — only --allow-cross-org "
                f"after confirming they are genuinely distinct transactions",
            ))
        if self.unpostable:
            reasons.append((
                REFUSAL_UNPOSTABLE,
                f"{len(self.unpostable)} entry(ies) unpostable (flagged accounts "
                f"/ malformed rows) — fix the export or pass --allow-partial",
            ))
        return reasons


def plan_post(
    entries: list[JournalEntry],
    ledger: PostLedger | None,
    org_id: str,
    *,
    allow_cross_org: bool = False,
) -> PostPlan:
    """Partition candidates against the ledger. ``ledger=None`` means
    the ledger file does not exist yet (nothing was ever posted): every
    postable entry is new. Pure read — plans never write.

    A reference already recorded under ANOTHER org is refused
    (``cross_org``) unless ``allow_cross_org``: a transaction belongs to
    one legal entity, so the same reviewed CSV posted under the other
    entity's config is almost always the cross-entity double-post, not
    a coincidence."""
    to_post: list[JournalEntry] = []
    skip: list[JournalEntry] = []
    conflicts: list[tuple[JournalEntry, str]] = []
    blocked: list[tuple[JournalEntry, str]] = []
    unpostable: list[JournalEntry] = []
    cross_org: list[tuple[JournalEntry, str]] = []

    for entry in entries:
        if not entry.postable:
            unpostable.append(entry)
            continue
        row = ledger.status_for(org_id, entry.reference) if ledger else None
        if row is None:
            elsewhere = (
                ledger.other_org_rows(entry.reference, exclude_org=org_id)
                if ledger
                else []
            )
            if elsewhere and not allow_cross_org:
                other = elsewhere[0]
                cross_org.append((
                    entry,
                    f"reference already {other.state} under org {other.org_id} "
                    f"(recorded {other.recorded_at})",
                ))
            else:
                to_post.append(entry)
        elif row.state == _STATE_POSTED:
            if row.content_hash == entry_content_hash(entry):
                skip.append(entry)
            else:
                conflicts.append(
                    (
                        entry,
                        f"posted {row.posted_at} as journal "
                        f"{row.zoho_journal_id}; content differs now",
                    )
                )
        else:
            blocked.append((entry, f"ledger state {row.state} since {row.recorded_at}"))
    return PostPlan(
        to_post=tuple(to_post),
        skip_posted=tuple(skip),
        conflicts=tuple(conflicts),
        blocked=tuple(blocked),
        unpostable=tuple(unpostable),
        cross_org=tuple(cross_org),
    )


@dataclass(frozen=True)
class PostReport:
    posted: tuple[tuple[str, str], ...]  # (reference, zoho_journal_id)
    rejected: tuple[tuple[str, str], ...]  # (reference, error) — clean 4xx, rolled back
    ambiguous: tuple[tuple[str, str], ...]  # (reference, error) — unknown commit state
    not_attempted: tuple[str, ...]  # references after an abort


def execute_post(
    client: "ZohoClient",
    entries: tuple[JournalEntry, ...],
    ledger: PostLedger,
    org_id: str,
    *,
    now_iso: str,
    status: str = "draft",
    source: str | None = None,
) -> PostReport:
    """Post the plan's ``to_post`` entries one at a time, write-ahead
    intent first. Failure taxonomy (the load-bearing part):

    * Zoho answered with 4xx → the write was rejected, nothing exists
      in Zoho: roll the intent back, report, continue the batch.
    * Auth refresh failed → the POST provably never left this process
      (the token refresh precedes it): roll back and abort with a
      credential error — a KNOWN non-commit, never quarantined.
    * Anything else (network error, 5xx, malformed success) → the
      commit state is UNKNOWN: mark ambiguous and ABORT the batch.
      `verify_ambiguous` is the only path back to postable.
    """
    posted: list[tuple[str, str]] = []
    rejected: list[tuple[str, str]] = []
    ambiguous: list[tuple[str, str]] = []
    not_attempted: list[str] = []
    aborted = False

    for entry in entries:
        if aborted:
            not_attempted.append(entry.reference)
            continue
        if not entry.postable:  # defense in depth; the plan already filtered
            rejected.append((entry.reference, "unpostable entry reached execute"))
            continue
        content_hash = entry_content_hash(entry)
        try:
            ledger.mark_inflight(
                org_id,
                entry.reference,
                content_hash,
                now_iso=now_iso,
                source=source,
            )
        except PostedConflictError as exc:
            # A row appeared between plan and execute: concurrent
            # activity. Deny the rest of the batch — state is moving
            # under us and "post nothing" is the safe outcome.
            ambiguous.append((entry.reference, str(exc)))
            aborted = True
            continue

        try:
            journal = client.create_journal(build_journal_payload(entry, status=status))
        except ZohoAuthError as exc:
            # Raised by the token refresh, which strictly precedes the
            # POST: nothing reached Zoho. Known non-commit.
            ledger.remove(org_id, entry.reference)
            rejected.append((entry.reference, f"auth failed before POST: {exc}"))
            aborted = True
        except ZohoAPIError as exc:
            if exc.status is not None and 400 <= exc.status < 500:
                ledger.remove(org_id, entry.reference)
                rejected.append((entry.reference, str(exc)))
                continue
            ledger.mark_ambiguous(
                org_id, entry.reference, now_iso=now_iso,
                content_hash=content_hash, note=str(exc), source=source,
            )
            ambiguous.append((entry.reference, str(exc)))
            aborted = True
        except Exception as exc:  # unexpected transport/runtime failure
            ledger.mark_ambiguous(
                org_id, entry.reference, now_iso=now_iso,
                content_hash=content_hash, note=str(exc), source=source,
            )
            ambiguous.append((entry.reference, str(exc)))
            aborted = True
        else:
            ledger.mark_posted(
                org_id,
                entry.reference,
                zoho_journal_id=str(journal["journal_id"]),
                entry_number=(
                    str(journal["entry_number"]) if journal.get("entry_number") else None
                ),
                now_iso=now_iso,
                content_hash=content_hash,
            )
            posted.append((entry.reference, str(journal["journal_id"])))

    return PostReport(
        posted=tuple(posted),
        rejected=tuple(rejected),
        ambiguous=tuple(ambiguous),
        not_attempted=tuple(not_attempted),
    )


@dataclass(frozen=True)
class VerifyReport:
    confirmed: tuple[tuple[str, str], ...]  # (reference, zoho_journal_id) — found in Zoho
    cleared: tuple[str, ...]  # explicitly cleared (aged out + operator asked)
    kept: tuple[tuple[str, str], ...]  # (reference, reason) — absent but NOT cleared


def _is_older_than(recorded_at: str, cutoff_iso: str) -> bool:
    """recorded_at strictly before the cutoff. Unparseable timestamps
    count as NOT older (deny-by-default: never age a row out on bad
    data)."""
    try:
        return datetime.fromisoformat(recorded_at) < datetime.fromisoformat(cutoff_iso)
    except ValueError:
        return False


def verify_ambiguous(
    client: "ZohoClient",
    ledger: PostLedger,
    org_id: str,
    *,
    now_iso: str,
    clear_absent_before: str | None = None,
) -> VerifyReport:
    """Reconcile every unresolved (inflight/ambiguous) ledger row
    against Zoho itself: list the org's journals and match by
    ``reference_number``. Found → the post DID commit; record its id.

    Absence is NOT proof of non-commit, so by default an absent row is
    only REPORTED (``kept``), never cleared: the exact failure class
    that creates these rows (client-side timeout, gateway 5xx) can
    commit server-side AFTER any point-in-time listing, and posts are
    drafts, which the unfiltered listing is not documented to include.
    Clearing requires the operator to pass ``clear_absent_before`` (an
    ISO cutoff; the CLI derives it from ``--clear-absent`` + the grace
    window), and even then only rows RECORDED before that cutoff clear —
    a row younger than the grace window can still be racing a late
    server-side commit."""
    unresolved = ledger.unresolved(org_id)
    if not unresolved:
        return VerifyReport(confirmed=(), cleared=(), kept=())

    by_reference: dict[str, dict] = {}
    for journal in client.list_journals():
        ref = str(journal.get("reference_number") or "").strip()
        if ref and ref not in by_reference:
            by_reference[ref] = journal

    confirmed: list[tuple[str, str]] = []
    cleared: list[str] = []
    kept: list[tuple[str, str]] = []
    for row in unresolved:
        found = by_reference.get(row.reference)
        if found is not None and found.get("journal_id"):
            ledger.mark_posted(
                org_id,
                row.reference,
                zoho_journal_id=str(found["journal_id"]),
                entry_number=(
                    str(found["entry_number"]) if found.get("entry_number") else None
                ),
                now_iso=now_iso,
                content_hash=row.content_hash,
            )
            confirmed.append((row.reference, str(found["journal_id"])))
        elif clear_absent_before is None:
            kept.append((
                row.reference,
                "absent from the journals listing; NOT cleared (check the Zoho "
                "UI including Drafts, then re-run with --clear-absent)",
            ))
        elif not _is_older_than(row.recorded_at, clear_absent_before):
            kept.append((
                row.reference,
                f"absent but recorded {row.recorded_at}, inside the grace "
                f"window — a late server-side commit could still land; "
                f"re-verify later",
            ))
        else:
            ledger.remove(org_id, row.reference)
            cleared.append(row.reference)
    return VerifyReport(
        confirmed=tuple(confirmed), cleared=tuple(cleared), kept=tuple(kept)
    )
