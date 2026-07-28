"""`expense-recon zoho-post` — the guarded slice-4b posting CLI (BLUEPRINT 4.8).

Posts the REVIEWED journal export CSV to Zoho Books as draft journal
entries, cross-referencing the 4.8 idempotency ledger before anything
is uploaded. The default run is a DRY RUN: it prints the full
plan (post / skip / conflict / blocked / unpostable) plus a gate
readiness report and sends nothing. ``--go`` is required to post, and
``--go`` only fires when every gate passes:

1. config ``zoho.post.enabled: true`` (default false — the whole path
   is OFF unless a config deliberately turns it on)
2. env ``EXPENSE_RECON_ZOHO_POST=1`` (a second, deployment-level switch;
   neither the Fly app nor any dev shell sets it by default)
3. the target org is on the hard allowlist (the two provisioned
   Brisken orgs; widening it is an explicit PR-reviewed config change)
4. ``--expect N`` (when given) matches the to-post count exactly
5. the plan has no conflicts, no unresolved ledger states, and no
   unpostable entries (``--allow-partial`` may waive ONLY the
   unpostable refusal; conflicts and unresolved states always refuse)

Config (extends the run config's ``zoho:`` block)::

    "zoho": {
        ...,
        "post": {
            "enabled": true,                 // default false
            "ledger_path": "post-ledger.sqlite",  // relative to the config
            "status": "draft",               // journal status; default draft
            "org_allowlist": ["822741658"]   // optional; defaults to the
                                             // two provisioned Brisken orgs
        }
    }

The entity org and chart come from the same ``coa_validation`` block the
COA gate uses (``org_id`` + ``chart_path``), so the poster can never
target a different org than the one the export was validated against.
Credentials come from the environment via the same derivation
`learning_cli` uses (ZOHO_BOOKS_REFRESH_TOKEN wins, ZOHO_DC domains) —
never from the config file.

Actions: default = plan/post a ``--csv`` export; ``--verify`` reconciles
unresolved ledger rows against Zoho; ``--ledger`` lists the ledger;
``--forget REF`` releases one reference (operator escape hatch, e.g.
after a deliberate Zoho-side delete).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from datetime import timedelta

from .coa_gate import load_entity_chart
from .learning_cli import _zoho_config_from_env
from .output.zoho_export import read_journal_csv
from .zoho.client import ZohoAPIError, ZohoAuthError, ZohoClient
from .zoho.idempotent import (
    DEFAULT_ORG_ALLOWLIST,
    REFUSAL_CROSS_ORG,
    REFUSAL_UNPOSTABLE,
    JournalEntry,
    PostLedger,
    entries_from_rows,
    execute_post,
    plan_post,
    verify_ambiguous,
)

POST_ENV = "EXPENSE_RECON_ZOHO_POST"

# Ambiguous/inflight rows younger than this cannot be cleared or
# forgotten: a timed-out POST can still commit server-side well after
# the client gave up, and clearing inside that window re-opens the
# double-post door the ledger exists to close.
DEFAULT_GRACE_HOURS = 1.0


def _make_client(org_id: str) -> ZohoClient:
    """Build the API client for `org_id`. Module-level so tests can
    monkeypatch it with a fake-transport client (mirrors
    `learning_cli._make_zoho_client`)."""
    return ZohoClient(_zoho_config_from_env(org_id))


def _err(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _grace_cutoff_iso(grace_hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=grace_hours)).isoformat(
        timespec="seconds"
    )


def _older_than_grace(recorded_at: str, grace_hours: float) -> bool:
    try:
        recorded = datetime.fromisoformat(recorded_at)
    except ValueError:
        return False  # bad timestamp never ages out (deny-by-default)
    return recorded < datetime.now(timezone.utc) - timedelta(hours=grace_hours)


def _entry_line(entry: JournalEntry) -> str:
    total = sum(
        (ln.amount for ln in entry.lines if ln.debit_or_credit == "credit"),
        start=Decimal("0"),
    )
    debits = sum(1 for ln in entry.lines if ln.debit_or_credit == "debit")
    return (
        f"  {entry.reference}  {entry.journal_date}  "
        f"{debits} debit line(s)  total {total:.2f}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="expense-recon zoho-post",
        description=(
            "Post the reviewed Zoho journal export via the Books API, "
            "guarded by the 4.8 idempotency ledger. Dry-run by default."
        ),
    )
    parser.add_argument(
        "--config", required=True, type=Path,
        help="Run config JSON (zoho.post block + coa_validation for org/chart).",
    )
    parser.add_argument(
        "--csv", type=Path, default=None,
        help="The reviewed journal export CSV to post (required unless "
        "--verify/--ledger/--forget).",
    )
    parser.add_argument(
        "--go", action="store_true",
        help="Actually post. Without this flag the run is a dry run that "
        "prints the plan and posts nothing.",
    )
    parser.add_argument(
        "--expect", type=int, default=None,
        help="Refuse unless the to-post count equals exactly this number "
        "(count assertion, rule_brisken_graph_send_by_id).",
    )
    parser.add_argument(
        "--allow-partial", action="store_true",
        help="Waive ONLY the unpostable-entries batch refusal (post the "
        "clean entries, report the rest). Conflicts and unresolved "
        "ledger states still refuse.",
    )
    parser.add_argument(
        "--allow-cross-org", action="store_true",
        help="Waive ONLY the cross-org refusal, after confirming the "
        "flagged references are genuinely different transactions and "
        "not the same export posted under the other entity's config.",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Reconcile unresolved (inflight/ambiguous) ledger rows "
        "against Zoho by reference_number. Confirms what it finds; "
        "absent rows are only reported unless --clear-absent.",
    )
    parser.add_argument(
        "--clear-absent", action="store_true",
        help="With --verify: clear absent rows OLDER than the grace "
        "window (zoho.post.grace_hours, default 1h) so they may post "
        "again. Younger rows are kept — a late server-side commit "
        "could still land.",
    )
    parser.add_argument(
        "--ledger", action="store_true", help="List the ledger and exit.",
    )
    parser.add_argument(
        "--forget", metavar="REFERENCE", default=None,
        help="Remove one reference from the ledger so it may post again "
        "(operator escape hatch; use only after confirming Zoho-side state).",
    )
    args = parser.parse_args(argv)

    # ── config ───────────────────────────────────────────────────────
    try:
        cfg = json.loads(args.config.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _err(f"config not found: {args.config}")
    except ValueError as exc:
        return _err(f"config is not valid JSON: {exc}")
    config_dir = args.config.parent

    zoho_cfg = cfg.get("zoho") or {}
    post_cfg = zoho_cfg.get("post") or {}
    coa_cfg = cfg.get("coa_validation") or {}

    org_id = str(coa_cfg.get("org_id") or "").strip()
    if not org_id:
        return _err(
            "config.coa_validation.org_id is required (the poster targets the "
            "same entity org the COA gate validated against)"
        )

    ledger_rel = post_cfg.get("ledger_path")
    ledger_path = (config_dir / ledger_rel).resolve() if ledger_rel else None

    # The config may only NARROW the hardcoded allowlist, never widen
    # it: a runtime JSON must not be able to authorize an org the code
    # was never reviewed for. Widening = editing DEFAULT_ORG_ALLOWLIST
    # in a PR.
    allowlist = frozenset(DEFAULT_ORG_ALLOWLIST)
    if post_cfg.get("org_allowlist"):
        allowlist &= frozenset(str(o) for o in post_cfg["org_allowlist"])
    status = str(post_cfg.get("status") or "draft")
    if status not in ("draft", "published"):
        return _err(f"config.zoho.post.status must be draft|published, got {status!r}")
    try:
        grace_hours = float(post_cfg.get("grace_hours", DEFAULT_GRACE_HOURS))
    except (TypeError, ValueError):
        return _err("config.zoho.post.grace_hours must be a number")

    # ── ledger-only actions ──────────────────────────────────────────
    if args.ledger or args.forget:
        if ledger_path is None:
            return _err("config.zoho.post.ledger_path is required")
        if not ledger_path.exists():
            print(f"Ledger not yet created: {ledger_path}")
            return 0 if args.ledger else _err("nothing to forget: no ledger file")
        with PostLedger(ledger_path) as ledger:
            if args.forget:
                row = ledger.status_for(org_id, args.forget)
                if row is None:
                    return _err(f"no ledger row for {args.forget!r} in org {org_id}")
                if row.state == "inflight" and not _older_than_grace(
                    row.recorded_at, grace_hours
                ):
                    return _err(
                        f"{args.forget} is inflight and recorded {row.recorded_at} "
                        f"(inside the {grace_hours}h grace window) — a posting "
                        f"process may still be running or a POST may still "
                        f"commit; wait, or run --verify first"
                    )
                ledger.remove(org_id, args.forget)
                print(f"Forgot {args.forget} (org {org_id}); it may post again.")
                return 0
            rows = ledger.list_rows()
            if not rows:
                print("Ledger is empty.")
            for r in rows:
                print(
                    f"  {r.state:9s}  {r.reference}  org {r.org_id}  "
                    f"journal {r.zoho_journal_id or '-'}  at {r.posted_at or r.recorded_at}"
                )
        return 0

    # ── verify action ────────────────────────────────────────────────
    if args.verify:
        if ledger_path is None:
            return _err("config.zoho.post.ledger_path is required")
        if not ledger_path.exists():
            print("Ledger not yet created; nothing to verify.")
            return 0
        try:
            client = _make_client(org_id)
        except ValueError as exc:
            return _err(str(exc))
        with PostLedger(ledger_path) as ledger:
            if not ledger.unresolved(org_id):
                print("No unresolved ledger rows; nothing to verify.")
                return 0
            try:
                report = verify_ambiguous(
                    client,
                    ledger,
                    org_id,
                    now_iso=_now_iso(),
                    clear_absent_before=(
                        _grace_cutoff_iso(grace_hours) if args.clear_absent else None
                    ),
                )
            except (ZohoAPIError, ZohoAuthError) as exc:
                return _err(f"verify failed against Zoho: {exc}")
        for ref, jid in report.confirmed:
            print(f"CONFIRMED in Zoho: {ref} -> journal {jid} (ledger now posted)")
        for ref in report.cleared:
            print(f"CLEARED (absent + aged past grace): {ref} (may post again)")
        for ref, reason in report.kept:
            print(f"KEPT unresolved: {ref} — {reason}")
        return 0

    # ── plan / post flow ─────────────────────────────────────────────
    if args.csv is None:
        return _err("--csv is required (the reviewed journal export to post)")
    chart_rel = coa_cfg.get("chart_path")
    if not chart_rel:
        return _err("config.coa_validation.chart_path is required")
    chart_path = (config_dir / chart_rel).resolve()
    try:
        chart = load_entity_chart(chart_path, org_id)
    except FileNotFoundError:
        return _err(f"chart file not found: {chart_path}")
    except KeyError as exc:
        return _err(f"org {org_id} not in chart file: {exc}")

    try:
        rows = read_journal_csv(args.csv)
    except FileNotFoundError:
        return _err(f"journal CSV not found: {args.csv}")
    except ValueError as exc:
        return _err(str(exc))

    entries = entries_from_rows(rows, chart)

    ledger: PostLedger | None = None
    ledger_exists = ledger_path is not None and ledger_path.exists()
    if ledger_exists:
        ledger = PostLedger(ledger_path)
    try:
        plan = plan_post(
            entries, ledger, org_id, allow_cross_org=args.allow_cross_org
        )

        # ── the plan, human-legible (the last human check) ───────────
        print(f"Journal post plan — org {org_id}, {args.csv.name}, status={status}")
        print(f"  TO POST: {len(plan.to_post)}")
        for e in plan.to_post:
            print(_entry_line(e))
        if plan.skip_posted:
            print(f"  ALREADY POSTED (skipped, idempotency): {len(plan.skip_posted)}")
            for e in plan.skip_posted:
                print(f"    {e.reference}")
        for e, reason in plan.conflicts:
            print(f"  CONFLICT: {e.reference} — {reason}")
        for e, reason in plan.blocked:
            print(f"  BLOCKED: {e.reference} — {reason}")
        for e, reason in plan.cross_org:
            print(f"  CROSS-ORG: {e.reference} — {reason}")
        for e in plan.unpostable:
            print(f"  UNPOSTABLE: {e.reference or '(blank ref)'}")
            for b in e.blockers:
                print(f"      - {b}")

        # ── gates (reported on dry run, enforced on --go) ────────────
        # Waivers key on the refusal KIND, never on message prose.
        waived_kinds = set()
        if args.allow_partial:
            waived_kinds.add(REFUSAL_UNPOSTABLE)
        if args.allow_cross_org:
            waived_kinds.add(REFUSAL_CROSS_ORG)  # already waived in the plan
        refusals = [
            msg for kind, msg in plan.batch_refusals if kind not in waived_kinds
        ]
        # Strict boolean: a kill switch must not read "false" as on.
        if post_cfg.get("enabled") is not True:
            refusals.append(
                "config.zoho.post.enabled is not the boolean true"
                + (
                    f" (found {post_cfg.get('enabled')!r})"
                    if "enabled" in post_cfg
                    else ""
                )
            )
        if os.environ.get(POST_ENV) != "1":
            refusals.append(f"env {POST_ENV}=1 is not set")
        if org_id not in allowlist:
            refusals.append(
                f"org {org_id} is not on the allowlist {sorted(allowlist)}"
            )
        if ledger_path is None:
            refusals.append("config.zoho.post.ledger_path is required")
        if args.expect is not None and len(plan.to_post) != args.expect:
            refusals.append(
                f"--expect {args.expect} but plan has {len(plan.to_post)} to post"
            )

        if not args.go:
            if refusals:
                print("Would REFUSE --go:")
                for r in refusals:
                    print(f"  - {r}")
            else:
                print(
                    f"DRY RUN: would post {len(plan.to_post)} journal(s) as "
                    f"{status}. Re-run with --go."
                )
            return 0

        if refusals:
            for r in refusals:
                print(f"REFUSED: {r}", file=sys.stderr)
            print("Nothing was posted.", file=sys.stderr)
            return 2

        if not plan.to_post:
            print("Nothing to post (all entries already in the ledger).")
            return 0

        # ── the actual post ──────────────────────────────────────────
        if ledger is None:
            ledger = PostLedger(ledger_path)
        try:
            client = _make_client(org_id)
        except ValueError as exc:
            return _err(str(exc))
        report = execute_post(
            client,
            plan.to_post,
            ledger,
            org_id,
            now_iso=_now_iso(),
            status=status,
            source=str(args.csv),
        )
    finally:
        if ledger is not None:
            ledger.close()

    for ref, jid in report.posted:
        print(f"POSTED {ref} -> journal {jid} ({status})")
    for ref, msg in report.rejected:
        print(f"REJECTED by Zoho (rolled back, may retry): {ref} — {msg}")
    for ref, msg in report.ambiguous:
        print(
            f"AMBIGUOUS (batch aborted; run --verify before anything else): "
            f"{ref} — {msg}"
        )
    for ref in report.not_attempted:
        print(f"NOT ATTEMPTED (after abort): {ref}")
    print(
        f"Posted {len(report.posted)}/{len(plan.to_post)}; "
        f"rejected {len(report.rejected)}; ambiguous {len(report.ambiguous)}."
    )
    return 0 if not (report.rejected or report.ambiguous) else 1
