"""Chart-of-accounts ingest — BLUEPRINT slice 4.1.

Loads Brisken's Zoho Books chart of accounts so the categorizer can
target real GL accounts (the `zoho_account` leaf per LD-2) and the
journal export can post to them.

Two sources, one `Account` shape:

* **API** — `ChartOfAccounts.from_api(records)` over the dicts
  returned by `ZohoClient.list_chart_of_accounts()` (fields
  `account_id`, `account_name`, `account_code`, `account_type`,
  `parent_account_name`, `is_active`).
* **CSV** — `ChartOfAccounts.from_csv(path)` over a Zoho UI export.
  Column-mapped and tolerant (same idea as the statement parser),
  because Zoho's export column labels vary by org locale.

The real Brisken chart is sensitive client financial data and is NOT
committed to this (public) repo; it is pulled live from the API, or
kept in the separate private brisken-config repo (BLUEPRINT slice
5.3). Tests here run on synthetic accounts only.

`postable_expense_accounts()` is the candidate set fed to the
categorizer / used by the export. It is the intersection of: active,
expense-class account_type, a leaf (Zoho only posts to leaf
accounts), and not a "DO NOT USE" account. Which account_types and
subtrees actually count as card-expense targets for Brisken is a
scoping decision pending with Chris/Dirk; the filter is parameterized
so that decision slots in without a code change.
"""
from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ._common import StatementParseError

# account_type values Zoho assigns to expense-class accounts (per the
# chart-of-accounts API enum). Cost-of-goods and other-expense are
# included by default but may be out of scope for card expenses; the
# caller can narrow via `postable_expense_accounts(types=...)`.
EXPENSE_ACCOUNT_TYPES: tuple[str, ...] = (
    "expense",
    "cost_of_goods_sold",
    "other_expense",
)

# Marker Brisken's accountant uses to retire an account without
# deleting it. Case-insensitive substring match on the account name.
_DO_NOT_USE_MARKER = "do not use"

# Default column map for a Zoho Books chart-of-accounts CSV export.
# Override per-export when the org's locale renames the headers.
_DEFAULT_CSV_COLUMN_MAP: dict[str, str] = {
    "name": "Account Name",
    "code": "Account Code",
    "account_type": "Account Type",
    "parent_name": "Parent Account",
    "is_active": "Status",
}


@dataclass(frozen=True)
class Account:
    """One chart-of-accounts entry.

    `account_id` is the Zoho GL id (the journal POST target); it is
    None for CSV-sourced accounts (the export doesn't carry the id, so
    those feed the file-export path, not direct posting).
    """

    name: str
    code: str
    account_type: str
    parent_name: str | None = None
    is_active: bool = True
    account_id: str | None = None

    @property
    def is_do_not_use(self) -> bool:
        return _DO_NOT_USE_MARKER in self.name.lower()

    @property
    def label(self) -> str:
        """Stable human label for reports + LLM prompts: `code name`."""
        return f"{self.code} {self.name}".strip()


class ChartOfAccounts:
    """A loaded chart of accounts with lookup + filtering helpers."""

    def __init__(self, accounts: Iterable[Account]):
        self.accounts: list[Account] = list(accounts)

    def __len__(self) -> int:
        return len(self.accounts)

    # ── construction ────────────────────────────────────────────────

    @classmethod
    def from_api(cls, records: Iterable[Mapping]) -> "ChartOfAccounts":
        out: list[Account] = []
        for rec in records:
            name = (rec.get("account_name") or "").strip()
            if not name:
                continue
            out.append(
                Account(
                    name=name,
                    code=(rec.get("account_code") or "").strip(),
                    account_type=(rec.get("account_type") or "").strip(),
                    parent_name=(rec.get("parent_account_name") or "").strip() or None,
                    is_active=bool(rec.get("is_active", True)),
                    account_id=(str(rec["account_id"]) if rec.get("account_id") else None),
                )
            )
        return cls(out)

    @classmethod
    def from_csv(
        cls, path: str | Path, column_map: Mapping[str, str] | None = None
    ) -> "ChartOfAccounts":
        """Parse a Zoho UI chart-of-accounts CSV export. Tolerant: a row
        missing a name is skipped, not fatal. A missing `name` column in
        the header IS fatal (nothing to recover)."""
        cmap = {**_DEFAULT_CSV_COLUMN_MAP, **(column_map or {})}
        path = Path(path)
        with path.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            headers = reader.fieldnames or []
            if cmap["name"] not in headers:
                raise StatementParseError(
                    f"chart-of-accounts CSV missing the name column "
                    f"{cmap['name']!r}; found {headers}"
                )
            out: list[Account] = []
            for row in reader:
                name = (row.get(cmap["name"]) or "").strip()
                if not name:
                    continue
                status = (row.get(cmap.get("is_active", ""), "") or "").strip().lower()
                out.append(
                    Account(
                        name=name,
                        code=(row.get(cmap.get("code", ""), "") or "").strip(),
                        account_type=(row.get(cmap.get("account_type", ""), "") or "").strip().lower(),
                        parent_name=(row.get(cmap.get("parent_name", ""), "") or "").strip() or None,
                        is_active=status in ("", "active", "true", "yes", "1"),
                    )
                )
        return cls(out)

    # ── lookup ──────────────────────────────────────────────────────

    def by_code(self, code: str) -> Account | None:
        code = code.strip()
        return next((a for a in self.accounts if a.code == code), None)

    def by_name(self, name: str) -> Account | None:
        name = name.strip().lower()
        return next((a for a in self.accounts if a.name.lower() == name), None)

    def resolve(self, name_or_code: str) -> Account | None:
        """Resolve by exact code first, then exact name. The categorizer
        returns either form; this collapses both to one Account."""
        return self.by_code(name_or_code) or self.by_name(name_or_code)

    # ── filtering ───────────────────────────────────────────────────

    def _parent_names(self) -> set[str]:
        return {a.parent_name for a in self.accounts if a.parent_name}

    def leaf_accounts(self) -> list[Account]:
        """Accounts that are not a parent of any other account. Zoho
        only allows posting to leaf accounts; parent/header accounts are
        roll-ups."""
        parents = self._parent_names()
        return [a for a in self.accounts if a.name not in parents]

    def postable_expense_accounts(
        self,
        *,
        types: Iterable[str] = EXPENSE_ACCOUNT_TYPES,
        include_inactive: bool = False,
        include_do_not_use: bool = False,
    ) -> list[Account]:
        """Candidate accounts for categorization / posting: active +
        expense-class + leaf + not DO-NOT-USE, by default.

        Narrow `types` to scope the categorizer (e.g. drop
        `cost_of_goods_sold` once Chris confirms COGS is journal-only)."""
        type_set = {t.strip().lower() for t in types}
        parents = self._parent_names()
        out: list[Account] = []
        for a in self.accounts:
            if a.account_type.lower() not in type_set:
                continue
            if not include_inactive and not a.is_active:
                continue
            if not include_do_not_use and a.is_do_not_use:
                continue
            if a.name in parents:  # not a leaf
                continue
            out.append(a)
        return out

    def llm_account_labels(self, accounts: Iterable[Account] | None = None) -> list[str]:
        """`code name` labels for the categorizer's chart-of-accounts
        prompt argument. Defaults to the postable-expense candidate set."""
        chosen = list(accounts) if accounts is not None else self.postable_expense_accounts()
        return [a.label for a in chosen]
