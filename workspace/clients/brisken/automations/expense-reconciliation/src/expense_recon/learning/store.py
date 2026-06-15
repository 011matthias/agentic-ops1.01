"""Cross-run learning store — Phase 2 (BLUEPRINT slice 9).

A single opt-in SQLite database (default `learning.sqlite` under the web
app's data dir) that remembers the reviewer's confirmed decisions so next
month's pile is smaller. Three tables, every key scoped by
`legal_entity_id` (multi-entity hard requirement — no cross-entity bleed):

* `merchant_category`  a confirmed vendor -> category (+ Zoho account)
                       mapping. Consulted in the Sort pass (PR 2b) to
                       promote a known merchant to Tier-1 instead of
                       re-paying for an LLM call / landing Tier-2.
* `vendor_alias`       a confirmed (statement-vendor, receipt-vendor)
                       equivalence, e.g. "MEGA CENTE CONSTR" == the full
                       Brazilian name. Strengthens the token-similarity
                       tie-break in Match (PR 2c).
* `merchant_fx`        observed implied FX rates per merchant + currency
                       pair, kept as raw samples so min/mean/max refine
                       the band score in Judge (PR 2c) WITHOUT widening
                       the LD-5 bands themselves.

Vendor keys are normalized with the SAME function the matcher uses
(`matching.deterministic._normalize`), imported here so a learned key can
never drift out of alignment with a consult-time lookup. Conflict policy
is latest-wins with an audit trail (`decision_count` / `confirmed_count` /
`last_*_at`): correct for a single-user tool, no quorum ceremony at n=1.

Nothing reads this store yet (PR 2a is capture-only); the consult paths
land in PR 2b / 2c, and the inspect / forget / reset escape hatch in PR
2d — deliberately before any learned data can influence output. The store
is opened per operation as a context manager, mirroring `web.store.RunStore`
and `runlog.RunLog`; SQLite's default locking suffices for one user.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

# Single source of truth for vendor normalization. Importing the matcher's
# own helper (rather than re-implementing it) guarantees a key written here
# matches the key a future consult computes from the same vendor string.
from ..matching.deterministic import _normalize as normalize_vendor

__all__ = [
    "LearningStore",
    "MerchantCategory",
    "VendorAlias",
    "MerchantFx",
    "normalize_vendor",
]


@dataclass(frozen=True)
class MerchantCategory:
    legal_entity_id: str
    vendor_norm: str
    category: str | None
    zoho_account: str | None
    decision_count: int
    last_confirmed_at: str | None
    source_run: str | None


@dataclass(frozen=True)
class VendorAlias:
    legal_entity_id: str
    stmt_vendor_norm: str
    receipt_vendor_norm: str
    confirmed_count: int
    last_confirmed_at: str | None
    source_run: str | None


@dataclass(frozen=True)
class MerchantFx:
    legal_entity_id: str
    vendor_norm: str
    from_ccy: str
    to_ccy: str
    samples: tuple[Decimal, ...]
    last_seen_at: str | None
    source_run: str | None

    @property
    def count(self) -> int:
        return len(self.samples)

    @property
    def mean(self) -> Decimal | None:
        if not self.samples:
            return None
        return sum(self.samples, Decimal("0")) / Decimal(len(self.samples))

    @property
    def min(self) -> Decimal | None:
        return min(self.samples) if self.samples else None

    @property
    def max(self) -> Decimal | None:
        return max(self.samples) if self.samples else None


class LearningStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def __enter__(self) -> "LearningStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS merchant_category (
                legal_entity_id   TEXT NOT NULL,
                vendor_norm       TEXT NOT NULL,
                category          TEXT,
                zoho_account      TEXT,
                decision_count    INTEGER NOT NULL DEFAULT 1,
                last_confirmed_at TEXT,
                source_run        TEXT,
                PRIMARY KEY (legal_entity_id, vendor_norm)
            );
            CREATE TABLE IF NOT EXISTS vendor_alias (
                legal_entity_id     TEXT NOT NULL,
                stmt_vendor_norm    TEXT NOT NULL,
                receipt_vendor_norm TEXT NOT NULL,
                confirmed_count     INTEGER NOT NULL DEFAULT 1,
                last_confirmed_at   TEXT,
                source_run          TEXT,
                PRIMARY KEY (legal_entity_id, stmt_vendor_norm, receipt_vendor_norm)
            );
            CREATE TABLE IF NOT EXISTS merchant_fx (
                legal_entity_id TEXT NOT NULL,
                vendor_norm     TEXT NOT NULL,
                from_ccy        TEXT NOT NULL,
                to_ccy          TEXT NOT NULL,
                samples         TEXT NOT NULL DEFAULT '[]',
                last_seen_at    TEXT,
                source_run      TEXT,
                PRIMARY KEY (legal_entity_id, vendor_norm, from_ccy, to_ccy)
            );
            """
        )
        self.conn.commit()

    # -- merchant_category ------------------------------------------------

    def record_merchant_category(
        self,
        legal_entity_id: str,
        vendor_norm: str,
        category: str | None,
        zoho_account: str | None,
        now_iso: str,
        source_run: str | None,
    ) -> None:
        """Upsert a confirmed vendor -> category mapping. Latest-wins on the
        category/account; `decision_count` accumulates as the audit trail."""
        self.conn.execute(
            "INSERT INTO merchant_category (legal_entity_id, vendor_norm, "
            "category, zoho_account, decision_count, last_confirmed_at, source_run) "
            "VALUES (?, ?, ?, ?, 1, ?, ?) "
            "ON CONFLICT(legal_entity_id, vendor_norm) DO UPDATE SET "
            "category = excluded.category, "
            "zoho_account = excluded.zoho_account, "
            "decision_count = merchant_category.decision_count + 1, "
            "last_confirmed_at = excluded.last_confirmed_at, "
            "source_run = excluded.source_run",
            (legal_entity_id, vendor_norm, category, zoho_account, now_iso, source_run),
        )
        self.conn.commit()

    def get_merchant_category(
        self, legal_entity_id: str, vendor_norm: str
    ) -> MerchantCategory | None:
        row = self.conn.execute(
            "SELECT * FROM merchant_category WHERE legal_entity_id = ? "
            "AND vendor_norm = ?",
            (legal_entity_id, vendor_norm),
        ).fetchone()
        return self._row_to_category(row) if row else None

    def all_merchant_categories(
        self, legal_entity_id: str | None = None
    ) -> list[MerchantCategory]:
        if legal_entity_id is None:
            rows = self.conn.execute(
                "SELECT * FROM merchant_category ORDER BY legal_entity_id, vendor_norm"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM merchant_category WHERE legal_entity_id = ? "
                "ORDER BY vendor_norm",
                (legal_entity_id,),
            ).fetchall()
        return [self._row_to_category(r) for r in rows]

    @staticmethod
    def _row_to_category(row: sqlite3.Row) -> MerchantCategory:
        return MerchantCategory(
            legal_entity_id=row["legal_entity_id"],
            vendor_norm=row["vendor_norm"],
            category=row["category"],
            zoho_account=row["zoho_account"],
            decision_count=row["decision_count"],
            last_confirmed_at=row["last_confirmed_at"],
            source_run=row["source_run"],
        )

    # -- vendor_alias -----------------------------------------------------

    def record_vendor_alias(
        self,
        legal_entity_id: str,
        stmt_vendor_norm: str,
        receipt_vendor_norm: str,
        now_iso: str,
        source_run: str | None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO vendor_alias (legal_entity_id, stmt_vendor_norm, "
            "receipt_vendor_norm, confirmed_count, last_confirmed_at, source_run) "
            "VALUES (?, ?, ?, 1, ?, ?) "
            "ON CONFLICT(legal_entity_id, stmt_vendor_norm, receipt_vendor_norm) "
            "DO UPDATE SET "
            "confirmed_count = vendor_alias.confirmed_count + 1, "
            "last_confirmed_at = excluded.last_confirmed_at, "
            "source_run = excluded.source_run",
            (legal_entity_id, stmt_vendor_norm, receipt_vendor_norm, now_iso, source_run),
        )
        self.conn.commit()

    def get_vendor_aliases(
        self, legal_entity_id: str | None = None
    ) -> list[VendorAlias]:
        if legal_entity_id is None:
            rows = self.conn.execute(
                "SELECT * FROM vendor_alias ORDER BY legal_entity_id, stmt_vendor_norm"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM vendor_alias WHERE legal_entity_id = ? "
                "ORDER BY stmt_vendor_norm",
                (legal_entity_id,),
            ).fetchall()
        return [
            VendorAlias(
                legal_entity_id=r["legal_entity_id"],
                stmt_vendor_norm=r["stmt_vendor_norm"],
                receipt_vendor_norm=r["receipt_vendor_norm"],
                confirmed_count=r["confirmed_count"],
                last_confirmed_at=r["last_confirmed_at"],
                source_run=r["source_run"],
            )
            for r in rows
        ]

    # -- merchant_fx ------------------------------------------------------

    def record_merchant_fx(
        self,
        legal_entity_id: str,
        vendor_norm: str,
        from_ccy: str,
        to_ccy: str,
        implied_rate: Decimal,
        now_iso: str,
        source_run: str | None,
    ) -> None:
        """Append one observed implied rate to a merchant's FX history.

        Raw samples are kept (not a running mean) so the consult layer can
        derive min/mean/max and so a bad sample stays individually visible /
        forgettable. Read-modify-write because SQLite cannot append to a
        JSON list inside an upsert; volumes are a handful per merchant."""
        existing = self.conn.execute(
            "SELECT samples FROM merchant_fx WHERE legal_entity_id = ? "
            "AND vendor_norm = ? AND from_ccy = ? AND to_ccy = ?",
            (legal_entity_id, vendor_norm, from_ccy, to_ccy),
        ).fetchone()
        samples = json.loads(existing["samples"]) if existing else []
        samples.append(str(implied_rate))
        self.conn.execute(
            "INSERT INTO merchant_fx (legal_entity_id, vendor_norm, from_ccy, "
            "to_ccy, samples, last_seen_at, source_run) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(legal_entity_id, vendor_norm, from_ccy, to_ccy) DO UPDATE SET "
            "samples = excluded.samples, "
            "last_seen_at = excluded.last_seen_at, "
            "source_run = excluded.source_run",
            (
                legal_entity_id,
                vendor_norm,
                from_ccy,
                to_ccy,
                json.dumps(samples),
                now_iso,
                source_run,
            ),
        )
        self.conn.commit()

    def get_merchant_fx(
        self, legal_entity_id: str, vendor_norm: str
    ) -> list[MerchantFx]:
        rows = self.conn.execute(
            "SELECT * FROM merchant_fx WHERE legal_entity_id = ? AND vendor_norm = ? "
            "ORDER BY from_ccy, to_ccy",
            (legal_entity_id, vendor_norm),
        ).fetchall()
        return [self._row_to_fx(r) for r in rows]

    def all_merchant_fx(
        self, legal_entity_id: str | None = None
    ) -> list[MerchantFx]:
        if legal_entity_id is None:
            rows = self.conn.execute(
                "SELECT * FROM merchant_fx ORDER BY legal_entity_id, vendor_norm"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM merchant_fx WHERE legal_entity_id = ? ORDER BY vendor_norm",
                (legal_entity_id,),
            ).fetchall()
        return [self._row_to_fx(r) for r in rows]

    @staticmethod
    def _row_to_fx(row: sqlite3.Row) -> MerchantFx:
        return MerchantFx(
            legal_entity_id=row["legal_entity_id"],
            vendor_norm=row["vendor_norm"],
            from_ccy=row["from_ccy"],
            to_ccy=row["to_ccy"],
            samples=tuple(Decimal(s) for s in json.loads(row["samples"])),
            last_seen_at=row["last_seen_at"],
            source_run=row["source_run"],
        )
