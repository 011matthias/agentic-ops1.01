"""One command for the month end: ingest -> guards -> transform -> plan-assert
-> guarded post -> readback, in a single run.

    uv run python -m expense_recon.zoho.reconcile_month \\
        --month YYYY-MM --csv PATH --ledger PATH [--env-file PATH] \\
        [--org ORG_ID] [--card ID --card-name NAME] [--dry-run]

COMPOSITION ONLY. Every stage calls a function that already exists and is
proven (2026-09-23: 41 of 46 July purchases posted to TEST-BTS, read back
field by field, USD 56,340.44 exact). Nothing here re-derives resolution
order, conversion math, the audit envelope or a guard. If a stage looks
like it needs new logic, the module it calls already has it.

1. INGEST       `read_expense_csv` + `group_by_reference` (expense_post):
                the REVIEWED export, never a rebuild.
2. GUARDS       `check_month_occupancy` (occupancy), plus the resume rule
                below. Date and ledger checks are not repeated here; they
                live inside `plan_expense_post` and run because `period`
                is passed.
3. TRANSFORM    `plan_expense_post` against the LIVE chart, with
                statement-currency conversion and the period window.
4. PLAN ASSERT  print the whole plan, then re-plan ONLY the postable
                references (send-by-id) so the poster receives a plan with
                zero refusals. The count and the tie-out total are read
                from that plan, never typed.
5. POST         `execute_expense_post(go=True, expect=N)`, unchanged: it
                write-aheads, releases clean 4xx, aborts on the unknown.
6. READBACK     GET each new id and compare field by field against a
                rebuild through `build_expense_payload` with the same
                flags. Not through `plan_expense_post`, which would now
                refuse every row as `already_in_ledger`.
7. SUMMARY      plain text. Non-zero exit on any verification failure,
                ambiguity, rejection or abort.

**The occupancy resume rule, the one design decision here.** The ledger
knows what THIS tool posted; Zoho knows what anyone posted. When the month
is ALREADY_OCCUPIED and the ledger holds at least one of this batch's
references as posted for this org, the occupied month is at least partly
ours: report it and continue, and let the per-reference `already_in_ledger`
refusal decide what is skipped. When the ledger holds NONE of them, the
rows are somebody else's hand-entered month (Criss's, in production), which
is exactly the case the guard exists to protect: abort. UNVERIFIABLE and
LOCKED_PERIOD always abort.

**Only the sandbox may be touched.** `assert_org` refuses production ids by
name and every other id by not being the sandbox, before a client exists.
Card id, card name and statement currency are per-org config in
`ORG_PROFILES`; a future org needs its own row, and its production mapping
is Brisken's sign-off, not ours.

**A dry run cannot post.** `run_month` returns before `_post_and_read_back`
is on its call path: the post stage is a separate function reached only
from the live branch, and the ledger is only READ until then. The live
branch additionally needs `EXPENSE_RECON_ZOHO_POST=1`, the same
deployment-level switch `zoho_post_cli` requires.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from ..ingest.chart_of_accounts import ChartOfAccounts
from .client import ZohoAPIError, ZohoAuthError, ZohoClient, zoho_config_from_env
from .expense_post import (
    AUDIT_PREFIX,
    DEFAULT_STALE_DAYS,
    MAX_DESCRIPTION_CHARS,
    ExpenseGroup,
    ExpensePlan,
    ExpensePostReport,
    PostRefusal,
    build_expense_payload,
    execute_expense_post,
    group_by_reference,
    plan_expense_post,
    read_expense_csv,
)
from .idempotent import PostLedger
from .occupancy import (
    VERDICT_ALREADY_OCCUPIED,
    VERDICT_CLEAR,
    OccupancyVerdict,
    check_month_occupancy,
    month_bounds,
)
from .orgs import PRODUCTION_ORG_IDS, SANDBOX_ORG_ID

__all__ = [
    "ORG_PROFILES",
    "POST_ENV",
    "REFUSAL_BLANK_REFERENCE",
    "MonthRun",
    "OrgProfile",
    "OrgRefused",
    "ReadbackResult",
    "RunRefused",
    "assert_org",
    "compare_expense",
    "main",
    "resolve_profile",
    "run_month",
]

POST_ENV = "EXPENSE_RECON_ZOHO_POST"

# A postable purchase whose reference is blank cannot be selected by id
# for the send set and would collide in the ledger with every other blank.
# It is refused at the runner level rather than posted.
REFUSAL_BLANK_REFERENCE = "reference_blank"

_CENT = Decimal("0.01")
_STATE_POSTED = "posted"


# ── per-org config ──────────────────────────────────────────────────


@dataclass(frozen=True)
class OrgProfile:
    org_id: str
    label: str
    card_account_id: str  # the payload wants the id
    card_name: str  # occupancy matches by name
    base_currency: str  # the statement currency foreign rows convert to


ORG_PROFILES: dict[str, OrgProfile] = {
    SANDBOX_ORG_ID: OrgProfile(
        org_id=SANDBOX_ORG_ID,
        label="TEST-BTS",
        card_account_id="4369050000000320002",
        card_name="Visa dummy card Matthias",
        base_currency="USD",
    ),
}


class RunRefused(ValueError):
    """The run is refused before anything is read or written."""


class OrgRefused(RunRefused):
    """The org is not the sandbox."""


def assert_org(org_id: str | None) -> str:
    """Refuse everything but the sandbox, production by name first.

    Two checks rather than one so a production id is named as such in the
    refusal, and so an unknown or typo'd id is still refused rather than
    treated as "not production, therefore fine".
    """
    text = str(org_id or "").strip()
    if text in PRODUCTION_ORG_IDS:
        raise OrgRefused(
            f"REFUSING org {text}: production books. Production mapping needs "
            "Brisken's sign-off; until then only the sandbox "
            f"{SANDBOX_ORG_ID} may be touched"
        )
    if text != SANDBOX_ORG_ID:
        raise OrgRefused(
            f"REFUSING org {text!r}: not the TEST-BTS sandbox ({SANDBOX_ORG_ID})"
        )
    return text


def resolve_profile(
    org_id: str | None,
    *,
    card_account_id: str | None = None,
    card_name: str | None = None,
) -> OrgProfile:
    """The org's posting config, after `assert_org`.

    A card override must name BOTH the id and the name: occupancy matches
    on the name and the payload carries the id, and checking one card
    while posting to another would blind the guard.
    """
    org = assert_org(org_id)
    profile = ORG_PROFILES.get(org)
    if profile is None:
        raise RunRefused(
            f"org {org} has no posting profile (card id, card name, statement "
            "currency); add one to ORG_PROFILES deliberately"
        )
    if bool(card_account_id) != bool(card_name):
        raise RunRefused(
            "--card and --card-name go together: occupancy matches the card "
            "by name and the payload posts to it by id"
        )
    if card_account_id and card_name:
        profile = OrgProfile(
            org_id=profile.org_id,
            label=profile.label,
            card_account_id=card_account_id.strip(),
            card_name=card_name.strip(),
            base_currency=profile.base_currency,
        )
    return profile


# ── results ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ReadbackResult:
    reference: str
    expense_id: str
    stored_total: Decimal | None
    problems: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not self.problems


@dataclass
class MonthRun:
    org: OrgProfile
    period: str
    csv_path: Path
    dry_run: bool
    rows: int = 0
    purchases: int = 0
    occupancy: OccupancyVerdict | None = None
    ours_in_ledger: tuple[str, ...] = ()
    plan: ExpensePlan | None = None
    send_plan: ExpensePlan | None = None
    runner_refusals: tuple[PostRefusal, ...] = ()
    report: ExpensePostReport | None = None
    readback: tuple[ReadbackResult, ...] = ()
    ledger_states: dict[str, int] = field(default_factory=dict)
    abort_reason: str | None = None
    exit_code: int = 0

    @property
    def planned_total(self) -> Decimal:
        return self.send_plan.total if self.send_plan is not None else Decimal("0")

    @property
    def stored_total(self) -> Decimal:
        return sum(
            (r.stored_total for r in self.readback if r.stored_total is not None),
            Decimal("0"),
        )

    @property
    def refusals(self) -> tuple[PostRefusal, ...]:
        planned = self.plan.refusals if self.plan is not None else ()
        return tuple(planned) + tuple(self.runner_refusals)


# ── the run ─────────────────────────────────────────────────────────


def _make_client(org_id: str) -> ZohoClient:
    """Module-level so tests can monkeypatch it with a fake."""
    return ZohoClient(zoho_config_from_env(org_id))


def _plan_kwargs(org: OrgProfile, period: str) -> dict:
    """The ONE place the planning flags are set. Stages 3, 4 and 6 all
    take them from here, so the plan, the send plan and the readback
    rebuild cannot disagree about currency policy or the period window."""
    return {
        "org_id": org.org_id,
        "paid_through_account_id": org.card_account_id,
        # Item 184: the id must be the card occupancy checks by name.
        "paid_through_name": org.card_name,
        "base_currency": org.base_currency,
        "convert_foreign_to_base": True,
        "period": period,
        "stale_days": DEFAULT_STALE_DAYS,
    }


def _occupancy_decision(
    verdict: OccupancyVerdict, ours: tuple[str, ...]
) -> str | None:
    """None to continue, otherwise the reason to abort."""
    if verdict.verdict == VERDICT_CLEAR:
        return None
    if verdict.verdict == VERDICT_ALREADY_OCCUPIED:
        if ours:
            return None  # partly ours: per-reference ledger refusals govern
        return (
            f"{verdict.verdict}: {verdict.detail}. The ledger holds none of "
            "this batch's references for this org, so those rows are someone "
            "else's hand-entered month; refusing to post beside them"
        )
    return f"{verdict.verdict}: {verdict.detail}"


def run_month(
    *,
    period: str,
    csv_path: str | Path,
    ledger_path: str | Path,
    org_id: str | None = SANDBOX_ORG_ID,
    card_account_id: str | None = None,
    card_name: str | None = None,
    dry_run: bool = True,
    client_factory: Callable[[str], ZohoClient] | None = None,
    environ: Mapping[str, str] | None = None,
    emit: Callable[[str], None] = print,
) -> MonthRun:
    """The runner. Returns the `MonthRun` with `exit_code` set.

    Raises `RunRefused` (before any read) for a wrong org, a bad card
    override, a malformed period, or a live run without the env gate.
    """
    org = resolve_profile(
        org_id, card_account_id=card_account_id, card_name=card_name
    )
    month_bounds(period)  # a malformed period is a loud ValueError, not a query
    env = os.environ if environ is None else environ
    if not dry_run and env.get(POST_ENV) != "1":
        raise RunRefused(
            f"live run refused: env {POST_ENV}=1 is not set. Re-run with "
            "--dry-run to plan, or set the gate to post"
        )
    factory = client_factory or _make_client
    csv_path = Path(csv_path)
    run = MonthRun(org=org, period=period, csv_path=csv_path, dry_run=dry_run)
    kwargs = _plan_kwargs(org, period)

    emit(f"== reconcile-month {period}  org {org.org_id} ({org.label})  "
         f"{'DRY RUN' if dry_run else 'LIVE'}")
    emit(f"   card {org.card_account_id} {org.card_name!r}  "
         f"statement currency {org.base_currency}")

    # 1. INGEST & GROUP
    rows = read_expense_csv(csv_path)
    # Period-scoped, so the export's per-batch filename fallback
    # (`NNNN__rendered-body.pdf`) cannot collide with another month's.
    groups = group_by_reference(rows, period=period)
    run.rows, run.purchases = len(rows), len(groups)
    splits = sum(1 for g in groups if g.is_split)
    scoped = sum(1 for g in groups if g.was_scoped)
    emit(f"\n[1/7] ingest: {csv_path.name}: {len(rows)} rows -> {len(groups)} "
         f"purchases ({splits} split across accounts, {scoped} synthetic "
         f"reference(s) scoped to {period})")

    client = factory(org.org_id)

    # 2. PRE-FLIGHT GUARDS
    occ = check_month_occupancy(
        client, org_id=org.org_id, period=period, paid_through=org.card_name
    )
    run.occupancy = occ
    emit(f"\n[2/7] occupancy {period}: {occ.verdict}")
    emit(f"      {occ.detail}")
    for line in occ.sample:
        emit(f"        - {line}")

    with PostLedger(ledger_path) as ledger:
        ours = []
        for g in groups:
            if not g.reference:
                continue
            row = ledger.status_for(org.org_id, g.reference)
            if row is not None and row.state == _STATE_POSTED:
                ours.append(g.reference)
        run.ours_in_ledger = tuple(ours)
        emit(f"      ledger holds {len(ours)} of {len(groups)} batch reference(s) "
             f"as posted for org {org.org_id}")
        reason = _occupancy_decision(occ, run.ours_in_ledger)
        if reason is not None:
            run.abort_reason = reason
            emit(f"      ABORT: {reason}")
            run.ledger_states = _ledger_states(ledger, org.org_id)
            return _finish(run, emit)
        if occ.verdict == VERDICT_ALREADY_OCCUPIED:
            emit("      resume: the occupied month is at least partly ours; "
                 "per-reference already_in_ledger refusals govern skipping")

        # 3. TRANSFORM & NORMALIZE
        try:
            chart = ChartOfAccounts.from_api(client.list_chart_of_accounts())
        except (ZohoAPIError, ZohoAuthError) as exc:
            run.abort_reason = f"chart pull failed: {exc}"
            emit(f"\n[3/7] ABORT: {run.abort_reason}")
            run.ledger_states = _ledger_states(ledger, org.org_id)
            return _finish(run, emit)
        emit(f"\n[3/7] chart: {len(chart)} accounts pulled live from org {org.org_id}")
        plan = plan_expense_post(groups, chart, ledger, **kwargs)
        run.plan = plan

        # 4. PLAN ASSERTION (before ANY write)
        emit("\n[4/7] plan")
        _print_plan(plan, groups, chart, org, emit)
        selected = [p.reference for p in plan.postable if p.reference]
        blanks = [p for p in plan.postable if not p.reference]
        run.runner_refusals = tuple(
            PostRefusal(
                reference="",
                reason=REFUSAL_BLANK_REFERENCE,
                detail=(
                    "postable, but its Reference# is blank so it cannot be "
                    "selected by id for the send set; give it a reference"
                ),
            )
            for _ in blanks
        )
        for r in run.runner_refusals:
            emit(f"      REFUSED [{r.reason}] (blank ref): {r.detail}")
        wanted = set(selected)
        send_groups = [g for g in groups if g.reference and g.reference in wanted]
        send_plan = plan_expense_post(send_groups, chart, ledger, **kwargs)
        expected_total = sum(
            (p.total for p in plan.postable if p.reference), Decimal("0")
        )
        _assert_send_plan(send_plan, selected, expected_total)
        run.send_plan = send_plan
        emit(f"      PLAN ASSERT: {len(send_plan.postable)} expense(s), zero "
             f"refusals, tie-out {send_plan.total:.2f} {org.base_currency} "
             "(read from the plan)")

        if dry_run:
            emit("\n[5/7] post: SKIPPED (dry run)")
            emit("[6/7] readback: SKIPPED (dry run)")
            run.ledger_states = _ledger_states(ledger, org.org_id)
            return _finish(run, emit)

        if not send_plan.postable:
            emit("\n[5/7] post: nothing to post")
            emit("[6/7] readback: nothing to read back")
            run.ledger_states = _ledger_states(ledger, org.org_id)
            return _finish(run, emit)

        _post_and_read_back(client, chart, ledger, send_plan, send_groups, run, emit)
        run.ledger_states = _ledger_states(ledger, org.org_id)
    return _finish(run, emit)


def _assert_send_plan(
    send_plan: ExpensePlan, selected: list[str], expected_total: Decimal
) -> None:
    """The plan handed to the poster carries zero refusals, exactly the
    selected references, and the same tie-out total the full plan showed."""
    if send_plan.refusals:
        raise AssertionError(
            f"send plan carries {len(send_plan.refusals)} refusal(s) after "
            "selecting only postable references; the two plans disagree: "
            + "; ".join(f"{r.reference}: {r.reason}" for r in send_plan.refusals)
        )
    got = [p.reference for p in send_plan.postable]
    if got != selected:
        raise AssertionError(
            f"send plan holds {len(got)} expense(s) for {len(selected)} "
            f"selected reference(s): {got} != {selected}"
        )
    if send_plan.total != expected_total:
        raise AssertionError(
            f"send plan tie-out {send_plan.total} != full plan {expected_total}"
        )


def _post_and_read_back(
    client: ZohoClient,
    chart: ChartOfAccounts,
    ledger: PostLedger,
    send_plan: ExpensePlan,
    send_groups: list[ExpenseGroup],
    run: MonthRun,
    emit: Callable[[str], None],
) -> None:
    """The live half. Reached only from `run_month`'s live branch."""
    kwargs = _plan_kwargs(run.org, run.period)
    before = _expense_ids(client)
    emit(f"\n[5/7] post: {len(before)} expense(s) in org before the run")

    report = execute_expense_post(
        client, send_plan, ledger, go=True, expect=len(send_plan.postable)
    )
    run.report = report
    for ref, eid in report.posted:
        emit(f"      POSTED    {ref} -> expense {eid}")
    for ref, msg in report.rejected:
        emit(f"      REJECTED  {ref} (intent released, may retry): {msg}")
    for ref, msg in report.ambiguous:
        emit(f"      AMBIGUOUS {ref} (batch aborted; verify before anything): {msg}")
    if report.aborted:
        emit("      batch ABORTED after an ambiguous result")

    # 6. READBACK
    emit(f"\n[6/7] readback: {len(report.posted)} expense(s) by id")
    by_ref = {g.reference: g for g in send_groups}
    results = []
    for ref, eid in report.posted:
        result = _read_back_one(client, chart, run.org, kwargs, by_ref[ref], eid, before)
        results.append(result)
        if result.clean:
            emit(f"      CLEAN     {ref} -> {eid}  {result.stored_total}")
        else:
            emit(f"      MISMATCH  {ref} -> {eid}")
            for p in result.problems:
                emit(f"          - {p}")
    run.readback = tuple(results)


def _expense_ids(client: ZohoClient) -> frozenset[str]:
    return frozenset(
        str(e.get("expense_id") or "") for e in client.list_expenses()
    ) - {""}


def _read_back_one(
    client: ZohoClient,
    chart: ChartOfAccounts,
    org: OrgProfile,
    kwargs: dict,
    group: ExpenseGroup,
    expense_id: str,
    before: frozenset[str],
) -> ReadbackResult:
    problems: list[str] = []
    if not expense_id:
        return ReadbackResult(group.reference, "", None, ("no expense_id returned",))
    if expense_id in before:
        problems.append("expense id existed BEFORE this run; not a new record")
    # The rebuild goes through build_expense_payload directly. Through
    # plan_expense_post it would refuse every row as already_in_ledger,
    # because the ledger has just recorded them.
    expected = build_expense_payload(group, chart, **kwargs)
    if isinstance(expected, PostRefusal):
        problems.append(f"rebuild refused: {expected.reason}: {expected.detail}")
        return ReadbackResult(group.reference, expense_id, None, tuple(problems))
    try:
        stored = client._get(f"/books/v3/expenses/{expense_id}").get("expense") or {}
    except Exception as exc:  # noqa: BLE001 - any failure is a verification failure
        problems.append(f"GET /expenses/{expense_id} failed: {exc}")
        return ReadbackResult(group.reference, expense_id, None, tuple(problems))
    source_currency = (group.cell("Currency Code") or org.base_currency).upper()
    problems.extend(
        compare_expense(
            stored,
            expected,
            card_account_id=org.card_account_id,
            base_currency=org.base_currency,
            converted=source_currency != org.base_currency.upper(),
        )
    )
    return ReadbackResult(
        group.reference, expense_id, _dec(stored.get("total")), tuple(problems)
    )


# ── comparison ──────────────────────────────────────────────────────


def _dec(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(_CENT)
    except (ArithmeticError, ValueError):
        return None


def _payload_lines(payload: Mapping) -> list[tuple[str, Decimal | None]]:
    if payload.get("line_items"):
        items = payload["line_items"]
    else:
        items = [{"account_id": payload.get("account_id"), "amount": payload.get("amount")}]
    return sorted((str(li.get("account_id") or ""), _dec(li.get("amount"))) for li in items)


def _stored_lines(stored: Mapping) -> list[tuple[str, Decimal | None]]:
    if stored.get("line_items"):
        items = stored["line_items"]
    else:
        items = [
            {
                "account_id": stored.get("account_id"),
                "amount": stored.get("amount", stored.get("total")),
            }
        ]
    return sorted((str(li.get("account_id") or ""), _dec(li.get("amount"))) for li in items)


def _payload_total(payload: Mapping) -> Decimal:
    if "amount" in payload and not payload.get("line_items"):
        return _dec(payload["amount"]) or Decimal("0")
    return sum(
        (_dec(li.get("amount")) or Decimal("0") for li in payload.get("line_items", ())),
        Decimal("0"),
    )


def compare_expense(
    stored: Mapping,
    expected: Mapping,
    *,
    card_account_id: str,
    base_currency: str,
    converted: bool,
) -> list[str]:
    """Field-by-field problems between a stored Zoho expense and the
    payload the builder produces for it. Empty means clean."""
    problems: list[str] = []
    want_total = _payload_total(expected)
    got_total = _dec(stored.get("total"))
    if got_total != want_total:
        problems.append(f"total {got_total} != planned {want_total}")
    if (stored.get("date") or "") != expected.get("date"):
        problems.append(f"date {stored.get('date')!r} != planned {expected.get('date')!r}")
    if (stored.get("reference_number") or "") != expected.get("reference_number"):
        problems.append(
            f"reference {stored.get('reference_number')!r} != planned "
            f"{expected.get('reference_number')!r}"
        )
    if (stored.get("currency_code") or "").upper() != base_currency.upper():
        problems.append(
            f"currency {stored.get('currency_code')!r} != statement currency "
            f"{base_currency}"
        )
    if str(stored.get("paid_through_account_id") or "") != card_account_id:
        problems.append(
            f"paid_through {stored.get('paid_through_account_id')!r} != card "
            f"{card_account_id}"
        )
    want_lines = _payload_lines(expected)
    got_lines = _stored_lines(stored)
    if got_lines != want_lines:
        problems.append(f"lines {got_lines} != planned {want_lines}")
    desc = stored.get("description") or ""
    if AUDIT_PREFIX not in desc:
        problems.append("audit envelope missing from description")
    if converted and "Original:" not in desc:
        problems.append("Original: tag missing on a converted row")
    if len(desc) > MAX_DESCRIPTION_CHARS:
        problems.append(f"description is {len(desc)} chars, Zoho's cap is under 500")
    return problems


# ── output ──────────────────────────────────────────────────────────


def _account_names(chart: ChartOfAccounts) -> dict[str, str]:
    return {a.account_id: a.name for a in chart.accounts if a.account_id}


def _print_plan(
    plan: ExpensePlan,
    groups: list[ExpenseGroup],
    chart: ChartOfAccounts,
    org: OrgProfile,
    emit: Callable[[str], None],
) -> None:
    names = _account_names(chart)
    by_ref = {g.reference: g for g in groups if g.reference}
    emit(f"      POSTABLE: {len(plan.postable)}  total {plan.total:.2f} {org.base_currency}")
    for p in plan.postable:
        payload = p.payload
        lines = payload.get("line_items") or [
            {"account_id": payload.get("account_id"), "amount": payload.get("amount")}
        ]
        accts = ", ".join(
            f"{names.get(str(li.get('account_id')), '?')} {_dec(li.get('amount'))}"
            for li in lines
        )
        group = by_ref.get(p.reference)
        source = (group.cell("Currency Code") if group else "") or org.base_currency
        original = next(
            (part for part in payload.get("description", "").split(" | ")
             if part.startswith("Original: ")),
            "",
        )
        tag = f"  {source}  {original}".rstrip() if original else f"  {source}"
        emit(
            f"        {payload.get('date')}  {p.total:>10.2f} {org.base_currency}  "
            f"{len(lines)} line(s)  ref={p.reference!r}{tag}"
        )
        emit(f"            {accts}")
    by_reason: dict[str, list[PostRefusal]] = {}
    for r in plan.refusals:
        by_reason.setdefault(r.reason, []).append(r)
    emit(f"      REFUSED: {len(plan.refusals)}")
    for reason, items in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        refs = ", ".join(repr(r.reference or "(blank)") for r in items)
        emit(f"        {len(items):>3}  {reason}: {refs}")
        emit(f"             e.g. {items[0].detail[:160]}")


def _ledger_states(ledger: PostLedger, org_id: str) -> dict[str, int]:
    return dict(Counter(r.state for r in ledger.list_rows(org_id)))


def _exit_code(run: MonthRun) -> int:
    if run.abort_reason:
        return 2
    if run.dry_run or run.report is None:
        return 0
    report = run.report
    if report.ambiguous or report.aborted or report.rejected:
        return 1
    if len(run.readback) != len(report.posted):
        return 1
    if any(not r.clean for r in run.readback):
        return 1
    return 0


def _finish(run: MonthRun, emit: Callable[[str], None]) -> MonthRun:
    run.exit_code = _exit_code(run)
    _summary(run, emit)
    return run


def _summary(run: MonthRun, emit: Callable[[str], None]) -> None:
    org = run.org
    emit(f"\n[7/7] SUMMARY  {run.period}  org {org.org_id} ({org.label})  "
         f"{run.csv_path.name}  {'DRY RUN' if run.dry_run else 'LIVE'}")
    emit(f"  rows / purchases       {run.rows} / {run.purchases}")
    if run.occupancy is not None:
        occ = run.occupancy
        emit(f"  occupancy              {occ.verdict}  (ledger holds "
             f"{len(run.ours_in_ledger)} of {run.purchases} batch refs as posted)")
    postable = len(run.send_plan.postable) if run.send_plan is not None else 0
    posted = len(run.report.posted) if run.report is not None else 0
    clean = sum(1 for r in run.readback if r.clean)
    emit(f"  postable               {postable}")
    emit(f"  posted                 {posted}")
    if run.dry_run:
        emit("  verified clean         readback: SKIPPED (dry run)")
    else:
        emit(f"  verified clean         {clean} / {posted}")
    if run.report is not None:
        emit(f"  rejected / ambiguous   {len(run.report.rejected)} / "
             f"{len(run.report.ambiguous)}"
             + ("  (batch aborted)" if run.report.aborted else ""))
    refusals = run.refusals
    emit(f"  refusals               {len(refusals)}")
    by_reason: dict[str, list[str]] = {}
    for r in refusals:
        by_reason.setdefault(r.reason, []).append(r.reference or "(blank)")
    for reason, refs in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        emit(f"    {len(refs):>3}  {reason}: {', '.join(refs)}")
    emit(f"  planned total          {run.planned_total:.2f} {org.base_currency}")
    if run.dry_run or run.report is None:
        emit("  stored total           n/a")
    else:
        verdict = "MATCH" if run.stored_total == run.planned_total else "MISMATCH"
        emit(f"  stored total           {run.stored_total:.2f} {org.base_currency}  {verdict}")
    states = ", ".join(f"{k} {v}" for k, v in sorted(run.ledger_states.items())) or "empty"
    emit(f"  ledger states (org)    {states}")
    if run.abort_reason:
        emit(f"  ABORTED                {run.abort_reason}")
    emit(f"  exit                   {run.exit_code}")


# ── CLI ─────────────────────────────────────────────────────────────


def _load_env_file(path: Path) -> None:
    """KEY=VALUE lines into the process env, never overriding what is
    already set. Same parse the 2026-09-23 rehearsal scripts used."""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m expense_recon.zoho.reconcile_month",
        description=(
            "Post one reviewed month into Zoho Books in a single run: ingest, "
            "guards, transform, plan-assert, guarded post, readback. Sandbox "
            f"org {SANDBOX_ORG_ID} only."
        ),
    )
    parser.add_argument("--month", required=True, help="Period YYYY-MM.")
    parser.add_argument(
        "--csv", required=True, type=Path,
        help="The REVIEWED expense export CSV (post the reviewed artifact, never a rebuild).",
    )
    parser.add_argument(
        "--ledger", required=True, type=Path,
        help="The durable post ledger (sqlite). The ledger is part of the guard; "
        "a fresh one would plan an already-posted month as new.",
    )
    parser.add_argument(
        "--env-file", type=Path, default=None,
        help="KEY=VALUE file with the Zoho credentials (gitignored context/.env). "
        "Omit to use the process environment.",
    )
    parser.add_argument(
        "--org", default=SANDBOX_ORG_ID,
        help=f"Zoho org id. Anything but the sandbox {SANDBOX_ORG_ID} is refused.",
    )
    parser.add_argument("--card", default=None, help="Paid-through card account id (override).")
    parser.add_argument("--card-name", default=None, help="Paid-through card NAME (override; goes with --card).")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Stages 1-4 only: read, guard, plan, assert. Posts nothing, mutates nothing.",
    )
    args = parser.parse_args(argv)

    if args.env_file is not None:
        if not args.env_file.exists():
            print(f"ERROR: env file not found: {args.env_file}", file=sys.stderr)
            return 2
        _load_env_file(args.env_file)

    try:
        run = run_month(
            period=args.month,
            csv_path=args.csv,
            ledger_path=args.ledger,
            org_id=args.org,
            card_account_id=args.card,
            card_name=args.card_name,
            dry_run=args.dry_run,
        )
    except RunRefused as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (ValueError, ZohoAuthError, ZohoAPIError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except AssertionError as exc:
        print(f"PLAN ASSERTION FAILED (nothing posted): {exc}", file=sys.stderr)
        return 2
    return run.exit_code


if __name__ == "__main__":
    sys.exit(main())
