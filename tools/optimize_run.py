# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Optimize-run engine: deterministic executor of the autoresearch loop.

Backs .claude/commands/comd_optimize.md + rule_optimize_loop.md. The agent
contributes HYPOTHESES and asset edits; this engine executes everything a
fumble could corrupt: branch/commit protocol, scoring under timeout, guard
gating, direction-aware keep/revert, the append-only results.tsv journal,
and per-round hash re-verification of the scorer, manifest, and journal.
Reference: karpathy/autoresearch program.md (loop protocol, results.tsv,
baseline-first, kill rule) + evo (guards discard even on a score win) +
codex-autoresearch ("a plain measurement never stages, commits, or reverts
anything" - the SCORER stays pure; the engine is the experiment executor
around it).

Subcommands:
  start <tag>                          lock-on: branch, manifest commit,
                                       baseline score + guards, state file
  round --desc "<hypothesis>"          one experiment: commit -> score ->
        [--simplification] [--rework]  guards -> keep/revert -> journal
        [--discard]
  resume                               crash/interrupt recovery + repro check
  stop [--reason X]                    final journal row, unlock
  status                               print run state

The repo root is discovered via `git rev-parse --show-toplevel` from CWD, so
the engine runs identically in the real repo, a worktree, or a throwaway
test repo. State lives at <repo>/.claude/optimize/run.json (gitignored),
which the optimize-run-gate hook reads to enforce the file ACL.

Test seam: OPTIMIZE_NOW=<ISO ts> freezes the clock (wall-clock budget tests).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys

import yaml

# The engine imports helper modules (pin_scorer, _globs) from the target
# repo via importlib; without this, Python drops __pycache__/ dirs into the
# repo mid-run, which the engine's own strict dirty-tree check then flags.
sys.dont_write_bytecode = True

TSV_HEADER = "round\tcommit\tscore\tdelta\tstatus\tdescription\n"
SCORE_RE = re.compile(r"^SCORE:\s*(-?\d+(?:\.\d+)?)\s*$", re.MULTILINE)
VALID_MODES = ("converge", "continuous", "supervised")

# Paths that asset globs may never cover (mirror of the gate's machinery
# lock; validated at start so a mis-scoped manifest fails before lock-on).
MACHINERY_PREFIXES = (
    ".claude/hooks/", ".claude/optimize/", "tools/scorers/",
    ".claude/commands/comd_optimize.md", ".claude/rules/rule_optimize_loop.md",
    "tools/wire-hooks.py", "tools/optimize_run.py", "tools/pin_scorer.py",
    "docs/optimize/",
)


def die(msg: str) -> "NoReturn":  # noqa: F821
    print(f"ABORT: {msg}", file=sys.stderr)
    sys.exit(1)


def _now() -> _dt.datetime:
    seam = os.environ.get("OPTIMIZE_NOW")
    if seam:
        return _dt.datetime.fromisoformat(seam)
    return _dt.datetime.now()


def repo_root() -> str:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        die("not inside a git repository")
    return proc.stdout.strip()


def git(repo: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", repo, *args],
                          capture_output=True, text=True)
    if check and proc.returncode != 0:
        die(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc


def current_branch(repo: str) -> str:
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def head_sha(repo: str) -> str:
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def _load_module(repo: str, rel: str, name: str):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(repo, *rel.split("/")))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pin_helpers(repo: str):
    return _load_module(repo, "tools/pin_scorer.py", "pin_scorer")


def globs_helper(repo: str):
    return _load_module(repo, ".claude/hooks/_globs.py", "_globs")


def state_path(repo: str) -> str:
    return os.path.join(repo, ".claude", "optimize", "run.json")


def load_state(repo: str) -> dict | None:
    p = state_path(repo)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        die(f"run state {p} is unparseable; repair or delete it (that file "
            "is engine-owned - its corruption is a harness event)")


def save_state(repo: str, state: dict) -> None:
    p = state_path(repo)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, p)


def tsv_path(repo: str, tag: str) -> str:
    return os.path.join(repo, "docs", "optimize", tag, "results.tsv")


def tsv_anchors(path: str) -> tuple[int, str]:
    with open(path, "rb") as f:
        data = f.read()
    return data.count(b"\n"), hashlib.sha256(data).hexdigest()


def verify_tsv(repo: str, state: dict) -> None:
    lines, sha = tsv_anchors(tsv_path(repo, state["tag"]))
    if lines != state["tsv_lines"] or sha != state["tsv_sha256"]:
        die("results.tsv was modified outside the engine (append-only "
            "integrity anchor mismatch). This is a harness event - surface "
            "it to the user; do not continue the run.")


def append_tsv(repo: str, state: dict, row: list[str]) -> None:
    verify_tsv(repo, state)
    path = tsv_path(repo, state["tag"])
    clean = [str(c).replace("\t", " ").replace("\n", " ") for c in row]
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(clean) + "\n")
    state["tsv_lines"], state["tsv_sha256"] = tsv_anchors(path)


def parse_manifest(repo: str, tag: str) -> dict:
    mpath = os.path.join(repo, "docs", "optimize", tag, "RUN.md")
    if not os.path.isfile(mpath):
        die(f"manifest not found: docs/optimize/{tag}/RUN.md")
    with open(mpath, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not m:
        die("manifest has no YAML frontmatter block")
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        die(f"manifest frontmatter is invalid YAML: {e}")
    if not isinstance(meta, dict):
        die("manifest frontmatter is not a mapping")
    return meta


def blob_sha_of(repo: str, rel: str) -> str:
    return pin_helpers(repo).blob_sha(os.path.join(repo, *rel.split("/")))


def validate_manifest(repo: str, tag: str, meta: dict) -> dict:
    """Cross-check manifest vs PINS vs scorer header; return normalized run."""
    ph = pin_helpers(repo)
    gl = globs_helper(repo)

    if meta.get("tag") != tag:
        die(f"manifest tag {meta.get('tag')!r} != directory tag {tag!r}")
    scorer = str(meta.get("scorer", "")).replace("\\", "/")
    scorer_abs = os.path.join(repo, *scorer.split("/"))
    if not scorer.startswith("tools/scorers/") or not os.path.isfile(scorer_abs):
        die(f"scorer {scorer!r} missing or not under tools/scorers/")
    scorer_name = scorer.rsplit("/", 1)[1]

    pins_file = os.path.join(repo, "tools", "scorers", "PINS.json")
    try:
        with open(pins_file, encoding="utf-8") as f:
            pins = json.load(f)
    except Exception:
        die("tools/scorers/PINS.json missing or unparseable")
    pin = pins.get(scorer_name)
    if not pin:
        die(f"scorer {scorer_name} is not pinned in PINS.json (build + pin "
            "the scorer via its own PR first; see docs/optimize/RECIPES.md)")
    live_sha = ph.blob_sha(scorer_abs)
    if live_sha != pin.get("sha"):
        die(f"scorer {scorer_name} live hash {live_sha[:12]} != pinned "
            f"{str(pin.get('sha'))[:12]} - re-pin via pin_scorer.py under "
            "user approval before running")
    header_dir = ph.scorer_direction(scorer_abs)
    direction = meta.get("direction")
    if not (header_dir == pin.get("direction") == direction):
        die(f"direction mismatch: header={header_dir} pin={pin.get('direction')} "
            f"manifest={direction}")

    assets = [str(a).replace("\\", "/") for a in (meta.get("assets") or [])]
    if not assets:
        die("manifest declares no asset globs")
    for a in assets:
        for mp in MACHINERY_PREFIXES:
            probe = mp.rstrip("/") + ("/x" if mp.endswith("/") else "")
            if gl.match_one(a, probe) or gl.match_one(a, mp.rstrip("/")):
                die(f"asset glob {a!r} covers locked machinery path {mp!r}")

    guards = [str(g) for g in (meta.get("guards") or [])]
    guard_files = [str(g).replace("\\", "/") for g in (meta.get("guard_files") or [])]
    for gf in guard_files:
        if not os.path.isfile(os.path.join(repo, *gf.split("/"))):
            die(f"guard_files entry not found: {gf}")

    budgets = dict(meta.get("budgets") or {})
    budgets.setdefault("rounds", 10)
    budgets.setdefault("wall_clock_minutes", 240)
    budgets.setdefault("score_timeout_seconds", 300)
    budgets.setdefault("max_rework_attempts", 2)
    mode = meta.get("mode", "converge")
    if mode not in VALID_MODES:
        die(f"mode {mode!r} not one of {VALID_MODES}")
    stop = dict(meta.get("stop") or {})
    stop.setdefault("consecutive_reverts", 5)

    scorer_args = [str(a) for a in (meta.get("scorer_args") or [])]
    return {
        "tag": tag,
        "branch": f"optimize/{tag}",
        "manifest": f"docs/optimize/{tag}/RUN.md",
        "scorer": scorer,
        "scorer_args": scorer_args,
        "direction": direction,
        "assets": assets,
        "guards": guards,
        "locked": [f"docs/optimize/{tag}/RUN.md",
                   f"docs/optimize/{tag}/results.tsv", *guard_files],
        "budgets": budgets,
        "mode": mode,
        "stop": stop,
    }


def run_scorer(repo: str, state: dict, log_name: str) -> tuple[float | None, str]:
    """Run the pinned scorer under timeout. (score, status) status in
    {'ok','crash','timeout'}. Full output -> docs/optimize/<tag>/logs/."""
    timeout = int(state["budgets"]["score_timeout_seconds"])
    cmd = ["uv", "run", state["scorer"], *state["scorer_args"]]
    kwargs: dict = {}
    if os.name != "nt":
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, cwd=repo, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, **kwargs)
    try:
        out, _ = proc.communicate(timeout=timeout)
        status = "ok" if proc.returncode == 0 else "crash"
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True)
        else:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        out, _ = proc.communicate()
        status = "timeout"

    log_dir = os.path.join(repo, "docs", "optimize", state["tag"], "logs")
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, log_name), "w", encoding="utf-8",
              errors="replace", newline="\n") as f:
        f.write(out or "")

    if status != "ok":
        return None, status
    matches = SCORE_RE.findall(out or "")
    if not matches:
        return None, "crash"
    return float(matches[-1]), "ok"


def run_guards(repo: str, state: dict, log_prefix: str) -> tuple[bool, str]:
    """Run guard commands (argv, no shell). (all_passed, first_failed_cmd)."""
    timeout = int(state["budgets"]["score_timeout_seconds"])
    for i, cmd in enumerate(state["guards"]):
        argv = shlex.split(cmd, posix=True)
        try:
            proc = subprocess.run(argv, cwd=repo, capture_output=True,
                                  text=True, timeout=timeout)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            _log_guard(repo, state, f"{log_prefix}-guard{i}.log", str(e))
            return False, cmd
        _log_guard(repo, state, f"{log_prefix}-guard{i}.log",
                   (proc.stdout or "") + (proc.stderr or ""))
        if proc.returncode != 0:
            return False, cmd
    return True, ""


def _log_guard(repo: str, state: dict, name: str, content: str) -> None:
    log_dir = os.path.join(repo, "docs", "optimize", state["tag"], "logs")
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, name), "w", encoding="utf-8",
              errors="replace", newline="\n") as f:
        f.write(content)


def improved(state: dict, score: float, allow_equal: bool) -> bool:
    best = state["best_score"]
    if state["direction"] == "minimize":
        return score < best or (allow_equal and score == best)
    return score > best or (allow_equal and score == best)


def changed_asset_files(repo: str, state: dict) -> list[str]:
    """Dirty files; abort if any dirty path is outside the asset globs."""
    gl = globs_helper(repo)
    proc = git(repo, "status", "--porcelain")
    changed, foreign = [], []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].split(" -> ")[-1].strip().strip('"')
        rel = path.replace("\\", "/")
        if gl.matches_any(state["assets"], rel):
            changed.append(rel)
        else:
            foreign.append(rel)
    if foreign:
        die(f"working tree has changes OUTSIDE the asset scope: {foreign}. "
            "The gate should have prevented this - treat as a harness event; "
            "clean or stash those paths, then re-run.")
    return changed


def verify_harness_hashes(repo: str, state: dict) -> None:
    live_scorer = blob_sha_of(repo, state["scorer"])
    with open(os.path.join(repo, "tools", "scorers", "PINS.json"),
              encoding="utf-8") as f:
        pins = json.load(f)
    pin_sha = (pins.get(state["scorer"].rsplit("/", 1)[1]) or {}).get("sha")
    if not (live_scorer == state["scorer_sha"] == pin_sha):
        die(f"scorer hash drift mid-run (live={live_scorer[:12]} "
            f"state={state['scorer_sha'][:12]} pin={str(pin_sha)[:12]}). "
            "A tampered metric can never yield an accepted round.")
    live_manifest = blob_sha_of(repo, state["manifest"])
    if live_manifest != state["manifest_sha"]:
        die("manifest (RUN.md) hash drift mid-run - the instructions file is "
            "locked for the duration of the run.")


def check_budgets(state: dict) -> str | None:
    if state["round"] >= int(state["budgets"]["rounds"]):
        return "ROUNDS EXHAUSTED"
    started = _dt.datetime.fromisoformat(state["started_at"])
    elapsed_min = (_now() - started).total_seconds() / 60.0
    if elapsed_min > float(state["budgets"]["wall_clock_minutes"]):
        return "WALL-CLOCK EXHAUSTED"
    return None


def announce_stops(state: dict) -> list[str]:
    notes = []
    goal = state["stop"].get("goal_score")
    if goal is not None and state["best_score"] is not None:
        hit = (state["best_score"] <= goal if state["direction"] == "minimize"
               else state["best_score"] >= goal)
        if hit:
            notes.append(f"GOAL REACHED ({state['best_score']} vs {goal})")
    limit = int(state["stop"]["consecutive_reverts"])
    if state["consecutive_non_keeps"] >= limit:
        notes.append(f"PLATEAU ({state['consecutive_non_keeps']} consecutive "
                     "non-keeps)"
                     + ("" if state["mode"] == "continuous"
                        else " - stop the run"))
    b = check_budgets(state)
    if b:
        notes.append(b)
    return notes


# ---------------------------------------------------------------- commands --

def cmd_start(tag: str) -> int:
    repo = repo_root()
    if load_state(repo) is not None:
        die("a run is already active (.claude/optimize/run.json exists); "
            "one run at a time - `resume` it or `stop` it first")
    # Clean tree required (revert must be exact) - EXCEPT the run's own
    # docs/optimize/<tag>/ files, which the setup interview just wrote and
    # which lock-on is about to commit.
    run_prefix = f"docs/optimize/{tag}/"
    dirty = [ln[3:].strip().strip('"').replace("\\", "/")
             for ln in git(repo, "status", "--porcelain").stdout.splitlines()
             if ln.strip()]
    foreign_dirty = [p for p in dirty if not p.startswith(run_prefix)]
    if foreign_dirty:
        die(f"working tree not clean outside {run_prefix}: {foreign_dirty} - "
            "commit or stash before start (revert must be exact)")
    meta = parse_manifest(repo, tag)
    state = validate_manifest(repo, tag, meta)
    branch = state["branch"]
    if git(repo, "rev-parse", "--verify", branch, check=False).returncode == 0:
        die(f"branch {branch} already exists - runs are fresh (Karpathy setup "
            "rule); pick a new tag")

    gl = globs_helper(repo)
    resolved = []
    for dirpath, _dirs, files in os.walk(repo):
        rel_dir = os.path.relpath(dirpath, repo).replace("\\", "/")
        if rel_dir.startswith((".git", ".claude/optimize")):
            continue
        for fn in files:
            rel = (fn if rel_dir == "." else f"{rel_dir}/{fn}")
            if gl.matches_any(state["assets"], rel):
                resolved.append(rel)
    if not resolved:
        print("WARNING: asset globs currently match zero files.")

    # Score + guard the baseline BEFORE creating anything: a broken harness
    # must leave no branch, no commit, no state behind.
    state.update({
        "started_at": _now().isoformat(timespec="seconds"),
        "round": 0, "best_score": None, "consecutive_non_keeps": 0,
        "rework_count": 0,
    })
    score, status = run_scorer(repo, state, "r0.log")
    if status != "ok":
        die(f"baseline scoring failed ({status}) - the harness is broken; "
            f"never start a run on a guessed score (docs/optimize/{tag}/"
            "logs/r0.log)")
    ok, failed = run_guards(repo, state, "r0")
    if not ok:
        die(f"baseline guard failed: {failed!r} - a run cannot enforce "
            "'discard on guard-fail' from a baseline that already fails")

    git(repo, "checkout", "-b", branch)
    git(repo, "add", "--", state["manifest"])
    if git(repo, "diff", "--cached", "--quiet", check=False).returncode != 0:
        git(repo, "commit", "-m", f"experiment({tag}): lock-on: run manifest")

    tsvp = tsv_path(repo, tag)
    with open(tsvp, "w", encoding="utf-8", newline="\n") as f:
        f.write(TSV_HEADER)
    state.update({
        "scorer_sha": blob_sha_of(repo, state["scorer"]),
        "manifest_sha": blob_sha_of(repo, state["manifest"]),
        "tsv_lines": 1, "tsv_sha256": tsv_anchors(tsvp)[1],
    })
    state["best_score"] = score
    append_tsv(repo, state, ["0", head_sha(repo)[:7], f"{score}", "0",
                             "baseline", "baseline (asset as-is)"])
    git(repo, "add", "--", f"docs/optimize/{tag}/results.tsv")
    git(repo, "commit", "-m", f"experiment({tag}): r0 baseline SCORE={score}")
    state["base_sha"] = head_sha(repo)
    save_state(repo, state)

    print(f"LOCK-ON: run '{tag}' active on {branch}")
    print(f"baseline: SCORE={score} ({state['direction']})")
    print(f"assets ({len(resolved)} file(s) resolve): "
          + ", ".join(resolved[:10]) + (" ..." if len(resolved) > 10 else ""))
    print(f"locked: manifest, journal, guards, scorers, machinery "
          f"(rule_optimize_loop.md). budgets: {state['budgets']}")
    return 0


def _refuse_off_branch(repo: str, state: dict) -> None:
    br = current_branch(repo)
    if br in ("main", "master"):
        die("engine never operates on main/master")
    if br != state["branch"]:
        die(f"current branch {br!r} != run branch {state['branch']!r}; "
            f"`git checkout {state['branch']}` first (or resume)")


def cmd_round(desc: str, simplification: bool, rework: bool,
              forced_discard: bool) -> int:
    repo = repo_root()
    state = load_state(repo)
    if state is None:
        die("no active run - `start <tag>` first")
    _refuse_off_branch(repo, state)
    if not desc or not desc.strip():
        die("--desc is required: one-sentence hypothesis for the journal")

    if not rework:
        if head_sha(repo) != state["base_sha"]:
            die("HEAD != last kept state - the tree drifted (crash?). "
                "Run `resume`.")
        stop_reason = check_budgets(state)
        if stop_reason:
            die(f"{stop_reason} - `stop` the run "
                f"(or raise the budget in a NEW run)")
    verify_harness_hashes(repo, state)
    verify_tsv(repo, state)

    changed = changed_asset_files(repo, state)
    if not changed:
        die("no asset change to test - edit files inside the asset scope "
            "first (one hypothesis, one change)")

    n = state["round"] + 1
    if rework:
        state["rework_count"] += 1
        if state["rework_count"] > int(state["budgets"]["max_rework_attempts"]):
            git(repo, "reset", "--hard", state["base_sha"])
            append_tsv(repo, state, [str(n), "-", "NA", "NA", "guard_fail",
                                     f"{desc} (rework attempts exhausted)"])
            git(repo, "add", "--", f"docs/optimize/{state['tag']}/results.tsv")
            git(repo, "commit", "-m",
                f"experiment({state['tag']}): r{n} journal (guard_fail, "
                "rework cap)")
            state["base_sha"] = head_sha(repo)
            state["round"] = n
            state["consecutive_non_keeps"] += 1
            state["rework_count"] = 0
            save_state(repo, state)
            print(f"r{n}: DISCARDED (rework attempts exhausted)")
            return 0
    else:
        state["rework_count"] = 0

    for f_rel in changed:
        git(repo, "add", "--", f_rel)
    label = f"r{n} rework {state['rework_count']}" if rework else f"r{n}"
    git(repo, "commit", "-m", f"experiment({state['tag']}): {label}: {desc}")
    exp_sha = head_sha(repo)

    score, status = run_scorer(repo, state, f"r{n}.log")
    verdict: str
    if status != "ok":
        verdict = "crash"
    elif forced_discard:
        verdict = "discard"
    elif improved(state, score, allow_equal=simplification):
        ok, failed_guard = run_guards(repo, state, f"r{n}")
        if ok:
            verdict = "keep"
        else:
            verdict = "guard_fail"
            print(f"guard failed: {failed_guard!r} (see logs/r{n}-guard*.log). "
                  f"You may fix WITHIN this round: edit assets, then "
                  f"`round --rework --desc \"...\"` "
                  f"({state['rework_count']}/{state['budgets']['max_rework_attempts']} used).")
    else:
        verdict = "discard"

    if verdict == "keep":
        prior_best = state["best_score"]
        state["best_score"] = score
        state["base_sha"] = exp_sha
        state["consecutive_non_keeps"] = 0
        state["rework_count"] = 0
        delta = f"{score - prior_best:+g}"
    else:
        if verdict == "guard_fail" and \
                state["rework_count"] < int(state["budgets"]["max_rework_attempts"]):
            # leave the experiment commit in place for the in-round rework
            save_state(repo, state)
            return 0
        git(repo, "reset", "--hard", state["base_sha"])
        state["consecutive_non_keeps"] += 1
        state["rework_count"] = 0
        delta = "NA"

    score_txt = "NA" if score is None else f"{score}"
    append_tsv(repo, state, [str(n), exp_sha[:7], score_txt, delta,
                             verdict, desc])
    git(repo, "add", "--", f"docs/optimize/{state['tag']}/results.tsv")
    git(repo, "commit", "-m",
        f"experiment({state['tag']}): r{n} journal ({verdict})")
    state["base_sha"] = head_sha(repo)
    state["round"] = n
    save_state(repo, state)

    print(f"r{n}: {verdict.upper()}"
          + (f" SCORE={score} (best={state['best_score']}, delta={delta})"
             if score is not None else " (no score - see logs)"))
    print(f"budget: round {n}/{state['budgets']['rounds']}, "
          f"non-keep streak {state['consecutive_non_keeps']}")
    for note in announce_stops(state):
        print(f"STOP-CONDITION: {note}")
    return 0


def cmd_resume() -> int:
    repo = repo_root()
    state = load_state(repo)
    if state is None:
        die("no active run to resume")
    if current_branch(repo) != state["branch"]:
        git(repo, "checkout", state["branch"])

    if git(repo, "status", "--porcelain").stdout.strip():
        print("dirty tree from interrupted round - restoring last kept state")
        git(repo, "reset", "--hard", state["base_sha"])
    elif head_sha(repo) != state["base_sha"]:
        n = state["round"] + 1
        print(f"interrupted between experiment commit and journal - "
              f"logging r{n} as crash and restoring")
        interrupted = head_sha(repo)[:7]
        git(repo, "reset", "--hard", state["base_sha"])
        append_tsv(repo, state, [str(n), interrupted, "NA", "NA", "crash",
                                 "interrupted (resume recovery)"])
        git(repo, "add", "--", f"docs/optimize/{state['tag']}/results.tsv")
        git(repo, "commit", "-m",
            f"experiment({state['tag']}): r{n} journal (crash/interrupted)")
        state["base_sha"] = head_sha(repo)
        state["round"] = n
        state["consecutive_non_keeps"] += 1

    verify_harness_hashes(repo, state)
    verify_tsv(repo, state)
    score, status = run_scorer(repo, state, "resume-repro.log")
    if status != "ok" or score != state["best_score"]:
        print(f"REPRODUCIBILITY MISMATCH: re-scored {score} ({status}) vs "
              f"recorded best {state['best_score']}. Environment drift - "
              "surface this to the user before continuing; scores across the "
              "drift boundary are not comparable.")
    else:
        print(f"reproducibility check OK (SCORE={score})")
    save_state(repo, state)
    b = check_budgets(state)
    print(f"resumed run '{state['tag']}' at round {state['round']}, "
          f"best={state['best_score']}" + (f" [{b}]" if b else ""))
    return 0


def cmd_stop(reason: str) -> int:
    repo = repo_root()
    state = load_state(repo)
    if state is None:
        die("no active run to stop")
    if current_branch(repo) != state["branch"]:
        if git(repo, "checkout", state["branch"], check=False).returncode != 0:
            # Run branch is gone: nothing to journal onto. Unlock anyway -
            # a stale lock must never require hand-editing the state file.
            os.remove(state_path(repo))
            print(f"run '{state['tag']}' branch missing; state cleared, "
                  "locks OFF (no final journal row - branch was deleted).")
            return 0
    if current_branch(repo) in ("main", "master"):
        die("engine never operates on main/master")
    if git(repo, "status", "--porcelain").stdout.strip():
        git(repo, "reset", "--hard", state["base_sha"])
    append_tsv(repo, state, [str(state["round"] + 1), "-", "NA", "NA",
                             "stopped", reason or "user stop"])
    git(repo, "add", "--", f"docs/optimize/{state['tag']}/results.tsv")
    git(repo, "commit", "-m",
        f"experiment({state['tag']}): stopped ({reason or 'user stop'})")
    os.remove(state_path(repo))
    print(f"run '{state['tag']}' stopped after {state['round']} round(s); "
          f"best={state['best_score']} ({state['direction']}). Locks OFF.")
    print("Ship checklist: write SUMMARY.md from results.tsv, push the "
          "branch, open the PR (normal B6 bands). Dead ends ship the "
          "journal alone.")
    return 0


def cmd_status() -> int:
    repo = repo_root()
    state = load_state(repo)
    if state is None:
        print("no active optimize run")
        return 0
    print(json.dumps({k: state[k] for k in
                      ("tag", "branch", "mode", "round", "best_score",
                       "consecutive_non_keeps", "started_at", "budgets")},
                     indent=2))
    for note in announce_stops(state):
        print(f"STOP-CONDITION: {note}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="optimize-run engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start"); p.add_argument("tag")
    p = sub.add_parser("round")
    p.add_argument("--desc", required=True)
    p.add_argument("--simplification", action="store_true")
    p.add_argument("--rework", action="store_true")
    p.add_argument("--discard", action="store_true")
    sub.add_parser("resume")
    p = sub.add_parser("stop"); p.add_argument("--reason", default="")
    sub.add_parser("status")
    args = ap.parse_args()
    if args.cmd == "start":
        return cmd_start(args.tag)
    if args.cmd == "round":
        return cmd_round(args.desc, args.simplification, args.rework,
                         args.discard)
    if args.cmd == "resume":
        return cmd_resume()
    if args.cmd == "stop":
        return cmd_stop(args.reason)
    return cmd_status()


if __name__ == "__main__":
    sys.exit(main())
