"""Period-scoped synthetic references, and the legacy ledger key.

The export writes `ref = detected_reference or document_id`, so a receipt
whose invoice number was never read falls back to its archive filename.
A mail-rendered receipt's filename is `NNNN__rendered-body.pdf`, where
NNNN is only its index within that batch, and those indexes restart every
month. July's `0003__rendered-body.pdf` is Konsultancy Finance EUR
15,972.00; August's is OpenAI USD 80.04. The ledger keys on
(org, reference), so August's OpenAI purchase read as already posted and
the other three August fallbacks would have posted under references that
collide with every later month.

Two properties are pinned here, and the second is the one with teeth: a
purchase posted BEFORE scoping existed is recorded under the raw
filename, so the ledger must still recognise it or the fix would make
July postable a second time.
"""
from __future__ import annotations

import pytest

from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS
from expense_recon.zoho.expense_post import (
    REFUSAL_LEDGER,
    group_by_reference,
    is_synthetic_reference,
    migrate_legacy_synthetic_references,
    period_scoped_reference,
    plan_expense_post,
)
from expense_recon.zoho.idempotent import PostLedger
from expense_recon.zoho.orgs import SANDBOX_ORG_ID

from tests.test_zoho_reconcile_month import CHART, SOFTWARE  # noqa: F401

from expense_recon.ingest.chart_of_accounts import ChartOfAccounts

ORG = SANDBOX_ORG_ID
CARD = "4369050000000320002"
_COA = ChartOfAccounts.from_api(CHART)


def _row(ref, **over):
    row = dict.fromkeys(EXPENSE_COLUMNS, "")
    row.update(
        {
            "Expense Date": "2026-08-20",
            "Expense Account": "Software & Subscriptions",
            "Expense Amount": "80.04",
            "Currency Code": "USD",
            "Reference#": ref,
            "Vendor": "OpenAI",
        }
    )
    row.update(over)
    return row


# ── the detector, both directions ───────────────────────────────────


@pytest.mark.parametrize(
    "ref",
    [
        "0003__rendered-body.pdf",  # the real one, July and August both
        "0001__rendered-body.pdf",
        "12__receipt.PDF",
        "0007__scan.jpeg",
        "0002__photo.heic",
        "0004__body.html",
    ],
)
def test_filename_fallbacks_are_synthetic(ref):
    assert is_synthetic_reference(ref)


@pytest.mark.parametrize(
    "ref",
    [
        # Every one of these is a REAL July or August reference. A
        # detector that scoped any of them would rewrite an issuer's own
        # number and break the tie back to the vendor's document.
        "H_46243348",
        "IUS25300",
        "TYP260723-7110-37202",
        "028-4596654-9227559",
        "Beleg-Nr. 2742",
        "ch_3TpsgGJFr6CCHwIi1OLfWQ9H",
        "NFC-e 270745 Serie 411",
        "2251 6044 9324",
        "DZ9BH3VA0037",
        "ENLLLY23 0007",
        "2611-9785-2578",
        "50102456463",
        "",
        # Shape-adjacent but not the fallback: digits without the double
        # underscore, and a double underscore without an extension.
        "0003-rendered-body.pdf",
        "0003__rendered-body",
        "invoice__final.pdf",
    ],
)
def test_real_references_are_not_synthetic(ref):
    assert not is_synthetic_reference(ref)


def test_scoping_only_touches_synthetic_references():
    assert (
        period_scoped_reference("0003__rendered-body.pdf", "2026-08")
        == "2026-08_0003__rendered-body.pdf"
    )
    assert period_scoped_reference("H_46243348", "2026-08") == "H_46243348"
    assert period_scoped_reference("", "2026-08") == ""


def test_without_a_period_nothing_is_scoped():
    """Opt-in, so every existing caller keeps its behaviour."""
    assert (
        period_scoped_reference("0003__rendered-body.pdf", None)
        == "0003__rendered-body.pdf"
    )


# ── grouping ────────────────────────────────────────────────────────


def test_grouping_scopes_the_synthetic_reference():
    (g,) = group_by_reference([_row("0003__rendered-body.pdf")], period="2026-08")
    assert g.reference == "2026-08_0003__rendered-body.pdf"
    assert g.raw_reference == "0003__rendered-body.pdf"
    assert g.was_scoped


def test_the_two_months_no_longer_collide():
    """The whole point: one string, two purchases, two keys."""
    jul = group_by_reference([_row("0003__rendered-body.pdf")], period="2026-07")
    aug = group_by_reference([_row("0003__rendered-body.pdf")], period="2026-08")
    assert jul[0].reference != aug[0].reference


def test_a_real_reference_is_untouched_by_grouping():
    (g,) = group_by_reference([_row("H_46243348")], period="2026-08")
    assert g.reference == "H_46243348"
    assert not g.was_scoped


def test_a_split_still_groups_after_scoping():
    """Indexes are unique WITHIN a batch, so scoping must not break the
    split that shares one filename across two account rows."""
    rows = [
        _row("0005__rendered-body.pdf", **{"Expense Amount": "10.00"}),
        _row("0005__rendered-body.pdf", **{"Expense Amount": "5.50"}),
    ]
    (g,) = group_by_reference(rows, period="2026-08")
    assert g.is_split and len(g.rows) == 2
    assert g.reference == "2026-08_0005__rendered-body.pdf"


def test_blank_references_still_never_merge():
    groups = group_by_reference([_row(""), _row("")], period="2026-08")
    assert len(groups) == 2
    assert all(g.reference == "" for g in groups)


# ── the legacy ledger key, the double-post guard ────────────────────


def _plan(groups, ledger, period="2026-08"):
    return plan_expense_post(
        groups, _COA, ledger, org_id=ORG, paid_through_account_id=CARD,
        base_currency="USD", period=period,
    )


JULY_ID = "4369050000000377001"
JULY_DATE = "2026-07-30"  # Konsultancy Finance, the real July 0003


class StoredClient:
    """Answers `GET /expenses/{id}` for the July row, and nothing else.

    The migration reads the ledger row's expense back to confirm WHICH
    purchase it records, so the fake has to carry that record; a fake
    that returned a match for any id would let the ambiguity through."""

    def __init__(self, records=None):
        self.records = records if records is not None else {
            JULY_ID: {"expense_id": JULY_ID, "date": JULY_DATE, "total": 18564.0}
        }
        self.reads: list[str] = []

    def _get(self, path, params=None):
        eid = path.rsplit("/", 1)[1]
        self.reads.append(eid)
        if eid not in self.records:
            raise RuntimeError(f"404 no expense {eid}")
        return {"code": 0, "expense": dict(self.records[eid])}


def _legacy_ledger(tmp_path):
    """The REAL shape: July posted `0003__rendered-body.pdf` under the
    bare filename, before scoping existed."""
    ledger = PostLedger(tmp_path / "l.db")
    ledger.mark_posted(
        ORG, "0003__rendered-body.pdf",
        zoho_journal_id=JULY_ID, entry_number=None,
        now_iso="2026-09-23T09:39:55+00:00", content_hash="h",
    )
    return ledger


def _july_group():
    return group_by_reference(
        [_row("0003__rendered-body.pdf", **{"Expense Date": JULY_DATE})],
        period="2026-07",
    )


def test_a_read_time_fallback_could_not_have_worked(tmp_path):
    """Why this is a migration and not a lookup.

    The first attempt fell back to the raw key when the scoped key
    missed. From August that fallback finds JULY's row, which is the
    exact collision scoping exists to remove, and the bare key carries no
    month so nothing at read time can tell the two apart. Pinned as a
    property of the DATA rather than of the discarded code: one bare key,
    two months, both of which legitimately produce it."""
    jul = group_by_reference([_row("0003__rendered-body.pdf")], period="2026-07")
    aug = group_by_reference([_row("0003__rendered-body.pdf")], period="2026-08")
    assert jul[0].raw_reference == aug[0].raw_reference
    assert jul[0].reference != aug[0].reference


def test_before_migration_july_would_double_post(tmp_path):
    """The hazard the migration closes, stated as a test so the migration
    cannot be quietly dropped: July's own key no longer matches."""
    with _legacy_ledger(tmp_path) as ledger:
        plan = _plan(_july_group(), ledger, period="2026-07")
        assert len(plan.postable) == 1  # would post a second time


def test_migration_moves_the_row_onto_the_scoped_key(tmp_path):
    client = StoredClient()
    with _legacy_ledger(tmp_path) as ledger:
        groups = _july_group()
        moves = migrate_legacy_synthetic_references(
            ledger, ORG, groups, client=client, go=True
        )
        assert moves == [
            ("0003__rendered-body.pdf", "2026-07_0003__rendered-body.pdf")
        ]
        moved = ledger.status_for(ORG, "2026-07_0003__rendered-body.pdf")
        assert moved is not None and moved.zoho_journal_id == JULY_ID
        assert ledger.status_for(ORG, "0003__rendered-body.pdf") is None

        plan = _plan(groups, ledger, period="2026-07")
        assert plan.postable == ()
        assert plan.refusals[0].reason == REFUSAL_LEDGER


def test_migration_is_a_dry_run_without_go(tmp_path):
    with _legacy_ledger(tmp_path) as ledger:
        moves = migrate_legacy_synthetic_references(
            ledger, ORG, _july_group(), client=StoredClient()
        )
        assert len(moves) == 1
        assert ledger.status_for(ORG, "0003__rendered-body.pdf") is not None
        assert ledger.status_for(ORG, "2026-07_0003__rendered-body.pdf") is None


def test_migration_run_from_august_leaves_julys_row_alone(tmp_path):
    """The failure the first draft actually had, now pinned.

    August's 0003 is OpenAI on 2026-08-20; the ledger row is July's
    Konsultancy purchase on 2026-07-30. Re-keying it to `2026-08_...`
    would lose July's record AND block August, so the stored expense's
    date is what decides, not the export being processed."""
    client = StoredClient()
    with _legacy_ledger(tmp_path) as ledger:
        groups = group_by_reference(
            [_row("0003__rendered-body.pdf", **{"Expense Date": "2026-08-20"})],
            period="2026-08",
        )
        moves = migrate_legacy_synthetic_references(
            ledger, ORG, groups, client=client, go=True
        )
        assert moves == []
        assert client.reads == [JULY_ID], "the stored expense must be consulted"
        assert ledger.status_for(ORG, "0003__rendered-body.pdf") is not None
        plan = _plan(groups, ledger, period="2026-08")
        assert len(plan.postable) == 1, "August's OpenAI row must be postable"


def test_migration_leaves_a_row_it_cannot_read(tmp_path):
    """Deny by default: an unreadable expense is not a confirmed match."""
    with _legacy_ledger(tmp_path) as ledger:
        moves = migrate_legacy_synthetic_references(
            ledger, ORG, _july_group(), client=StoredClient(records={}), go=True
        )
        assert moves == []
        assert ledger.status_for(ORG, "0003__rendered-body.pdf") is not None


def test_migration_is_idempotent(tmp_path):
    client = StoredClient()
    with _legacy_ledger(tmp_path) as ledger:
        groups = _july_group()
        migrate_legacy_synthetic_references(
            ledger, ORG, groups, client=client, go=True
        )
        assert migrate_legacy_synthetic_references(
            ledger, ORG, groups, client=client, go=True
        ) == []


def test_migration_refuses_an_unresolved_row(tmp_path):
    """An inflight row's Zoho-side truth is unknown; renaming it would
    hide it from verify_ambiguous."""
    with PostLedger(tmp_path / "l.db") as ledger:
        ledger.mark_inflight(ORG, "0003__rendered-body.pdf", "h", now_iso="t")
        with pytest.raises(ValueError, match="not\\s+posted|--verify"):
            migrate_legacy_synthetic_references(
                ledger, ORG, _july_group(), client=StoredClient(), go=True
            )
        assert ledger.status_for(ORG, "0003__rendered-body.pdf") is not None


def test_migration_refuses_a_posted_row_with_no_expense_id(tmp_path):
    with PostLedger(tmp_path / "l.db") as ledger:
        ledger.mark_posted(ORG, "0003__rendered-body.pdf", zoho_journal_id="",
                           entry_number=None, now_iso="t", content_hash="h")
        with pytest.raises(ValueError, match="records no expense id"):
            migrate_legacy_synthetic_references(
                ledger, ORG, _july_group(), client=StoredClient(), go=True
            )


def test_migration_ignores_real_references(tmp_path):
    client = StoredClient()
    with PostLedger(tmp_path / "l.db") as ledger:
        ledger.mark_posted(ORG, "H_46243348", zoho_journal_id="J",
                           entry_number=None, now_iso="t", content_hash="h")
        groups = group_by_reference([_row("H_46243348")], period="2026-07")
        assert migrate_legacy_synthetic_references(
            ledger, ORG, groups, client=client, go=True
        ) == []
        assert ledger.status_for(ORG, "H_46243348") is not None
        assert client.reads == [], "a real reference must not cost a read"
