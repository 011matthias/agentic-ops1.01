#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Behavioral eval harness for the fixture-backed subagents.

Turns the manual invoke-and-compare procedures in tools/fixtures/agnt_*/
into a runnable before/after measurement:

    uv run tools/eval-agents.py list
    uv run tools/eval-agents.py run   [--fixture ID] [--model sonnet] [--n 1]
                                      [--repo PATH] [--label NAME]
    uv run tools/eval-agents.py grade RUN_DIR
    uv run tools/eval-agents.py compare RUN_A RUN_B

`run` (PAID, local-only) composes each fixture's agent .md + an invocation
preamble + the SANITIZED fixture (the `## Expected agent behavior` answer key
is stripped -- feeding it verbatim would leak the rubric) and invokes headless
`claude -p` from a NEUTRAL cwd. Transcripts land in the gitignored
.scratch/evals/{run-id}/ -- they can quote memory-file content and are never
committed. `grade` (FREE, deterministic) applies the per-fixture regex
contracts below and writes grades.json. `compare` diffs two grade sets and
exits 1 on a green->red regression -- the before/after gate for rule/prompt
PRs (generate the base run with --repo <base worktree>).

WHY LOCAL-ONLY: intent-reviewer/comms-critic read machine-local memory files
outside the repo; a CI runner without them would exercise the agents'
degraded missing-memory path, i.e. measure the wrong system. (Plus the org's
30k-ITPM sonnet cap and the 2026-06-26 spend-cap incident.) CI runs only the
deterministic grader over synthetic samples (tools/tests/test_agnt_evals.py).

VERIFIED CLI FACTS (spike 2026-07-10, claude 2.1.205, VS Code native binary):
- binary: newest %USERPROFILE%/.vscode/extensions/anthropic.claude-code-*/
  resources/native-binary/claude.exe; override with EVAL_CLAUDE_EXE.
- flags: -p, --model, --allowedTools "A,B", --output-format json. There is
  NO --max-turns on 2.1.205; the cap is the subprocess timeout (300 s).
- result JSON: {type:"result", result, total_cost_usd, num_turns, usage,...}.
- NEUTRAL CWD must be OUTSIDE %TEMP%/claude/<project-slug>: a probe from the
  project scratchpad still auto-loaded repo CLAUDE.md + MEMORY.md; from
  %TEMP%/agentic-eval-* it loaded neither (probe-verified both ways).
- never set ANTHROPIC_API_KEY (subscription billing; a set key flips to API).
- stdin=DEVNULL (avoids the CLI's 3 s stdin wait).

Flake policy: default --n 1; verdicts GREEN (all gens pass) / RED (all fail)
/ FLAKY (mixed) / SKIPPED-ENV (missing env, never RED for environment
reasons). A suspected regression re-runs that fixture with --n 3; treat as
RED only if <=1/3 pass. Grading is shape/tag-level ONLY: fabricated-but-
well-formed findings are out of deterministic scope (documented limitation;
an LLM-judge pass is a v2 candidate, not stubbed).
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MEMORY_DIR = Path(
    r"C:\Users\neuma_p1qrsic\.claude\projects"
    r"\c--Users-neuma-p1qrsic-Repo-agentic-ops1\memory"
)
EVALS_HOME = ".scratch/evals"
ANSWER_KEY_RX = re.compile(r"^##\s+Expected agent behavior\s*$", re.MULTILINE)
GEN_TIMEOUT_S = 300

# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

def _preamble_intent(repo: Path, fixture_abs: str) -> str:
    return (
        "You are being invoked headlessly as the agnt_intent-reviewer subagent. "
        "Your instructions follow after '=== AGENT INSTRUCTIONS ==='. Inputs:\n"
        f"- plan_path: {fixture_abs} (the file contains the Context, User input, "
        "and Proposed plan sections)\n"
        f"- Repo root: {repo} -- resolve every repo-relative reference "
        "(.claude/rules/rule_behaviors.md etc.) against it via absolute paths.\n"
        f"- Memory directory: {MEMORY_DIR}\n"
        "Your final printed output must follow the agent's output contract "
        "EXACTLY (either the single line OK or the '## Intent findings' shape). "
        "No preamble, no commentary."
    )


def _preamble_comms(repo: Path, fixture_abs: str) -> str:
    return (
        "You are being invoked headlessly as the agnt_comms-critic subagent. "
        "Your instructions follow after '=== AGENT INSTRUCTIONS ==='. Inputs:\n"
        f"- draft_path: {fixture_abs}\n"
        "- client: _fixture-comms-critic (this client folder does NOT exist; "
        "the comms-log and sibling-draft checks are expected to be inert -- "
        "do not invent log content)\n"
        f"- Repo root: {repo} -- run the validate-output.py step as "
        f"`uv run --directory \"{repo}\" tools/validate-output.py <draft_path> "
        "--format json` and resolve every repo-relative path against the root.\n"
        f"- Memory directory: {MEMORY_DIR}\n"
        "Your final printed output must follow the agent's output contract "
        "EXACTLY (either the single line OK or the '## Critic findings' shape). "
        "No preamble, no commentary."
    )


def _preamble_research(repo: Path, fixture_abs: str) -> str:
    return (
        "You are being invoked headlessly as the agnt_proposal-research subagent. "
        "Your instructions follow after '=== AGENT INSTRUCTIONS ==='. Inputs:\n"
        "- prospect_name: Vague Prospect\n"
        f"- job_posting: {fixture_abs}\n"
        "- track_hint: none\n"
        f"- Repo root: {repo} -- resolve repo-relative references against it.\n"
        "WebFetch is NOT available in this run; do not attempt external research. "
        "Your final printed output must follow the agent's output contract "
        "EXACTLY. No preamble, no commentary."
    )


EVAL_SUITE: dict[str, dict] = {
    "intent-clean": {
        "agent_md": ".claude/agents/agnt_intent-reviewer.md",
        "fixture": "tools/fixtures/agnt_intent-reviewer/test-clean.md",
        "tools": "Read,Grep,Glob",
        "preamble": _preamble_intent,
        "grader": "grade_exact_ok",
    },
    "intent-violations": {
        "agent_md": ".claude/agents/agnt_intent-reviewer.md",
        "fixture": "tools/fixtures/agnt_intent-reviewer/test-violations.md",
        "tools": "Read,Grep,Glob",
        "preamble": _preamble_intent,
        "grader": "grade_intent_violations",
    },
    "comms-clean": {
        "agent_md": ".claude/agents/agnt_comms-critic.md",
        "fixture": "tools/fixtures/agnt_comms-critic/test-clean.md",
        "tools": "Read,Grep,Glob,Bash",
        "preamble": _preamble_comms,
        "grader": "grade_exact_ok",
    },
    "comms-violations": {
        "agent_md": ".claude/agents/agnt_comms-critic.md",
        "fixture": "tools/fixtures/agnt_comms-critic/test-violations.md",
        "tools": "Read,Grep,Glob,Bash",
        "preamble": _preamble_comms,
        "grader": "grade_comms_violations",
    },
    "research-blocked": {
        "agent_md": ".claude/agents/agnt_proposal-research.md",
        "fixture": "tools/fixtures/agnt_proposal-research/posting-blocked-empty.txt",
        "tools": "Read,Grep,Glob",
        "preamble": _preamble_research,
        "grader": "grade_research_blocked",
    },
}

# --------------------------------------------------------------------------
# Composition
# --------------------------------------------------------------------------

def sanitize_fixture(text: str) -> str:
    """Truncate at the '## Expected agent behavior' answer key (and a
    preceding --- rule, if any). Feeding the rubric to the model under eval
    invalidates the eval."""
    m = ANSWER_KEY_RX.search(text)
    if not m:
        return text
    cut = text[: m.start()]
    cut = re.sub(r"\n---\s*\n?\s*$", "\n", cut)
    return cut.rstrip() + "\n"


def strip_frontmatter(md: str) -> str:
    if md.startswith("---"):
        end = md.find("\n---", 3)
        if end != -1:
            return md[end + 4:].lstrip("\n")
    return md


def compose_prompt(repo: Path, spec: dict, fixture_abs: str) -> str:
    agent_md = (repo / spec["agent_md"]).read_text(encoding="utf-8")
    return (
        spec["preamble"](repo, fixture_abs)
        + "\n\n=== AGENT INSTRUCTIONS ===\n\n"
        + strip_frontmatter(agent_md)
    )

# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def find_claude_exe() -> str | None:
    if os.environ.get("EVAL_CLAUDE_EXE"):
        return os.environ["EVAL_CLAUDE_EXE"]
    pattern = os.path.expanduser(
        "~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude.exe"
    )
    hits = sorted(glob.glob(pattern))
    return hits[-1] if hits else None


def preflight(repo: Path, spec: dict) -> list[str]:
    """Environment problems -> SKIPPED-ENV (never RED for env reasons)."""
    problems = []
    if not (repo / spec["agent_md"]).is_file():
        problems.append(f"agent md missing: {spec['agent_md']}")
    if not (repo / spec["fixture"]).is_file():
        problems.append(f"fixture missing: {spec['fixture']}")
    if not MEMORY_DIR.is_dir():
        problems.append(f"memory dir missing: {MEMORY_DIR}")
    if find_claude_exe() is None:
        problems.append("claude.exe not found (set EVAL_CLAUDE_EXE)")
    return problems


def neutral_cwd(run_id: str) -> Path:
    # MUST be outside %TEMP%/claude/<project-slug> (see module docstring).
    d = Path(tempfile.gettempdir()) / f"agentic-eval-{run_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_one(exe: str, repo: Path, fid: str, spec: dict, gen_dir: Path,
            model: str, cwd: Path) -> dict:
    fixture_raw = (repo / spec["fixture"]).read_text(encoding="utf-8")
    sanitized = sanitize_fixture(fixture_raw)
    gen_dir.mkdir(parents=True, exist_ok=True)
    input_path = gen_dir / ("input" + Path(spec["fixture"]).suffix)
    input_path.write_text(sanitized, encoding="utf-8", newline="\n")

    prompt = compose_prompt(repo, spec, str(input_path.resolve()))
    (gen_dir / "prompt.md").write_text(prompt, encoding="utf-8", newline="\n")

    argv = [exe, "-p", prompt, "--allowedTools", spec["tools"],
            "--output-format", "json", "--model", model]
    meta: dict = {"argv_tail": argv[2:4] + argv[4:], "attempts": 0}
    for attempt in (1, 2):  # one automatic retry on hard failure
        meta["attempts"] = attempt
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True, encoding="utf-8",
                timeout=GEN_TIMEOUT_S, cwd=str(cwd), stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            meta["error"] = f"timeout {GEN_TIMEOUT_S}s"
            continue
        try:
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception:
            meta["error"] = f"json parse failed (exit {proc.returncode})"
            meta["stderr_tail"] = (proc.stderr or "")[-500:]
            continue
        meta.pop("error", None)
        (gen_dir / "raw.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8", newline="\n")
        transcript = payload.get("result") or ""
        (gen_dir / "transcript.md").write_text(
            transcript, encoding="utf-8", newline="\n")
        meta.update(
            cost_usd=payload.get("total_cost_usd"),
            num_turns=payload.get("num_turns"),
            session_id=payload.get("session_id"),
        )
        return meta
    (gen_dir / "transcript.md").write_text("", encoding="utf-8")
    return meta


def cmd_run(args) -> int:
    repo = Path(args.repo).resolve() if args.repo else REPO
    exe = find_claude_exe()
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        rev = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                    capture_output=True, text=True, timeout=10).stdout.strip())
    except Exception:
        rev, dirty = "unknown", False
    run_id = f"{ts}-{rev}" + (f"-{args.label}" if args.label else "")
    run_dir = REPO / EVALS_HOME / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    cwd = neutral_cwd(run_id)

    selected = {args.fixture: EVAL_SUITE[args.fixture]} if args.fixture else EVAL_SUITE
    run_meta = {"run_id": run_id, "repo": str(repo), "git_rev": rev,
                "dirty": dirty, "model": args.model, "n": args.n,
                "claude_exe": exe, "fixtures": {}}
    for fid, spec in selected.items():
        problems = preflight(repo, spec)
        if problems:
            run_meta["fixtures"][fid] = {"skipped_env": problems}
            print(f"[{fid}] SKIPPED-ENV: {'; '.join(problems)}")
            continue
        gens = []
        for i in range(1, args.n + 1):
            print(f"[{fid}] gen{i}/{args.n} ...", flush=True)
            gens.append(run_one(exe, repo, fid, spec,
                                run_dir / fid / f"gen{i}", args.model, cwd))
        run_meta["fixtures"][fid] = {"generations": gens}
    (run_dir / "run.json").write_text(
        json.dumps(run_meta, indent=2), encoding="utf-8", newline="\n")
    print(f"run dir: {run_dir}")
    return 0

# --------------------------------------------------------------------------
# Graders -- shape/tag-level, deterministic. Each returns [(name, ok, detail)].
# --------------------------------------------------------------------------

SEV = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
ITEM_RX = re.compile(r"^\d+\.\s+\[(HIGH|MEDIUM|LOW)\]\s+\[([a-z0-9-]+)\]", re.MULTILINE)

INTENT_REQUIRED = [
    ("HIGH", "exploratory-as-directive"),
    ("HIGH", "example-as-spec"),
    ("MEDIUM", "strategic-bypass"),
    ("HIGH", "re-ask-of-stated"),
    ("MEDIUM", "paraphrase-drift"),
    ("HIGH", "posture-mismatch"),
    ("HIGH", "unsourced-identity-or-limitation-claim"),
]
COMMS_REQUIRED = [
    ("HIGH", "imperative-tone"),
    ("HIGH", "pre-concession"),
    ("HIGH", "unsourced-identity-claim"),
    ("MEDIUM", "closing-offer"),
]


def _first_line(t: str) -> str:
    for ln in t.splitlines():
        if ln.strip():
            return ln.strip()
    return ""


def _findings_checks(t: str, header_word: str, required, min_n: int):
    checks = []
    m = re.match(rf"^## {header_word} findings — (\d+) item\(s\)$", _first_line(t))
    checks.append(("no-preamble-header", bool(m),
                   f"first line: {_first_line(t)[:80]!r}"))
    n = int(m.group(1)) if m else 0
    checks.append((f"item-count>={min_n}", n >= min_n, f"N={n}"))
    items = ITEM_RX.findall(t)
    checks.append(("numbered-items-match-N", len(items) == n,
                   f"{len(items)} numbered vs N={n}"))
    for sev, tag in required:
        ok = (sev, tag) in items
        checks.append((f"tag:{tag}", ok, f"expected [{sev}] [{tag}]"))
    sevs = [SEV[s] for s, _ in items]
    checks.append(("severity-non-increasing",
                   all(a >= b for a, b in zip(sevs, sevs[1:])), str(sevs)))
    return checks


def grade_exact_ok(t: str):
    return [("exact-OK", t.strip() == "OK", f"got: {t.strip()[:60]!r}")]


def grade_intent_violations(t: str):
    checks = _findings_checks(t, "Intent", INTENT_REQUIRED, 7)
    checks.append(("classification-pushback",
                   bool(re.search(r"^Input classification: pushback$", t, re.M)),
                   "expects 'Input classification: pushback'"))
    checks.append(("memories-applied-negotiation",
                   bool(re.search(r"^Memories applied: .*feedback_negotiation_posture\.md",
                                  t, re.M)),
                   "tail must list feedback_negotiation_posture.md"))
    return checks


def grade_comms_violations(t: str):
    checks = _findings_checks(t, "Critic", COMMS_REQUIRED, 4)
    checks.append(("memories-applied-present",
                   bool(re.search(r"^Memories applied: ", t, re.M)), ""))
    # Informational only (log-dependent checks are inert on this fixture):
    # [unanswered-question] / [anchor-drift] firing is not a failure.
    return checks


def grade_research_blocked(t: str):
    return [
        ("no-preamble-blocked-header",
         _first_line(t) == "## Research BLOCKED — Vague Prospect",
         f"first line: {_first_line(t)[:80]!r}"),
        ("posting-empty-tag", "[posting-empty]" in t, ""),
        ("unblock-footer",
         bool(re.search(r"^What's needed to unblock:", t, re.M)), ""),
        ("no-success-leakage", "## Research synthesis" not in t, ""),
        ("no-invocation-blocker", "[invocation]" not in t, ""),
    ]


GRADERS = {
    "grade_exact_ok": grade_exact_ok,
    "grade_intent_violations": grade_intent_violations,
    "grade_comms_violations": grade_comms_violations,
    "grade_research_blocked": grade_research_blocked,
}

# --------------------------------------------------------------------------
# grade / compare / list
# --------------------------------------------------------------------------

def grade_run(run_dir: Path) -> dict:
    run_meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    out = {"run_id": run_meta.get("run_id"), "git_rev": run_meta.get("git_rev"),
           "model": run_meta.get("model"), "fixtures": {}, "summary": {}}
    tally = {"GREEN": 0, "RED": 0, "FLAKY": 0, "SKIPPED-ENV": 0}
    for fid, info in run_meta.get("fixtures", {}).items():
        if "skipped_env" in info:
            out["fixtures"][fid] = {"verdict": "SKIPPED-ENV",
                                    "detail": info["skipped_env"]}
            tally["SKIPPED-ENV"] += 1
            continue
        grader = GRADERS[EVAL_SUITE[fid]["grader"]]
        gens = []
        for gen_dir in sorted((run_dir / fid).glob("gen*")):
            t = (gen_dir / "transcript.md").read_text(encoding="utf-8") \
                if (gen_dir / "transcript.md").is_file() else ""
            checks = [{"name": n, "pass": bool(ok), "detail": d}
                      for n, ok, d in grader(t)]
            gens.append({"gen": gen_dir.name,
                         "pass": all(c["pass"] for c in checks),
                         "checks": checks})
        passes = [g["pass"] for g in gens]
        verdict = ("GREEN" if all(passes) else "RED" if not any(passes)
                   else "FLAKY") if passes else "RED"
        out["fixtures"][fid] = {"verdict": verdict, "generations": gens}
        tally[verdict] += 1
    out["summary"] = tally
    (run_dir / "grades.json").write_text(
        json.dumps(out, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    return out


def cmd_grade(args) -> int:
    out = grade_run(Path(args.run_dir))
    for fid, f in sorted(out["fixtures"].items()):
        print(f"{f['verdict']:>11}  {fid}")
        for g in f.get("generations", []):
            for c in g["checks"]:
                if not c["pass"]:
                    print(f"             - FAIL {c['name']}: {c['detail']}")
    print("summary:", json.dumps(out["summary"]))
    return 0


def cmd_compare(args) -> int:
    a = json.loads((Path(args.run_a) / "grades.json").read_text(encoding="utf-8"))
    b = json.loads((Path(args.run_b) / "grades.json").read_text(encoding="utf-8"))
    regressions = []
    print(f"{'fixture':<22} {'A(' + str(a.get('git_rev')) + ')':<16} B({b.get('git_rev')})")
    for fid in sorted(set(a["fixtures"]) | set(b["fixtures"])):
        va = a["fixtures"].get(fid, {}).get("verdict", "-")
        vb = b["fixtures"].get(fid, {}).get("verdict", "-")
        marker = ""
        if va == "GREEN" and vb in ("RED", "FLAKY"):
            marker = "  <-- REGRESSION"
            regressions.append(fid)
        elif va in ("RED", "FLAKY") and vb == "GREEN":
            marker = "  (improved)"
        print(f"{fid:<22} {va:<16} {vb}{marker}")
    if regressions:
        print(f"REGRESSIONS: {', '.join(regressions)} -- re-run those fixtures "
              "with --n 3; RED stands only if <=1/3 pass.")
        return 1
    print("no regressions")
    return 0


def cmd_list(_args) -> int:
    for fid, spec in EVAL_SUITE.items():
        print(f"{fid:<20} {spec['fixture']}  [{spec['tools']}]")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="paid generation (local only)")
    r.add_argument("--fixture", choices=sorted(EVAL_SUITE))
    r.add_argument("--model", default="sonnet")
    r.add_argument("--n", type=int, default=1)
    r.add_argument("--repo", help="repo root to eval (base worktree for before/after)")
    r.add_argument("--label", help="suffix for the run id, e.g. base/head")
    r.set_defaults(fn=cmd_run)
    g = sub.add_parser("grade", help="free deterministic grading")
    g.add_argument("run_dir")
    g.set_defaults(fn=cmd_grade)
    c = sub.add_parser("compare", help="diff two graded runs; exit 1 on regression")
    c.add_argument("run_a")
    c.add_argument("run_b")
    c.set_defaults(fn=cmd_compare)
    ls = sub.add_parser("list", help="print the fixture manifest")
    ls.set_defaults(fn=cmd_list)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
