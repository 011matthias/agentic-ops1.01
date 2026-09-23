# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "openpyxl==3.1.5",
#     "openai==2.38.0",
#     "pypdf==6.13.2",
#     "pypdfium2==5.9.0",
#     "pillow==12.2.0",
#     "rapidfuzz>=3.0",
#     "reportlab>=4.0",
# ]
# ///
"""Attribution replay for the expense-recon grid: which card, entity, person
and category each receipt gets, from which link of which chain, and how often
that answer is the one a human gave.

The matcher has had an instrument since item 69 (`recon-match-attribution.py`,
"which gate lost this receipt"). The four ATTRIBUTION chains had none: nothing
anywhere judged a card, a legal entity, a person or a category, so every round
of work on them was argued from examples. This is that instrument.

It replays a hosted month through `build_expense_view` -- the same function the
Expenses route calls, with the same store reads -- so the rows it reports are
the rows Criss sees. No model call and no network beyond the database copy
handed to it; same input, same table.

Three truths ground it, in descending strength, and none of them is a judgement
call made here:

* THE STATEMENT'S OWN CARD COLUMN. For a receipt whose charge a human confirmed
  in `labels.csv`, the card that paid it is the `Card` column of that charge
  (`Transaction.card_last4`). Free, exact, and the only card truth that exists
  for a row nobody has edited.
* THE REVIEWER'S OWN FIX. `expense_field_overrides` (`card_key`) and
  `category_overrides` are Criss's answer where she gave one. Measured HELD
  OUT: the chain is re-run with her fix removed, and what it produces on its
  own is compared against it. That is the only honest way to score a chain
  whose output the fix otherwise overwrites.
* THE FILED CATEGORY. `Receipt.zoho_category`, what Criss typed on the ER PDF
  at filing time, for the months whose receipts carry one.

Sections printed per month: the source histogram for each chain (which link
answered), the card-less breakdown (what the receipt printed, when it printed
anything), and the held-out scores.

`--what-if` runs the same replay with ONE link of the chain changed and diffs
the two, which is how a proposed fix is sized before it is written. The changes
are installed as patches on the module's own functions, so the real chain runs
in the real order; each is named in `WHAT_IFS` with the fact it tests.
`--what-if sanity:HINT=card-key` is the instrument's own proof: it fabricates
one hint assignment, and the card-less count must fall by exactly the number of
rows printing that hint. An instrument whose numbers do not move when the rule
moves is measuring nothing.
"""
from __future__ import annotations

import argparse
import csv
import inspect
import json
import os
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_MODULE_SRC_DEFAULT = REPO / "workspace/clients/brisken/automations/expense-reconciliation/src"
MODULE_SRC = Path(os.environ.get("RECON_MODULE_SRC") or _MODULE_SRC_DEFAULT)

MODULE_FILE: Path | None = None
LEARNING_DB: Path | None = None


def _import_module() -> Path:
    """Put MODULE_SRC first on sys.path and PROVE the import took it.

    The same guard `recon-match-attribution.py` carries, for the same reason: a
    path that exists but cannot be imported from falls through to the venv's
    editable module with exit 0, and a branch's "after" table then silently
    equals main's "before"."""
    global MODULE_FILE
    if not MODULE_SRC.is_dir():
        raise SystemExit(f"ERROR: module source not found: {MODULE_SRC}")
    sys.path.insert(0, str(MODULE_SRC))
    import expense_recon

    resolved = Path(expense_recon.__file__).resolve()
    if MODULE_SRC.resolve() not in resolved.parents:
        raise SystemExit(
            f"ERROR: expense_recon imported from {resolved}, not from "
            f"{MODULE_SRC}. Set RECON_MODULE_SRC, or run from the tree you "
            "mean to measure."
        )
    MODULE_FILE = resolved
    return resolved


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


def replay(db: Path, run_id: str, *, drop_card_fix=False, drop_category=False) -> dict:
    """One month's grid, as the Expenses route composes it.

    `drop_card_fix` / `drop_category` strip the reviewer's own answers from the
    inputs, which is what makes a held-out score possible: the chain then has
    to produce the value she typed rather than echo it back."""
    from expense_recon.web.service import build_expense_view
    from expense_recon.web.store import RunStore

    store = RunStore(db)
    run = store.get_run(run_id)
    if run is None:
        raise SystemExit(f"ERROR: no run {run_id} in {db}")
    overrides = store.get_category_overrides(run_id)
    field_overrides = store.get_expense_field_overrides(run_id)
    if drop_category:
        overrides = {}
    if drop_card_fix:
        stripped = {
            doc: {k: v for k, v in fields.items() if k != "card_key"}
            for doc, fields in field_overrides.items()
        }
        field_overrides = {doc: f for doc, f in stripped.items() if f}
    kw = {}
    # Item 169: a tree that reads the remembered card live wants the learning
    # store; one that does not has no such parameter, and passing it would be
    # a TypeError rather than a measurement. Accept both, so a before/after
    # can be taken across the change.
    if LEARNING_DB is not None and "learning_db_path" in inspect.signature(
        build_expense_view
    ).parameters:
        kw["learning_db_path"] = LEARNING_DB
    view = build_expense_view(
        run,
        overrides,
        field_overrides,
        store.get_expense_edits(run_id),
        store.get_duplicate_resolutions(run_id),
        settings=store.get_settings(),
        decisions=store.get_decisions(run_id),
        **kw,
    )
    view["_label"] = run.label
    return view


def truth_cards(db: Path, run_id: str, labels: Path | None) -> dict[str, str]:
    """`{document_id: card last4}` from the statement's own Card column, for
    every pair a human confirmed. No inference: the charge the label names
    carries the card that paid it."""
    if labels is None or not labels.exists():
        return {}
    from expense_recon.web.serialize import snapshot_from_dict
    from expense_recon.web.store import RunStore

    run = RunStore(db).get_run(run_id)
    txs, _receipts, _outcome, _rest = snapshot_from_dict(run.snapshot)
    by_id = {t.transaction_id: t for t in txs}
    out: dict[str, str] = {}
    with labels.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("status") or "").strip() != "confirmed":
                continue
            tx = by_id.get((row.get("transaction_id") or "").strip())
            last4 = str(getattr(tx, "card_last4", "") or "").strip()
            if last4:
                out[(row.get("document_id") or "").strip()] = last4
    return out


# ---------------------------------------------------------------------------
# What-ifs: one link changed, the rest of the chain untouched
# ---------------------------------------------------------------------------


@contextmanager
def what_if_unresolved_digits(db: Path, run_id: str):
    """Fact 1 (item 169): a printed number naming none of our cards stops
    blocking the fallbacks.

    `resolve_batch_row_cards` guards the settled-charge / learned / merchant
    links with `not _card_keys(hint)`, so a hint carrying ANY digit run
    suppresses all three. The reason holds for a number that names a card
    ("memory never overrides a number the document shows") and not for one that
    names none. The patch narrows `_card_keys` to digits this batch's registry
    can resolve, which is the shape the fix would take."""
    from expense_recon.cards import resolve_hinted_card_ex
    from expense_recon.matching import deterministic
    from expense_recon.web import service
    from expense_recon.web.store import RunStore

    cfg = RunStore(db).get_run(run_id).config or {}
    cards = service._batch_cards(cfg)
    hints = service._batch_card_hints(cfg)
    original = deterministic._card_keys

    def narrowed(value):
        keys = original(value)
        if not keys:
            return keys
        card, _ambiguous = resolve_hinted_card_ex(str(value or ""), cards, hints)
        return keys if card is not None else ()

    deterministic._card_keys = narrowed
    try:
        yield
    finally:
        deterministic._card_keys = original


def _sanity_factory(spec: str):
    """`sanity:HINT=card-key` -- fabricate one hint assignment.

    The instrument's own proof. A fabricated rule has to move the count by
    exactly the rows it touches; a table that does not move is measuring
    nothing, which is how the item-115 replay was proven."""
    hint, _, key = spec.partition("=")
    hint, key = hint.strip(), key.strip()
    if not hint or not key:
        raise SystemExit("ERROR: --what-if sanity:HINT=card-key needs both halves")

    @contextmanager
    def run():
        from expense_recon.web import service

        original = service._batch_card_hints

        def patched(cfg):
            out = dict(original(cfg) or {})
            out[hint] = key
            return out

        service._batch_card_hints = patched
        try:
            yield
        finally:
            service._batch_card_hints = original

    return run


@contextmanager
def what_if_learned_card_live(db: Path, run_id: str):
    """Item 169: the remembered card consulted at READ time, like every link
    beside it.

    `resolve_batch_row_cards` reads the learned card off `Receipt.card_key`, a
    value `ExpenseMemory.apply` stamps during `generate_expenses` and nowhere
    else. Every other link in the same chain resolves live against current
    state -- the row's override, the batch's hints, the settled charge, and
    (note item M2, explicitly) the merchant registry, "so the day a merchant
    gains a card the existing months resolve without a refresh pass". The
    learned link alone is frozen at ingest, so a correction taught after a
    month was ingested can never reach it.

    The patch fills `card_key` from the live learning store before the chain
    runs, for rows carrying none, which is the shape the fix would take.
    Needs `--learning`."""
    learning = LEARNING_DB
    if learning is None or not Path(learning).exists():
        raise SystemExit(
            "ERROR: --what-if learned-card-live needs --learning <learning.sqlite>"
        )
    from expense_recon.learning.consult import FieldCorrectionLookup
    from expense_recon.learning.store import LearningStore
    from expense_recon.web import service

    lookup = FieldCorrectionLookup.from_store(LearningStore(Path(learning)))
    original = service.resolve_batch_row_cards

    def patched(receipts, cfg, field_overrides, **kw):
        from dataclasses import replace as _replace

        filled = []
        for r in receipts:
            if not getattr(r, "card_key", None):
                remembered = lookup.get(
                    (r.legal_entity_id or "").strip(), r.detected_vendor
                ).get("card_key")
                if remembered:
                    r = _replace(r, card_key=remembered)
            filled.append(r)
        return original(filled, cfg, field_overrides, **kw)

    service.resolve_batch_row_cards = patched
    try:
        yield
    finally:
        service.resolve_batch_row_cards = original


WHAT_IFS = {
    "unresolved-digits": what_if_unresolved_digits,
    "learned-card-live": what_if_learned_card_live,
}


def _resolve_what_if(name: str):
    if name.startswith("sanity:"):
        factory = _sanity_factory(name.split(":", 1)[1])
        return lambda db, run_id: factory()
    if name not in WHAT_IFS:
        raise SystemExit(
            f"ERROR: unknown --what-if {name!r}; known: "
            + ", ".join(sorted(WHAT_IFS))
            + ", sanity:HINT=card-key"
        )
    return WHAT_IFS[name]


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def rows_of(view: dict) -> list[dict]:
    return list(view.get("expenses") or [])


def card_key_of(row: dict) -> str:
    return str(((row.get("card") or {}) or {}).get("key") or "")


def digits_of(value: str) -> str:
    """The comparable form of a card number: digits only, leading zeros gone.

    A registry key spells the card `card-0340`; the statement's own Card column
    prints it `340`. Comparing the two literally reports a card as wrong that
    is the same card, which is exactly the false negative an unvalidated
    instrument hands back with confidence."""
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits.lstrip("0") or digits


def card_last4_of(row: dict) -> str:
    """The digits the resolved card is known by, for comparison with the
    statement's Card column."""
    card = (row.get("card") or {}) or {}
    return digits_of(card.get("key")) or digits_of(card.get("label"))


def hint_of(row: dict) -> str:
    return str(row.get("payment_hint") or row.get("payment_mode") or "").strip()


def hint_class(row: dict) -> str:
    """What a card-less receipt printed, in the three classes the fix work
    splits on: nothing at all, a tender word no card carries, or digits that
    resolved to none of our cards."""
    hint = hint_of(row)
    if not hint:
        return "no payment method printed"
    if any(ch.isdigit() for ch in hint):
        return "digits, no registry card"
    return "tender word, no card"


def measure(view: dict, truth: dict[str, str]) -> dict:
    rows = rows_of(view)
    total = len(rows) or 1
    cardless = [row for row in rows if not card_key_of(row)]
    right = wrong = unanswered = 0
    wrong_rows: list[tuple[str, str, str, str, str]] = []
    conflicts: list[tuple[str, str, str, str, str]] = []
    for row in rows:
        want = digits_of(truth.get(row["document_id"]))
        if not want:
            continue
        got = card_last4_of(row)
        source = str(row.get("card_source") or "none")
        entry = (row["document_id"], want, got, source, hint_of(row))
        # A reviewer's own pick is a decision, not a prediction: it is the top
        # link by design, so scoring it as a chain error would report the
        # chain as wrong for obeying her. It is still worth surfacing when it
        # contradicts the statement, which is a question for her, not a bug.
        if source == "override":
            if got and got != want:
                conflicts.append(entry)
            continue
        if not got:
            unanswered += 1
        elif got == want:
            right += 1
        else:
            wrong += 1
            wrong_rows.append(entry)
    return {
        "label": view.get("_label") or "",
        "n": len(rows),
        "total": total,
        "card_source": Counter(row.get("card_source") or "none" for row in rows),
        "entity_source": Counter(row.get("entity_source") or "none" for row in rows),
        "person_source": Counter(row.get("person_source") or "none" for row in rows),
        "category_source": Counter(
            ((row.get("posting_category") or {}) or {}).get("source") or "none"
            for row in rows
        ),
        "n_no_card": len(cardless),
        "n_no_entity": sum(
            1 for r in rows if not str(r.get("legal_entity_id") or "").strip()
        ),
        "n_no_person": sum(1 for r in rows if not str(r.get("person") or "").strip()),
        "n_no_category": sum(
            1
            for r in rows
            if not str(
                ((r.get("posting_category") or {}) or {}).get("category") or ""
            ).strip()
        ),
        "cardless_classes": Counter(hint_class(r) for r in cardless),
        "cardless_hints": Counter(hint_of(r) for r in cardless if hint_of(r)),
        "truth_right": right,
        "truth_wrong": wrong,
        "truth_unanswered": unanswered,
        "truth_wrong_rows": wrong_rows,
        "truth_conflicts": conflicts,
        "truth_n": right + wrong + unanswered,
    }


def held_out_card(db: Path, run_id: str) -> dict:
    """Score the chain against the reviewer's own card picks, held out.

    Her `card_key` fix is the top link, so with it in place the chain can only
    agree with itself. Removed, whatever the rest of the chain produces is a
    prediction of the answer she gave."""
    from expense_recon.web.store import RunStore

    fixes = {
        doc: str(fields.get("card_key") or "").strip()
        for doc, fields in RunStore(db).get_expense_field_overrides(run_id).items()
        if str(fields.get("card_key") or "").strip()
    }
    if not fixes:
        return {"n": 0, "right": 0, "wrong": 0, "silent": 0, "rows": []}
    rows = {r["document_id"]: r for r in rows_of(replay(db, run_id, drop_card_fix=True))}
    right = wrong = silent = 0
    detail = []
    for doc, want in sorted(fixes.items()):
        row = rows.get(doc) or {}
        got = card_key_of(row)
        if not got:
            silent += 1
        elif got == want:
            right += 1
        else:
            wrong += 1
        detail.append((doc, want, got or "-", str(row.get("card_source") or "none")))
    return {"n": len(fixes), "right": right, "wrong": wrong, "silent": silent, "rows": detail}


def held_out_category(db: Path, run_id: str) -> dict:
    """The same, for the reviewer's category overrides.

    A category override is keyed `(document_id, line_index)`, not by document:
    a reviewer reclassifies a LINE, and a two-line invoice can carry two
    different corrections. Scoring it per document reads every override as
    unanswered, which is the shape of a probe that cannot see the thing it is
    asked about (`rule_behaviors` instrument-validity)."""
    from expense_recon.web.store import RunStore

    fixes: dict[tuple[str, int], str] = {}
    for key, value in RunStore(db).get_category_overrides(run_id).items():
        doc, index = key if isinstance(key, tuple) else (key, 0)
        want = value.get("category") if isinstance(value, dict) else value
        want = str(want or "").strip()
        if want:
            fixes[(str(doc), int(index))] = want
    if not fixes:
        return {"n": 0, "right": 0, "wrong": 0, "silent": 0, "rows": [], "by_tier": Counter()}
    rows = {r["document_id"]: r for r in rows_of(replay(db, run_id, drop_category=True))}
    right = wrong = silent = 0
    detail = []
    by_tier: Counter = Counter()
    for (doc, index), want in sorted(fixes.items()):
        row = rows.get(doc) or {}
        lines = {int(li.get("index", i)): li for i, li in enumerate(row.get("line_items") or [])}
        line = lines.get(index) or {}
        got = str(line.get("category") or "").strip()
        tier = str(line.get("source") or "none")
        vendor = str(((row.get("vendor") or {}) or {}).get("display") or "")
        if not got:
            silent += 1
            verdict = "silent"
        elif got == want:
            right += 1
            verdict = "right"
        else:
            wrong += 1
            verdict = "wrong"
        by_tier[f"{tier}:{verdict}"] += 1
        detail.append((f"{doc}#{index}", vendor, want, got or "-", tier))
    return {
        "n": len(fixes),
        "right": right,
        "wrong": wrong,
        "silent": silent,
        "rows": detail,
        "by_tier": by_tier,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _hist(title: str, counter: Counter, total: int) -> list[str]:
    out = [f"  {title}"]
    for key, n in counter.most_common():
        out.append(f"    {key:<22} {n:>4}  {100 * n / total:5.1f}%")
    return out


def print_month(m: dict, held: dict | None, detail: bool = False) -> None:
    print(f"\n=== {m['label']}  ({m['n']} receipts) ===")
    for title, key in (
        ("card, by link", "card_source"),
        ("legal entity, by link", "entity_source"),
        ("person, by link", "person_source"),
        ("category, by link", "category_source"),
    ):
        for line in _hist(title, m[key], m["total"]):
            print(line)
    print(
        f"  unanswered: card {m['n_no_card']}, entity {m['n_no_entity']}, "
        f"person {m['n_no_person']}, category {m['n_no_category']}"
    )
    if m["cardless_classes"]:
        print("  card-less rows, by what the receipt printed")
        for key, n in m["cardless_classes"].most_common():
            print(f"    {key:<32} {n:>4}")
    if m["truth_n"]:
        print(
            f"  vs the statement's Card column on confirmed pairs, reviewer "
            f"picks excluded: {m['truth_right']} right, {m['truth_wrong']} "
            f"wrong, {m['truth_unanswered']} unanswered (of {m['truth_n']})"
        )
        for doc, want, got, source, hint in m["truth_wrong_rows"][:6]:
            print(
                f"    WRONG {doc[:46]}: statement {want}, tool {got} "
                f"via {source} (printed {hint!r})"
            )
    for doc, want, got, _source, _hint in m["truth_conflicts"][:6]:
        print(
            f"    REVIEWER PICK vs STATEMENT {doc[:40]}: she picked {got}, "
            f"the charge she confirmed posted on {want}"
        )
    if held:
        card, category = held["card"], held["category"]
        if card["n"]:
            print(
                f"  held-out reviewer card picks: {card['right']} right, "
                f"{card['wrong']} wrong, {card['silent']} silent (of {card['n']})"
            )
        if category["n"]:
            print(
                f"  held-out reviewer categories (per line): {category['right']} "
                f"right, {category['wrong']} wrong, {category['silent']} silent "
                f"(of {category['n']})"
            )
            tiers = category.get("by_tier") or Counter()
            if tiers:
                print(
                    "    by tier: "
                    + ", ".join(f"{k} {v}" for k, v in sorted(tiers.items()))
                )
        if detail:
            for doc, want, got, source in card["rows"]:
                print(f"    card  {doc[:40]:<40} want {want:<12} got {got:<12} via {source}")
            for doc, vendor, want, got, source in category["rows"]:
                print(
                    f"    cat   {vendor[:24]:<24} want {want[:24]:<24} "
                    f"got {got[:24]:<24} via {source}"
                )


def print_diff(before: dict, after: dict, name: str) -> None:
    print(f"\n--- what-if {name}: {before['label']} ---")
    moved = False
    for key in ("n_no_card", "n_no_entity", "n_no_person", "n_no_category"):
        if before[key] != after[key]:
            moved = True
            print(f"  {key:<16} {before[key]} -> {after[key]}  ({after[key] - before[key]:+d})")
    for key in sorted(set(before["card_source"]) | set(after["card_source"])):
        b, a = before["card_source"].get(key, 0), after["card_source"].get(key, 0)
        if b != a:
            moved = True
            print(f"  card via {key:<16} {b} -> {a}  ({a - b:+d})")
    if before["truth_n"]:
        print(
            f"  against the statement: {before['truth_right']} right / "
            f"{before['truth_wrong']} wrong -> {after['truth_right']} right / "
            f"{after['truth_wrong']} wrong"
        )
    if not moved:
        print("  no row moved.")


def _jsonable(m: dict) -> dict:
    return {
        key: (dict(value) if isinstance(value, Counter) else value)
        for key, value in m.items()
        if key not in ("truth_wrong_rows", "truth_conflicts")
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="expense-recon attribution replay")
    ap.add_argument("--live", type=Path, required=True, help="a copy of recon-web.sqlite")
    ap.add_argument("--run-id", action="append", required=True, help="repeatable")
    ap.add_argument(
        "--labels",
        action="append",
        default=[],
        help="a bundle labels.csv, positional against --run-id",
    )
    ap.add_argument(
        "--what-if",
        dest="what_if",
        help="unresolved-digits | learned-card-live | sanity:HINT=card-key",
    )
    ap.add_argument("--learning", type=Path, help="a copy of learning.sqlite")
    ap.add_argument(
        "--held-out",
        action="store_true",
        help="score the chains against the reviewer's own fixes",
    )
    ap.add_argument("--detail", action="store_true", help="per-row held-out table")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    global LEARNING_DB
    LEARNING_DB = args.learning
    resolved = _import_module()
    print(f"module: {resolved.parent}")

    labels = list(args.labels) + [None] * (len(args.run_id) - len(args.labels))
    payload = []
    for run_id, label_path in zip(args.run_id, labels):
        truth = truth_cards(args.live, run_id, Path(label_path) if label_path else None)
        before = measure(replay(args.live, run_id), truth)
        held = None
        if args.held_out:
            held = {
                "card": held_out_card(args.live, run_id),
                "category": held_out_category(args.live, run_id),
            }
        print_month(before, held, detail=args.detail)
        entry = {"run_id": run_id, "before": _jsonable(before)}
        if args.what_if:
            with _resolve_what_if(args.what_if)(args.live, run_id):
                after = measure(replay(args.live, run_id), truth)
            print_diff(before, after, args.what_if)
            entry["after"] = _jsonable(after)
        payload.append(entry)
    if args.json:
        print(json.dumps(payload, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
