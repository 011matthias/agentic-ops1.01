# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "openpyxl==3.1.5",
#     "openai==2.38.0",
#     "pypdf==6.13.2",
#     "pypdfium2==5.9.0",
#     "pillow==12.2.0",
#     "rapidfuzz==3.14.5",
# ]
# ///
"""Brisken expense-recon match accuracy: the CI gate and the deploy check.

Backlog item 127: matching accuracy was measured by hand, offline, and
nothing ran it before a deploy. Two subcommands, both thin wrappers over the
pinned scorer (`tools/scorers/recon-match-accuracy.py`), imported by path the
way `tools/recon-accuracy-guard.py` does so the scoring math has one home.

  ci    --fixtures DIR --expected JSON [--asset TUNING.json] [--write-expected]
        Replay every synthetic labelled bundle under DIR (the committed set
        in the module's tests/fixtures/accuracy/) under the asset (default:
        the module's config/match-tuning.json) and compare twelve per-bundle
        fields against expected.json. This is a GATE on exact equality. The
        scorer is deterministic (no LLM, no network, no clock), so the only
        thing that moves a number is a matcher behaviour change, which is
        exactly what must be written down: a deliberate change bumps
        expected.json in the same PR via --write-expected, and that diff is
        the review artefact. A "report the delta" mode would rot, because
        nobody reads a green comment. The table of differences also lands in
        $GITHUB_STEP_SUMMARY when that variable is set.
        Exit 0 every field equal / 1 any difference / 2 cannot measure.

  real  [--split all|train|holdout] [--baseline JSON] [--markdown]
        [--write-baseline] [--asset TUNING.json]
        Score the six REAL labelled bundles (gitignored client context; the
        scorer's main-clone fallback finds them from any worktree) and
        compare each split against tools/recon-accuracy-baseline.json. A
        split passes when composite >= baseline AND determ_wrong <= baseline
        AND nc_determ_matched <= baseline AND the reconciliation invariant
        holds. --markdown prints the PR-body block whatever the verdict.
        Exit 0 pass / 1 a drop (the failing axis is named) / 2 the bundles
        are absent or unreadable. .claude/hooks/recon-accuracy-deploy-gate.py
        runs this before a `flyctl deploy` of brisken-expense-recon.

The scorer signals an unmeasurable bundle by raising SystemExit with a
message string (which is exit status 1 in Python, not the 2 its docstring
names); both subcommands catch that and exit 2, so a broken fixture can
never read as a bad asset, and never as a pass.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCORER = REPO / "tools" / "scorers" / "recon-match-accuracy.py"
MODULE = REPO / "workspace/clients/brisken/automations/expense-reconciliation"
DEFAULT_ASSET = MODULE / "config" / "match-tuning.json"
DEFAULT_BASELINE = REPO / "tools" / "recon-accuracy-baseline.json"

# Per-bundle fields the CI gate pins, in the order they print.
CI_FIELDS = (
    "composite", "confirmed", "determ_ok", "determ_wrong", "deferred_ok",
    "ambiguous", "unresolved", "no_charge", "nc_determ_matched", "nc_deferred",
    "double_bound_receipts", "invariant_ok",
)
# Per-split fields the real-data baseline records.
REAL_FIELDS = (
    "composite", "determ_ok", "determ_wrong", "nc_determ_matched",
    "deferred_ok", "invariant_ok",
)
SPLITS = ("train", "holdout", "all")


class CannotMeasure(Exception):
    """Exit 2: the inputs cannot be scored (never a verdict either way)."""


def _load_scorer():
    spec = importlib.util.spec_from_file_location(
        "recon_match_accuracy", SCORER
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not mod.MODULE_SRC.is_dir():
        raise CannotMeasure(f"module src not found: {mod.MODULE_SRC}")
    if str(mod.MODULE_SRC) not in sys.path:
        sys.path.insert(0, str(mod.MODULE_SRC))
    return mod


def _match_cfg(asset: Path):
    if not asset.is_file():
        raise CannotMeasure(f"asset not found: {asset}")
    from expense_recon.matching.deterministic import MatchingConfig

    return MatchingConfig.from_file(asset)


def _round(field: str, value):
    return round(float(value), 2) if field == "composite" else value


def _score_bundle(scorer, bundle_dir: Path, cfg) -> dict:
    """The scorer's stats for one bundle, with its unmeasurable signals
    (SystemExit carrying a message, or any loader exception) turned into
    CannotMeasure."""
    try:
        return scorer.evaluate_bundle(bundle_dir, cfg)
    except SystemExit as exc:
        raise CannotMeasure(str(exc.code) if exc.code is not None else
                            f"scorer exited on {bundle_dir.name}") from exc
    except CannotMeasure:
        raise
    except Exception as exc:  # noqa: BLE001 - a broken input is exit 2, never a verdict
        raise CannotMeasure(
            f"{bundle_dir.name}: {type(exc).__name__}: {exc}"
        ) from exc


def _emit(lines: list[str]) -> None:
    text = "\n".join(lines)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write(text + "\n\n")
        except OSError:
            pass


# ─── ci ────────────────────────────────────────────────────────────────

def cmd_ci(args: argparse.Namespace) -> int:
    fixtures = Path(args.fixtures)
    expected_path = Path(args.expected)
    if not fixtures.is_dir():
        raise CannotMeasure(f"fixtures dir not found: {fixtures}")
    bundle_dirs = sorted(p for p in fixtures.iterdir() if p.is_dir())
    if not bundle_dirs:
        raise CannotMeasure(f"no bundle directories under {fixtures}")
    for d in bundle_dirs:
        for name in ("run.json", "labels.csv"):
            if not (d / name).is_file():
                raise CannotMeasure(f"bundle incomplete: {d} (missing {name})")

    scorer = _load_scorer()
    cfg = _match_cfg(Path(args.asset))
    got: dict[str, dict] = {}
    for d in bundle_dirs:
        stats = _score_bundle(scorer, d, cfg)
        got[d.name] = {f: _round(f, stats[f]) for f in CI_FIELDS}

    if args.write_expected:
        expected_path.write_text(
            json.dumps(got, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {expected_path} ({len(got)} bundles)")
        return 0

    if not expected_path.is_file():
        raise CannotMeasure(
            f"expected file not found: {expected_path} "
            "(run once with --write-expected to record it)"
        )
    try:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CannotMeasure(f"expected file unreadable: {exc}") from exc
    if not isinstance(expected, dict):
        raise CannotMeasure("expected file is not a JSON object")
    missing_on_disk = sorted(set(expected) - set(got))
    if missing_on_disk:
        raise CannotMeasure(
            f"expected.json names bundles absent from {fixtures}: "
            f"{missing_on_disk}"
        )

    diffs: list[tuple[str, str, object, object]] = []
    for bundle in sorted(got):
        exp = expected.get(bundle)
        if not isinstance(exp, dict):
            for f in CI_FIELDS:
                diffs.append((bundle, f, "(absent)", got[bundle][f]))
            continue
        for f in CI_FIELDS:
            e = exp.get(f, "(absent)")
            g = got[bundle][f]
            if e != g:
                diffs.append((bundle, f, e, g))

    lines = ["### Recon match accuracy: synthetic bundles vs expected.json", ""]
    if diffs:
        lines += ["| bundle | field | expected | got |", "|---|---|---|---|"]
        lines += [f"| {b} | {f} | {e} | {g} |" for b, f, e, g in diffs]
    else:
        lines.append(
            f"No differences across {len(got)} bundle(s) and "
            f"{len(CI_FIELDS)} fields each."
        )
    lines.append("")
    lines.append(_totals_line(list(got.values())))
    if diffs:
        lines.append("")
        lines.append(
            "GATE RED: the matcher's behaviour on the labelled fixtures moved. "
            "If the change is deliberate, re-record with "
            "`uv run tools/recon_accuracy_check.py ci ... --write-expected` "
            "in the same PR so the diff is reviewed; otherwise fix the matcher."
        )
    _emit(lines)
    return 1 if diffs else 0


def _totals_line(rows: list[dict]) -> str:
    def s(k):
        return sum(int(r[k]) for r in rows)

    inv = all(bool(r["invariant_ok"]) for r in rows)
    comp = round(sum(float(r["composite"]) for r in rows), 2)
    return (
        f"totals: determ_ok={s('determ_ok')}/{s('confirmed')} "
        f"determ_wrong={s('determ_wrong')} deferred_ok={s('deferred_ok')} "
        f"ambiguous={s('ambiguous')} unresolved={s('unresolved')} "
        f"no_charge={s('no_charge')} nc_matched={s('nc_determ_matched')} "
        f"invariant={'OK' if inv else 'BROKEN'} composite={comp}"
    )


# ─── real ──────────────────────────────────────────────────────────────

def _real_stats(scorer, asset: Path) -> tuple[list[dict], dict[str, dict]]:
    """Per-bundle stats for all six real bundles, and per-split totals
    restricted to REAL_FIELDS (each split is a filter over the one run)."""
    root = scorer._fixture_root()
    names = scorer.TRAIN_BUNDLES + scorer.HOLDOUT_BUNDLES
    absent = [n for n in names if not (root / n).is_dir()]
    if absent:
        raise CannotMeasure(
            f"real bundles absent under {root}: {absent} (the labelled "
            "months live in the gitignored client context)"
        )
    cfg = _match_cfg(asset)
    stats = [_score_bundle(scorer, root / n, cfg) for n in names]
    members = {
        "train": set(scorer.TRAIN_BUNDLES),
        "holdout": set(scorer.HOLDOUT_BUNDLES),
        "all": set(names),
    }
    per_split: dict[str, dict] = {}
    for split in SPLITS:
        tot = scorer.totals([s for s in stats if s["bundle"] in members[split]])
        per_split[split] = {f: _round(f, tot[f]) for f in REAL_FIELDS}
    return stats, per_split


def _compare_split(now: dict, base: dict) -> list[str]:
    """The axes on which `now` is worse than `base` (empty = pass)."""
    fails = []
    if float(now["composite"]) < float(base["composite"]):
        fails.append(f"composite {now['composite']} < baseline {base['composite']}")
    if int(now["determ_wrong"]) > int(base["determ_wrong"]):
        fails.append(
            f"determ_wrong {now['determ_wrong']} > baseline {base['determ_wrong']}"
        )
    if int(now["nc_determ_matched"]) > int(base["nc_determ_matched"]):
        fails.append(
            f"nc_determ_matched {now['nc_determ_matched']} > baseline "
            f"{base['nc_determ_matched']}"
        )
    if not now["invariant_ok"]:
        fails.append("reconciliation invariant BROKEN")
    return fails


def _fmt(now, base, key: str) -> str:
    b = "-" if base is None else base.get(key, "-")
    n = now[key]
    if key == "invariant_ok":
        n = "OK" if n else "BROKEN"
        if isinstance(b, bool):
            b = "OK" if b else "BROKEN"
    return f"{b} → {n}" if b != n else f"{n}"


def _real_markdown(stats, per_split, baseline, asset: Path, splits) -> list[str]:
    try:
        asset_label = asset.resolve().relative_to(REPO).as_posix()
    except ValueError:
        asset_label = str(asset)
    lines = [
        "### Recon match accuracy: six real labelled bundles",
        "",
        f"Asset `{asset_label}`; cells read `baseline → now` where they differ.",
        "",
        "| split | composite | determ_ok | determ_wrong | deferred_ok | "
        "nc_matched | invariant |",
        "|---|---|---|---|---|---|---|",
    ]
    for split in splits:
        now = per_split[split]
        base = (baseline or {}).get(split)
        lines.append(
            f"| {split} | {_fmt(now, base, 'composite')} | "
            f"{_fmt(now, base, 'determ_ok')} | {_fmt(now, base, 'determ_wrong')} | "
            f"{_fmt(now, base, 'deferred_ok')} | "
            f"{_fmt(now, base, 'nc_determ_matched')} | "
            f"{_fmt(now, base, 'invariant_ok')} |"
        )
    lines.append("")
    lines.append("Per bundle:")
    for s in stats:
        lines.append(
            f"- `{s['bundle']}`: confirmed={s['confirmed']} "
            f"determ_ok={s['determ_ok']} determ_wrong={s['determ_wrong']} "
            f"deferred_ok={s['deferred_ok']} ambiguous={s['ambiguous']} "
            f"unresolved={s['unresolved']} no_charge={s['no_charge']} "
            f"nc_matched={s['nc_determ_matched']} "
            f"invariant={'OK' if s['invariant_ok'] else 'BROKEN'} "
            f"composite={s['composite']:+.1f}"
        )
    return lines


def cmd_real(args: argparse.Namespace) -> int:
    splits = list(SPLITS) if args.split == "all" and not args.split_given \
        else [args.split]
    asset = Path(args.asset)
    baseline_path = Path(args.baseline)
    scorer = _load_scorer()
    stats, per_split = _real_stats(scorer, asset)

    if args.write_baseline:
        baseline_path.write_text(
            json.dumps({s: per_split[s] for s in SPLITS}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {baseline_path}")
        for split in SPLITS:
            print(f"  {split}: {json.dumps(per_split[split])}")
        return 0

    baseline = None
    if baseline_path.is_file():
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CannotMeasure(f"baseline unreadable: {exc}") from exc
    if args.markdown:
        _emit(_real_markdown(stats, per_split, baseline, asset, splits))
        print()
    if baseline is None:
        raise CannotMeasure(
            f"baseline not found: {baseline_path} "
            "(record it once with --write-baseline)"
        )

    failed = False
    for split in splits:
        base = baseline.get(split)
        if not isinstance(base, dict):
            raise CannotMeasure(f"baseline has no {split!r} split")
        fails = _compare_split(per_split[split], base)
        if fails:
            failed = True
            print(f"FAIL {split}: " + "; ".join(fails))
        else:
            now = per_split[split]
            print(
                f"PASS {split}: composite={now['composite']} "
                f"(baseline {base['composite']}) determ_ok={now['determ_ok']} "
                f"determ_wrong={now['determ_wrong']} "
                f"nc_matched={now['nc_determ_matched']} invariant=OK"
            )
    if failed:
        print(
            "ACCURACY BELOW BASELINE. Fix the matcher, or if the drop is "
            "deliberate re-record with `uv run tools/recon_accuracy_check.py "
            "real --write-baseline` and say why in the PR."
        )
    return 1 if failed else 0


# ─── entry ─────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="recon_accuracy_check.py",
        description="Expense-recon match accuracy: CI gate + deploy check.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    ci = sub.add_parser("ci", help="synthetic bundles vs expected.json (exact)")
    ci.add_argument("--fixtures", required=True)
    ci.add_argument("--expected", required=True)
    ci.add_argument("--asset", default=str(DEFAULT_ASSET))
    ci.add_argument("--write-expected", action="store_true")
    ci.set_defaults(fn=cmd_ci)

    real = sub.add_parser("real", help="real bundles vs the baseline")
    real.add_argument("--split", choices=SPLITS, default="all")
    real.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    real.add_argument("--asset", default=str(DEFAULT_ASSET))
    real.add_argument("--markdown", action="store_true")
    real.add_argument("--write-baseline", action="store_true")
    real.set_defaults(fn=cmd_real)
    return p


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # `real` with no --split reports every split; an explicit --split all
    # reports only the combined one.
    args.split_given = any(a == "--split" or a.startswith("--split=") for a in argv)
    try:
        return args.fn(args)
    except CannotMeasure as exc:
        print(f"ERROR: cannot measure: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
