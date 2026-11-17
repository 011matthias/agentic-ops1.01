"""Where the engine finds its register, data and secrets, plus fixed IDs.

Every path can be overridden by an environment variable, which is how the
tests and dry runs keep away from the real register and database.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

# Twitch category id for Grand Theft Auto VI, checked live 2026-11-17.
GTA6_GAME_ID = "1867279146"

ENGINE_DIR = Path(__file__).resolve().parents[2]
PROJECT_REL = Path("workspace/projects/gta6-clipping")
SECRET_KEYS = ("TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET")


def primary_root() -> Path | None:
    """The primary checkout of this repo, found through git's common directory.

    Every session works in its own worktree; state and secrets must not
    depend on which one runs the engine.
    """
    try:
        common = subprocess.run(
            ["git", "-C", str(ENGINE_DIR), "rev-parse", "--path-format=absolute",
             "--git-common-dir"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(common).parent if common else None


def data_dir() -> Path:
    """engine/data/ of the PRIMARY checkout, so every worktree shares one state.

    The folder carries its own `.gitignore` (`*`): a checkout whose root
    .gitignore predates the engine still never sees the database (it holds
    the cached Twitch token) as an untracked file a sweep could commit.
    """
    explicit = os.environ.get("CLIPENGINE_DATA_DIR")
    if explicit:
        path = Path(explicit)
    else:
        root = primary_root()
        path = (root / PROJECT_REL / "engine" / "data") if root else ENGINE_DIR / "data"
    path.mkdir(parents=True, exist_ok=True)
    guard = path / ".gitignore"
    if not guard.exists():
        guard.write_text("# clip engine state: never commit\n*\n", encoding="utf-8")
    return path


def db_path() -> Path:
    return data_dir() / "clipengine.sqlite"


def reports_dir() -> Path:
    path = data_dir() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def register_path() -> Path:
    return Path(os.environ.get("CLIPENGINE_REGISTER") or ENGINE_DIR / "config" / "streamers.yaml")


def env_file() -> Path | None:
    """The project's gitignored context/.env.

    A git worktree has no copy of the gitignored context/, so when the local
    one is missing the file is taken from the primary checkout, found through
    git's common directory. Secrets are never copied between checkouts.
    """
    explicit = os.environ.get("CLIPENGINE_ENV_FILE")
    if explicit:
        return Path(explicit)
    local = ENGINE_DIR.parent / "context" / ".env"
    if local.exists():
        return local
    root = primary_root()
    primary = root / PROJECT_REL / "context" / ".env" if root else None
    return primary if primary and primary.exists() else None


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_secrets() -> dict[str, str]:
    """Twitch app credentials; process environment wins over the .env file."""
    path = env_file()
    values = parse_env(path.read_text(encoding="utf-8")) if path and path.exists() else {}
    for key in SECRET_KEYS:
        if os.environ.get(key):
            values[key] = os.environ[key]
    return {k: values[k] for k in SECRET_KEYS if values.get(k)}
