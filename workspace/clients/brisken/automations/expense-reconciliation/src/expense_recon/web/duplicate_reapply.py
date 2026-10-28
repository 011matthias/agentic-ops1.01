"""Re-apply the duplicate rules to a month already matched (backlog item 223
step 7, 2026-09-27).

Which copy of a duplicated purchase counts is chosen at RE-MATCH time (item
217: the payment receipt over its invoice; front 4: a document over a
rendered mail body) and stored as the snapshot's `duplicate_kept`. A month
with a statement shows that stored choice until its next natural re-match,
so a rule that changed since leaves the month as it was: September 2026 held
12 invoice-over-receipt groups waiting for a re-match nothing was going to
trigger.

`POST /api/runs/{run_id}/duplicates/reapply` is the operator's way to run
that re-match on purpose, one month at a time, after previewing it.

- The preview (`preview_reapply`) writes nothing. It builds the Expenses
  view twice: once as the month stands, once with `duplicate_kept` replaced
  by the choice a re-match would store now. That choice comes from the
  re-match's own functions (`held_documents`, then `duplicate_pool`, which
  decides the groups without the statement check and runs `choose_kept`),
  over the grid's own receipts minus any another month has settled, which
  is the pool `rematch_month` hands `duplicate_pool`.
- What the preview cannot see: the statement check (rung 7) needs the match
  itself, so each group keeps the restoration the last re-match stored, and
  a charge the matcher pairs differently once another copy is in its pool
  shows up only in the real run's re-read (`applied`).
- The real run (`run_reapply_job`) is the month's ordinary re-match
  (`rematch_after_change`, trigger `duplicates_reapply`). Its job result
  carries the preview computed just before the write and the same diff read
  back after it.
"""
from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .service import (
    DUPLICATE_KEPT_KEY,
    MODE_EXPENSE_GENERATION,
    RunInputError,
    duplicate_pool,
    grid_card_chain,
    has_statement,
    held_documents,
    rematch_after_change,
    rematch_pending,
    run_mode,
)
from .store import JOB_DONE, JOB_ERROR, RunStore

log = logging.getLogger(__name__)

ViewOf = Callable[[RunStore, object], dict]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rematch_running(run) -> bool:
    """True while the month owes a re-match nobody has seen fail: the mark
    (`rematch_pending`, item 113) is written just before a re-match runs and
    cleared by its commit. A mark whose latest event is a recorded failure
    (`failed_at` at or after `changed_at`) is owed, not running; a re-apply
    is then the retry that pays it."""
    mark = rematch_pending(run)
    if mark is None:
        return False
    failed_at = str(mark.get("failed_at") or "")
    return not (failed_at and failed_at >= str(mark.get("changed_at") or ""))


def reapply_refusal(run) -> RunInputError | None:
    """Why the duplicate rules cannot be re-applied to this run, or None.
    Checked by the route and again when the job starts."""
    if run is None:
        return RunInputError("run not found", code="run_not_found")
    if run_mode(run) != MODE_EXPENSE_GENERATION:
        return RunInputError("not an expense batch", code="not_an_expense_batch")
    if not has_statement(run):
        return RunInputError(
            "this month has no statement, so nothing is matched; its "
            "duplicate rules already apply as the page is read",
            code="reapply_no_statement")
    if run.published:
        return RunInputError(
            "this month is published; unpublish it before re-applying its "
            "duplicate rules", code="month_published")
    if rematch_running(run):
        return RunInputError(
            "a re-match of this month is running or owed; it applies the "
            "duplicate rules itself, so wait for it to finish",
            code="rematch_running")
    return None


def confirm_refusal(run, confirm: str) -> RunInputError | None:
    """The typed confirm: the month's label or its run id, for a preview as
    for a real run, so a mistyped id never previews another month quietly."""
    if not confirm:
        return RunInputError(
            "confirm is required: repeat the month label (or run id) to "
            "re-apply its duplicate rules", code="reapply_confirm_required")
    if confirm not in {(run.label or "").strip(), run.run_id}:
        return RunInputError("confirm label mismatch", code="reapply_confirm_mismatch")
    return None


def kept_after_rematch(
    store: RunStore, run, learning_db_path: "Path | None"
) -> dict[str, str]:
    """group id -> the document a re-match of this month would keep, i.e.
    the `duplicate_kept` its commit would store. Read-only."""
    resolutions = store.get_duplicate_resolutions(run.run_id)
    chain = grid_card_chain(
        run,
        store.get_category_overrides(run.run_id),
        store.get_expense_field_overrides(run.run_id),
        store.get_expense_edits(run.run_id),
        resolutions,
        settings=store.get_settings(),
        decisions=store.get_decisions(run.run_id),
        learning_db_path=learning_db_path,
    )
    # rematch_month's advisory read: a receipt another run has settled is
    # out of the pool before `duplicate_pool` sees it.
    foreign = {
        doc for doc, c in store.get_claims_on_receipts(run.run_id).items()
        if c["claimed_by_run_id"] != run.run_id
    }
    pool = [r for r in chain.receipts if r.document_id not in foreign]
    _kept_pool, _collapsed, decisions = duplicate_pool(
        run, pool, resolutions, held=held_documents(store, run)
    )
    # The value rematch_month's commit writes under DUPLICATE_KEPT_KEY.
    return {d.group_id: d.members[0] for d in decisions if d.is_copy and d.members}


def with_stored_kept(run, kept: dict[str, str]):
    """The run as it would read once a re-match stored `kept`; never saved."""
    snapshot = dict(run.snapshot or {})
    if kept:
        snapshot[DUPLICATE_KEPT_KEY] = kept
    else:
        snapshot.pop(DUPLICATE_KEPT_KEY, None)
    return replace(run, snapshot=snapshot)


def duplicate_layer(view: dict) -> dict:
    """What an Expenses payload says about duplicates: each receipt group's
    basis, verdict and kept copy, whether each document counts in the total,
    and the totals."""
    groups: dict[str, dict] = {}
    for g in view.get("duplicate_groups") or []:
        if g.get("kind") != "receipt":
            continue
        members = list(g.get("members") or [])
        groups[g["group_id"]] = {
            "members": sorted(members),
            "basis": g.get("basis"),
            "verdict": g.get("verdict"),
            "kept": members[0] if g.get("verdict") == "copy" and members else None,
        }
    counts = {
        e["document_id"]: e.get("counts_in_total") is not False
        for e in view.get("expenses") or []
    }
    totals = dict((view.get("summary") or {}).get("totals_by_ccy") or {})
    return {"groups": groups, "counts": counts, "totals_by_ccy": totals}


def layer_diff(before: dict, after: dict) -> dict:
    """The groups whose basis, verdict or kept copy moved, the documents
    whose `counts_in_total` flipped, and the totals either side."""
    fields = ("basis", "verdict", "kept")
    moving = []
    for gid in sorted(set(before["groups"]) | set(after["groups"])):
        b, a = before["groups"].get(gid), after["groups"].get(gid)
        b_side = {k: b[k] for k in fields} if b else None
        a_side = {k: a[k] for k in fields} if a else None
        if b_side != a_side:
            moving.append({
                "group_id": gid,
                "members": (a or b)["members"],
                "before": b_side,
                "after": a_side,
            })
    both = sorted(set(before["counts"]) & set(after["counts"]))
    return {
        "n_groups": len(after["groups"]),
        "groups": moving,
        "counts_in_total": {
            "true_to_false": [
                d for d in both if before["counts"][d] and not after["counts"][d]
            ],
            "false_to_true": [
                d for d in both if not before["counts"][d] and after["counts"][d]
            ],
        },
        "totals_by_ccy": {
            "before": before["totals_by_ccy"], "after": after["totals_by_ccy"],
        },
    }


def preview_reapply(
    store: RunStore, run, view_of: ViewOf, learning_db_path: "Path | None",
    *, before_view: dict | None = None,
) -> dict:
    """What a re-match would change in the month's duplicate layer. Writes
    nothing: the "after" side is the same Expenses view built over the run
    with the re-match's kept choice in place of the stored one."""
    if before_view is None:
        before_view = view_of(store, run)
    kept = kept_after_rematch(store, run, learning_db_path)
    after_view = view_of(store, with_stored_kept(run, kept))
    return layer_diff(duplicate_layer(before_view), duplicate_layer(after_view))


def run_reapply_job(
    db_path: Path, learning_db_path: "Path | None", job_id: str, run_id: str,
    view_of: ViewOf,
) -> None:
    """The real run, off the request: preview, the month's ordinary re-match,
    then the same diff read back. A refusal or a failed re-match lands as the
    job's error, its code first; the preview rides the result either way."""
    def _stage(store: RunStore, name: str) -> None:
        try:
            store.set_job_stage(job_id, name, _now())
        except Exception:  # noqa: BLE001 - progress is best-effort
            pass

    preview = None
    try:
        with RunStore(db_path) as store:
            run = store.get_run(run_id)
            refused = reapply_refusal(run)
            if refused is not None:
                raise refused
            _stage(store, "previewing")
            before_view = view_of(store, run)
            preview = preview_reapply(
                store, run, view_of, learning_db_path, before_view=before_view,
            )
            rematch = rematch_after_change(
                store, run_id, learning_db_path=learning_db_path,
                on_stage=lambda s: _stage(store, s), trigger="duplicates_reapply",
            )
            if rematch is None:
                raise RunInputError(
                    "this month no longer has a statement to match against",
                    code="reapply_no_statement")
            if rematch.get("error"):
                raise RunInputError(
                    "the re-match failed; the month's match is as it was: "
                    f"{rematch['error']}", code="rematch_failed")
            fresh = store.get_run(run_id)
            applied = layer_diff(
                duplicate_layer(before_view), duplicate_layer(view_of(store, fresh))
            )
            result = {
                "run_id": run_id,
                "label": fresh.label,
                "preview": preview,
                "applied": applied,
                "rematch": rematch,
            }
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id,
                result=json.dumps(result, default=str), updated_at=_now(),
            )
    except RunInputError as exc:
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=f"{exc.code}: {exc.message}",
                result=json.dumps({"preview": preview}, default=str) if preview else None,
                updated_at=_now(),
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        log.exception("item 223 step 7: re-apply failed on %s", run_id)
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc),
                result=json.dumps({"preview": preview}, default=str) if preview else None,
                updated_at=_now(),
            )
