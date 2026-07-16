#!/usr/bin/env python3
"""PreToolUse(Write) hook: deterministic file-placement floor.

Backs rule_file_placement.md (W2). Classifies the write target by path +
basename pattern and:

  DENY     new file at the repo root not in the config/doc allowlist
  DENY     a never-commit pattern (secrets/tokens/keys) into a TRACKED path
  DENY     a scratch pattern into a non-gitignored path (incl. root)
  ADVISE   a token-bearing dotfile (.npmrc/.netrc/...) into a tracked path
  ADVISE   a data/PII export into a tracked, non-gitignored path
  ADVISE   write into an unknown top-level directory (no established home)
  PASS     edits to existing files; writes already in a known home;
           committable env templates (.env.example/.sample/.template);
           durable source/test/doc files that merely start with debug-/
           snapshot-/temp- etc.; anything under a gitignored area

WHY DENY AND NOT JUST WARN: the .gitignore already carries reactive
root-clutter patches (/test.pdf, /after-*.jpeg, ...) added after stray
artifacts hit the root. Advisory depends on agent recall, which is the
thing that kept failing; the deny floor removes the recall dependency for
the clear-cut cases. The rule + skill carry the intent nuance the
path-pattern gate can't read. The never-commit/scratch pattern lists are a
non-exhaustive floor, not complete coverage.

This module was hardened 2026-06-18 after an adversarial review (19 verified
findings): committable env templates and durable source files no longer
false-deny; YAML/PKCS12/SSH/service-account secrets no longer false-pass;
the git-down static fallback now mirrors the client-secret home; the
double-slash root-deny bypass is closed.

Mechanism: emits a PreToolUse JSON `permissionDecision: "deny"` with the
redirect reason (deny is the most-restrictive decision and wins over the
auto-approve-protected `allow` that fires earlier in the same chain).
Advisory uses `additionalContext`. Out-of-repo writes (the memory dir,
home-dir Bewerbungen, openclaw-sandbox) are never touched.

Defensive: any error -> exit 0 silently. NEVER bricks a write.
"""
from __future__ import annotations

import datetime
import os
import re
import subprocess
import sys

try:
    import json
except Exception:  # pragma: no cover
    sys.exit(0)

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HOOK_DIR))  # .../agentic-ops1
HOOK_LOG = os.path.join(HOOK_DIR, "hook-log.txt")

# --- test seams: never set in production -----------------------------------
# Used by tools/tests/test_file_placement_gate.py.
_ENV_REPO = os.environ.get("FILE_PLACEMENT_GATE_REPO")
if _ENV_REPO:
    REPO = _ENV_REPO
# Force the git-down static fallback path (exercise is_gitignored offline).
_FORCE_NO_GIT = bool(os.environ.get("FILE_PLACEMENT_GATE_NO_GIT"))

REPO_POSIX = REPO.replace("\\", "/").rstrip("/")
REPO_POSIX_LOWER = REPO_POSIX.lower()

# Files that legitimately live at the repo root. A NEW root file not here is
# denied; edits to these pass through. NOTE: token-bearing dotfiles
# (.npmrc/.pypirc/.netrc) are deliberately NOT here — they route to the
# token-dotfile advisory so an inline auth token is flagged.
ROOT_ALLOWLIST = {
    # existing repo config + top-level docs
    "claude.md", "readme.md", "delivery-guide.md", ".gitignore", ".mcp.json",
    "pytest.ini", "ruff.toml", ".pre-commit-config.yaml", "skills-lock.json",
    ".python-version", ".editorconfig", ".gitattributes", "license",
    "license.md", "skills.lock.json",
    # conventional root-only build / tooling config (no other sensible home)
    "makefile", "dockerfile", ".dockerignore",
    "package.json", "package-lock.json", "tsconfig.json", "tsconfig.base.json",
    "vercel.json", "turbo.json", "pnpm-workspace.yaml", "pnpm-lock.yaml",
    "yarn.lock", ".nvmrc", ".node-version", ".prettierrc", ".prettierignore",
    ".eslintrc.json", ".eslintignore",
    "pyproject.toml", "uv.lock", "requirements.txt", "requirements-dev.txt",
    "setup.py", "setup.cfg", "tox.ini", "mypy.ini", "conftest.py",
    # conventional root meta docs
    "changelog.md", "contributing.md", "security.md", "code_of_conduct.md",
    "authors", "notice",
    # secret-free env TEMPLATES (committable; real .env stays denied)
    ".env.example", ".env.sample", ".env.template",
}

# Top-level dirs with an established home (W2 §2). A write under any other
# top-level dir is ambiguous -> advisory. Committed homes: workspace,
# platform, docs, tools, scripts, api-docs, .claude, .github, .agents.
# The rest are gitignored tooling dirs (branch 4 already suppresses their
# advisory via `and not _ignored()`); kept here for clarity.
KNOWN_TOP_DIRS = {
    "workspace", "platform", "docs", "tools", "scripts", "api-docs",
    ".claude", ".github", ".agents", ".scratch", ".tmp", ".vscode",
    ".serena", ".playwright-mcp", "internal", "node_modules",
}

# Gitignored prefixes — static fallback when `git check-ignore` is
# unavailable. Must stay a subset-mirror of .gitignore directory prefixes
# (it cannot mirror extension globs like *.db without pulling in
# regex-matched names). Two high-value AREA rules are handled separately in
# is_gitignored(): workspace/clients/*/context/ and docs/sessions/*-context.yaml.
STATIC_IGNORED_PREFIXES = (
    ".scratch/", ".tmp/", "api-docs/", ".playwright-mcp/", "scripts/.",
    "internal/", ".serena/", ".pytest_cache/", ".ruff_cache/",
    "platform/.next/", "platform/node_modules/", "node_modules/",
)

# Scratch names. PREFIX members fire only on non-durable files (a committed
# .py/.ts/.md named debug-* is source, not scratch); HARD members are
# unambiguously ephemeral regardless of extension.
SCRATCH_PREFIX_RE = re.compile(r"^(scratch|tmp|temp|debug|snapshot)[-_.]", re.IGNORECASE)
SCRATCH_HARD_RE = re.compile(
    r"([-_]dump\.)|([-_]debug\.)|(\.tmp$)|(\.bak$)|(^state-\d)", re.IGNORECASE
)
DURABLE_EXT_RE = re.compile(
    r"(\.(py|ts|tsx|js|jsx|mjs|cjs|md|mdx|go|rs|css|scss|vue|svelte|sql)$)"
    r"|(\.(spec|test)\.)",
    re.IGNORECASE,
)

# Committable env templates — exempt from the never-commit env arms.
SAFE_ENV_SUFFIXES = (".env.example", ".env.sample", ".env.template", ".env.dist")

# Never-commit secret/token/key shapes. Non-exhaustive deny floor. The
# secret/credential arms use word-boundary forms ([-_] or ^) so a descriptive
# doc like `secrets-rotation-guide.json` is NOT treated as a secret.
NEVERCOMMIT_RE = re.compile(
    r"(\.env$)|(\.env\.)"                                  # .env / .env.local / .env.production
    r"|(^client_secrets\.json$)"
    r"|(^token\.json$)|([-_]token\.json$)"                 # token.json / refresh_token.json
    r"|(\.pem$)|(\.key$)|(\.key\.json$)"
    r"|(\.p12$)|(\.pfx$)|(\.jks$)|(\.keystore$)"           # binary key bundles
    r"|(^secrets?\.(json|ya?ml|toml|ini|conf|cfg)$)|([-_]secrets?\.(json|ya?ml|toml|ini|conf|cfg)$)"
    r"|(^credentials?\.(json|ya?ml|toml|ini|conf|cfg)$)|([-_]credentials?\.(json|ya?ml|toml|ini|conf|cfg)$)"
    r"|(service[-_]?account.*\.json$)|(^sa[-_]?key\.json$)|(firebase[-_]?adminsdk.*\.json$)"
    r"|(^id_(rsa|dsa|ecdsa|ed25519)$)|(_key$)",            # SSH/extensionless private keys
    re.IGNORECASE,
)

# Token-bearing dotfiles — name-only gate can't see an inline token, so warn.
TOKEN_DOTFILE_RE = re.compile(r"^(\.npmrc|\.pypirc|\.netrc|\.dockercfg)$", re.IGNORECASE)

# Data / PII export shapes — advise (never deny) on a tracked, non-fixture path.
EXPORT_RE = re.compile(
    r"(export.*\.csv$)|(^leads?[-_.].*\.csv$)|([-_]leads?[-_.].*\.csv$)|([-_]pii[-_.])",
    re.IGNORECASE,
)


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} file-placement-gate {msg}\n")
    except Exception:
        pass


def normalize(path: str) -> str:
    """Git-Bash /c/Users -> C:/Users; backslashes -> forward slashes."""
    if not path:
        return path
    if len(path) >= 3 and path[0] == "/" and path[2] == "/" and path[1].isalpha():
        path = f"{path[1].upper()}:{path[2:]}"
    return path.replace("\\", "/")


def rel_to_repo(abspath_posix: str) -> str | None:
    """Return the repo-relative POSIX path, or None if outside the repo."""
    low = abspath_posix.lower()
    if low == REPO_POSIX_LOWER:
        return ""
    prefix = REPO_POSIX_LOWER + "/"
    if not low.startswith(prefix):
        return None
    return abspath_posix[len(prefix):]


def is_gitignored(abspath_posix: str, rel: str) -> bool:
    """True if the path is gitignored. Authoritative via git; static fallback
    mirrors the high-value .gitignore areas (esp. the client-secret home) so a
    git outage cannot false-deny a legitimate secret/scratch write."""
    if not _FORCE_NO_GIT:
        try:
            proc = subprocess.run(
                ["git", "check-ignore", "-q", abspath_posix],
                cwd=REPO, timeout=5,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if proc.returncode in (0, 1):
                return proc.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
    rl = rel.lower()
    # client-secret home is gitignored EXCEPT the committable context/portable/
    # opt-in (mirror .gitignore: workspace/clients/*/context/ + !.../portable/).
    if re.match(r"workspace/clients/[^/]+/context/(?!portable/)", rl):
        return True
    # session-context YAMLs carry inline API keys (.gitignore).
    if re.match(r"docs/sessions/.*-context\.yaml$", rl):
        return True
    return any(rl.startswith(p) for p in STATIC_IGNORED_PREFIXES)


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def advise(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": text,
        }
    }))


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    # Only gate file CREATION. Edits operate on files already in a home.
    if event.get("tool_name") != "Write":
        return 0

    raw_path = (event.get("tool_input") or {}).get("file_path", "") or ""
    if not raw_path:
        return 0
    abspath = normalize(raw_path)

    # Resolve relative targets against the repo root.
    if not (len(abspath) >= 2 and abspath[1] == ":") and not abspath.startswith("/"):
        abspath = f"{REPO_POSIX}/{abspath.lstrip('/')}"

    rel = rel_to_repo(abspath)
    if rel is None:
        return 0  # outside this repo (memory dir, home dir, sandbox) — not our scope
    if rel == "":
        return 0  # writing the repo dir itself — unreachable, defensive

    # Collapse redundant separators and drop "."/"" segments BEFORE deriving
    # the top segment, so `<repo>//report.md` and `<repo>/./report.md` can't
    # dodge the root-deny branch.
    rel = "/".join(p for p in rel.split("/") if p not in ("", "."))
    if rel == "":
        return 0

    fname = rel.rsplit("/", 1)[-1].lower()
    parts = rel.split("/")
    top = parts[0].lower()
    is_root_level = len(parts) == 1

    # Already in the scratch home -> always fine.
    if top == ".scratch":
        return 0

    ignored = None  # lazy

    def _ignored() -> bool:
        nonlocal ignored
        if ignored is None:
            ignored = is_gitignored(abspath, rel)
        return ignored

    # 1. Never-commit pattern into a tracked path -> DENY.
    #    Committable env templates are exempt (they ship placeholder keys).
    if NEVERCOMMIT_RE.search(fname) and not fname.endswith(SAFE_ENV_SUFFIXES):
        if _ignored():
            return 0  # correctly hidden in a gitignored area
        log_fire(f"DENY never-commit-tracked {rel}")
        deny(
            f"PLACEMENT DENY (W2): '{fname}' looks like never-commit content "
            f"(secret/token/key) and '{rel}' is a TRACKED path. Write it to a "
            f"gitignored location (workspace/clients/{{client}}/context/ for "
            f"client secrets, or .scratch/ for throwaway), or do not write it. "
            f"Never commit credentials. See rule_file_placement.md §6."
        )
        return 0

    # 2. Scratch pattern into a non-gitignored path -> DENY. A durable
    #    source/test/doc file that merely starts with debug-/snapshot-/etc is
    #    NOT scratch (only the HARD dump/state/.tmp/.bak members deny it).
    is_scratch = bool(SCRATCH_HARD_RE.search(fname)) or (
        bool(SCRATCH_PREFIX_RE.search(fname)) and not DURABLE_EXT_RE.search(fname)
    )
    if is_scratch:
        if _ignored():
            return 0
        log_fire(f"DENY scratch-tracked {rel}")
        deny(
            f"PLACEMENT DENY (W2): '{fname}' is an ephemeral/scratch name and "
            f"'{rel}' is not gitignored. Ephemeral artifacts go to .scratch/ "
            f"(gitignored), never a tracked path. First apply W1: if this is a "
            f"finding you can print or distill into one line, write nothing. "
            f"Otherwise write to .scratch/{fname}. See rule_file_placement.md §2."
        )
        return 0

    # 2b. Token-bearing dotfile into a tracked path -> ADVISE (a name-only gate
    #     can't tell whether an auth token is inline). Fires at root too, so a
    #     root .npmrc is warned rather than hard-denied.
    if TOKEN_DOTFILE_RE.search(fname) and not _ignored():
        log_fire(f"ADVISE token-dotfile {rel}")
        advise(
            f"[PLACEMENT] '{fname}' at tracked path '{rel}' commonly carries an "
            f"inline auth token (e.g. //registry.npmjs.org/:_authToken=...). If it "
            f"does, do not commit it: move the token to an env var / CI secret, or "
            f"gitignore this file. See rule_file_placement.md §6."
        )
        return 0

    # 3. New file at repo root not in the allowlist -> DENY.
    if is_root_level:
        if fname in ROOT_ALLOWLIST:
            return 0
        if _ignored():
            advise(
                f"[PLACEMENT] '{fname}' is being written to the repo root. It is "
                f"gitignored, so it won't be committed, but new ephemeral writes "
                f"should go to .scratch/ (W2 §5)."
            )
            return 0
        log_fire(f"DENY root-write {rel}")
        deny(
            f"PLACEMENT DENY (W2): '{fname}' would be a NEW file at the repo "
            f"root. Root is reserved for config + top-level docs (CLAUDE.md, "
            f"README.md, Makefile, package.json, pyproject.toml, ...). Route it "
            f"by kind: a tool -> tools/, a doc -> docs/, a deliverable -> the "
            f"client's deliverables/ or platform/public/, an ephemeral artifact "
            f"-> .scratch/. See the home map in rule_file_placement.md §2."
        )
        return 0

    # 3b. Data / PII export into a tracked, non-gitignored path -> ADVISE.
    #     Excludes fixtures and the gitignored client tree to avoid noise.
    rl = rel.lower()
    if (EXPORT_RE.search(fname) and not _ignored()
            and "fixtures/" not in rl and not rl.startswith("workspace/clients/")):
        log_fire(f"ADVISE export {rel}")
        advise(
            f"[PLACEMENT] '{fname}' looks like a data/lead export into a tracked, "
            f"non-gitignored path ('{rel}'). If it contains raw leads or PII this "
            f"is never-commit (W2 home map): route to "
            f"workspace/clients/{{client}}/context/ (gitignored) or .scratch/, or "
            f"do not write it. If it's a fixture/report, ignore this."
        )
        return 0

    # 4. Unknown top-level directory -> ADVISORY (no established home).
    if top not in KNOWN_TOP_DIRS and not _ignored():
        log_fire(f"ADVISE unknown-top {rel}")
        advise(
            f"[PLACEMENT] '{rel}' is under a top-level directory ('{top}/') with "
            f"no established home in rule_file_placement.md §2. Confirm this is "
            f"the right place, route to an existing home, or use .scratch/ if "
            f"it's ephemeral. Don't create a new tracked top-level dir for an "
            f"orphan file."
        )
        return 0

    return 0  # in a known home — pass through silently


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never hard-fail a write
        try:
            log_fire(f"ERROR {type(exc).__name__}")
        except Exception:
            pass
        sys.exit(0)
