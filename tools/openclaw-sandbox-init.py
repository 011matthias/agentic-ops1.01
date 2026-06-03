#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Scaffold an isolated sandbox for prototyping an openclaw idea.

Creates a sibling directory tree OUTSIDE agentic-ops1 so a prototype
cannot be captured by a client `git subtree push` and so prototype
secrets/data cannot bleed into this repo's session env.

Usage:
    uv run tools/openclaw-sandbox-init.py <idea-slug>
    uv run tools/openclaw-sandbox-init.py <idea-slug> --root /custom/path
    uv run tools/openclaw-sandbox-init.py <idea-slug> --no-git

Default target: ~/Repo/openclaw-sandbox/<idea-slug>/
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

AGENTIC_OPS_ROOT = Path(__file__).resolve().parent.parent


def safe_slug(s: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_" else "-" for c in s.strip().lower())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


def refuse_if_inside_agentic_ops(target: Path) -> None:
    try:
        target.resolve().relative_to(AGENTIC_OPS_ROOT)
    except ValueError:
        return
    sys.exit(
        f"REFUSED: target {target} is inside agentic-ops1.\n"
        "A prototype here can be captured by a client `git subtree push` "
        "and inherit this repo's secrets. Pick a path outside the repo."
    )


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"  wrote {path}")


GITIGNORE = """\
.env
.env.*
!.env.example
.venv/
__pycache__/
*.pyc
node_modules/
scratch/
data/
*.cache
*.sqlite
*.log
.DS_Store
.idea/
.vscode/
"""

ENV_EXAMPLE = """\
# Scoped, throwaway keys ONLY. Never reuse production keys here.
# Anthropic / OpenAI: create a per-project key with a usage cap and
# verify the project is on the no-training tier before sending any
# buyer-sensitive content through.

ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Translation / OCR / scraping providers — provider-specific scoped keys.
TRANSLATION_API_KEY=
PROXY_URL=

# Sandbox flag — set non-empty to allow real-data ingestion. Default off.
ALLOW_REAL_DATA=
"""

DOCKERFILE = """\
FROM python:3.12-slim

RUN useradd --create-home --uid 10001 sandbox
WORKDIR /app
RUN chown sandbox:sandbox /app
USER sandbox

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1

COPY --chown=sandbox:sandbox requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --user -r requirements.txt; fi

COPY --chown=sandbox:sandbox src/ ./src/

CMD ["python", "-m", "src.main"]
"""

COMPOSE = """\
services:
  sandbox:
    build: .
    env_file: .env
    # Scratch volume only — no host mount beyond ./scratch.
    volumes:
      - ./scratch:/app/scratch
    # Narrow network policy: prototype must declare what it needs.
    # Uncomment + edit to enforce egress allowlist via an external network.
    # networks: [sandbox-egress]
    read_only: true
    tmpfs:
      - /tmp
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    mem_limit: 1g
    pids_limit: 256
"""

README_TMPL = """\
# {slug} — openclaw sandbox

Isolated prototype for the `{slug}` openclaw idea.

## Pre-flight (do BEFORE first run)

- [ ] `.env` populated with **scoped** API keys (not production).
- [ ] Anthropic/OpenAI project confirmed on the **no-training** tier.
- [ ] No copies of `agentic-ops1/workspace/clients/*` data in `data/` or `scratch/`.
- [ ] If the prototype scrapes: TOS read for each target source.
- [ ] If the prototype touches EU contact data: GDPR Article 6 basis documented.
- [ ] If the prototype dials phones: TCPA written-consent posture documented.

## Run

```bash
docker compose build
docker compose run --rm sandbox
```

## Promotion

If this idea graduates to a client engagement or platform module, port the
code into the appropriate destination (`workspace/clients/{{client}}/automations/`
or `platform/`). Do NOT just `mv` this folder in — re-scope secrets and data
deliberately at the boundary.
"""

MAIN_PY = """\
def main() -> None:
    print("openclaw sandbox: replace src/main.py with your prototype.")


if __name__ == "__main__":
    main()
"""


def scaffold(target: Path, slug: str) -> None:
    if target.exists() and any(target.iterdir()):
        sys.exit(f"REFUSED: {target} exists and is non-empty.")
    target.mkdir(parents=True, exist_ok=True)
    print(f"scaffolding {target}")
    write(target / ".gitignore", GITIGNORE)
    write(target / ".env.example", ENV_EXAMPLE)
    write(target / "Dockerfile", DOCKERFILE)
    write(target / "docker-compose.yml", COMPOSE)
    write(target / "README.md", README_TMPL.format(slug=slug))
    write(target / "src" / "main.py", MAIN_PY)
    write(target / "src" / "__init__.py", "")
    (target / "scratch").mkdir(exist_ok=True)
    (target / "data").mkdir(exist_ok=True)
    write(target / "scratch" / ".gitkeep", "")
    write(target / "data" / ".gitkeep", "")


def git_init(target: Path) -> None:
    try:
        subprocess.run(
            ["git", "init", "--quiet", "--initial-branch=main"],
            cwd=target,
            check=True,
        )
        print(f"  git init {target}")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"  WARN: git init skipped ({exc})", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("slug", help="Idea slug, e.g. 'soc2-evidence' or 'filings-concierge'")
    p.add_argument(
        "--root",
        default=str(Path.home() / "Repo" / "openclaw-sandbox"),
        help="Parent directory (default: ~/Repo/openclaw-sandbox)",
    )
    p.add_argument("--no-git", action="store_true", help="Skip `git init`")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    slug = safe_slug(args.slug)
    if not slug:
        sys.exit("REFUSED: empty slug after cleaning.")
    target = Path(args.root).expanduser() / slug
    refuse_if_inside_agentic_ops(target)
    scaffold(target, slug)
    if not args.no_git:
        git_init(target)
    print(
        f"\nDONE. Next:\n"
        f"  cd {target}\n"
        f"  cp .env.example .env   # fill in SCOPED keys only\n"
        f"  docker compose build\n"
    )


if __name__ == "__main__":
    main()
