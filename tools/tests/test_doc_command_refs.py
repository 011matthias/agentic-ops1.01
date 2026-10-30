"""Command references in the agent-facing docs resolve to a real command.

Every slash command in this repo is `.claude/commands/comd_<name>.md`, invoked
as `/comd_<name>`. The short forms (`/resume`, `/deploy`, `/test-dev`, ...) are
names from before the `comd_` prefix, and some never existed at all. CLAUDE.md
named 19 of them on 2026-10-28 (repo layout plan W1-5), and it is loaded into
every session and subagent and copied into continuation prompts, so a dead
name there spreads.

Two checks over CLAUDE.md, README.md, .claude/rules, .claude/commands,
.claude/agents and every markdown file under .claude/skills/skil_*:

- no legacy short name as a `/name` token. The deny-list is the plan's fixed
  list, plus every current command stem (so a new command joins without an
  edit here), plus names that were retired outright;
- every `/comd_<name>` has a `comd_<name>.md`.

The negative cases pin what the matcher must leave alone: URL and file paths
(`api/review`, `/test.pdf`), longer words (`/reviewer`) and the prefixed form.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COMMANDS = REPO / ".claude" / "commands"

# The plan's list (W1-5), kept literal so deleting a command file cannot
# silently re-allow its short name.
PLAN_DENY = {
    "resume", "checkpoint", "build-automation", "test-dev", "test-production",
    "status-check", "deploy", "draft", "new-client", "help-system", "system-dev",
    "review", "publish", "client-handoff", "export-client-docs", "new-proposal",
    "proposal-status", "publish-proposal",
}
# Never commands here: /comd_test takes the mode as an argument.
RETIRED = {"test-dev", "test-production", "verify-live"}

# (file, name) pairs that are not this repo's commands: a generic Claude Code
# namespacing example and a Slack slash command in an n8n pattern.
ALLOW = {
    (".claude/skills/skil_meta-builder/modules/COMMAND-GUIDE.md", "test"),
    (".claude/skills/skil_n8n-workflow-patterns/modules/AI-AGENT-WORKFLOW.md", "deploy"),
}

COMD_RE = re.compile(r"/comd_([A-Za-z0-9][\w-]*)")


def command_stems() -> set[str]:
    return {p.stem[len("comd_"):] for p in COMMANDS.glob("comd_*.md")}


def legacy_names() -> set[str]:
    return PLAN_DENY | RETIRED | command_stems()


def legacy_re(names) -> re.Pattern:
    alts = "|".join(map(re.escape, sorted(names, key=len, reverse=True)))
    # Not preceded by a word char, slash, dot or hyphen (paths, URLs); not
    # followed by a word char, hyphen or a file extension.
    return re.compile(rf"(?<![\w/.-])/({alts})(?![\w-]|\.\w)")


def scope_files() -> list[Path]:
    files = [REPO / "CLAUDE.md", REPO / "README.md"]
    for sub in (".claude/rules", ".claude/commands", ".claude/agents"):
        files += sorted((REPO / sub).rglob("*.md"))
    files += sorted((REPO / ".claude" / "skills").glob("skil_*/**/*.md"))
    return [f for f in files if f.is_file()]


def _rel(p: Path) -> str:
    return p.relative_to(REPO).as_posix()


def test_doc_ref_matcher_contract():
    rx = legacy_re({"resume", "review", "test", "deploy"})
    hits = [m.group(1) for m in rx.finditer(
        "Run `/resume {client}` then (/deploy) and /test dev."
    )]
    assert hits == ["resume", "deploy", "test"]
    for quiet in (
        "/comd_resume", "api/review", "https://x.com/review", "/reviewer",
        "/test.pdf", "tools/test-x.py", ".claude/commands/deploy.md",
        "push / deploy",
    ):
        assert not rx.search(quiet), quiet


def test_doc_ref_no_legacy_short_names():
    rx = legacy_re(legacy_names())
    found = []
    for f in scope_files():
        rel = _rel(f)
        text = f.read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            for m in rx.finditer(line):
                if (rel, m.group(1)) not in ALLOW:
                    found.append(f"{rel}:{n}: /{m.group(1)}")
    assert not found, (
        "legacy command names; use /comd_<name> (or `/comd_test <mode>`):\n"
        + "\n".join(found)
    )


def test_doc_ref_every_comd_command_exists():
    stems = command_stems()
    missing = []
    for f in scope_files():
        text = f.read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            for m in COMD_RE.finditer(line):
                name = m.group(1).rstrip("-")
                if name not in stems:
                    missing.append(f"{_rel(f)}:{n}: /comd_{name}")
    assert not missing, "no such command file:\n" + "\n".join(missing)


def test_doc_ref_allowlist_is_live():
    # An ALLOW entry whose file or name no longer occurs is dead weight that
    # would silently excuse a future real hit in that file.
    for rel, name in ALLOW:
        text = (REPO / rel).read_text(encoding="utf-8", errors="replace")
        assert legacy_re({name}).search(text), (rel, name)
