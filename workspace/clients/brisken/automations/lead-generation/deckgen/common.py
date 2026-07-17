# /// script
# dependencies = ["websockets"]
# ///
"""Shared plumbing for the Brisken deck-foundation-v2 build system.

Path resolution: durable binaries (the reference deck, the derived library)
live in the MAIN clone's gitignored client context, and build outputs in the
main clone's .scratch — even when this code runs from a git worktree (whose
gitignored dirs are empty/ephemeral). The main clone is the first entry of
`git worktree list`.

CDP: raw-websocket Chrome DevTools client against the dedicated headless
automation Edge (:9223 by default, profile %LOCALAPPDATA%\\EdgeCdpAutomation,
launcher tools/launch-edge-cdp.ps1). Same pattern as the proven
.scratch/deckgen/_sp_*.py scripts, promoted here to a tracked home.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import urllib.request
from pathlib import Path

try:
    import websockets  # CDP scripts declare this dep; path-only users skip it
except ImportError:
    websockets = None

SITE = "https://brisken.sharepoint.com/sites/MARKETING"
PPTX_ROOT = (
    "/sites/MARKETING/Shared Documents/20_Assets/BRISKEN PRESENTATIONS/"
    "OnePilot - Cloud Solutions Presentations/2026_PPTX"
)
REFERENCE_NAME = "OnePilot Solutions Overview 2026.pptx"
# The reference lives one level ABOVE 2026_PPTX (verified 2026-07-17).
REFERENCE_SR_URL = (
    "/sites/MARKETING/Shared Documents/20_Assets/BRISKEN PRESENTATIONS/"
    "OnePilot - Cloud Solutions Presentations/" + REFERENCE_NAME
)

CDP_PORT = int(os.environ.get("CDP_PORT", "9223"))


def main_clone_root() -> Path:
    """Root of the primary clone (first `git worktree list` entry)."""
    out = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=Path(__file__).parent, capture_output=True, text=True, check=True,
    ).stdout
    for line in out.splitlines():
        if line.startswith("worktree "):
            return Path(line.split(" ", 1)[1])
    raise RuntimeError("git worktree list returned no worktree")


def context_dir() -> Path:
    d = main_clone_root() / "workspace/clients/brisken/context/decks/reference-2026"
    d.mkdir(parents=True, exist_ok=True)
    return d


def dist_dir() -> Path:
    d = main_clone_root() / ".scratch/deckgen-v2/dist"
    d.mkdir(parents=True, exist_ok=True)
    return d


def qa_dir() -> Path:
    d = main_clone_root() / ".scratch/deckgen-v2/qa"
    d.mkdir(parents=True, exist_ok=True)
    return d


def reference_path() -> Path:
    return context_dir() / REFERENCE_NAME


def library_path() -> Path:
    return context_dir() / "library.pptx"


# ------------------------------------------------------------------ CDP

def _http_json(path: str):
    return json.load(
        urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}" + path, timeout=8)
    )


class Cdp:
    """One own-tab CDP session on the automation Edge. Use as async ctx mgr."""

    NEWTAB_URL = SITE + "/_layouts/15/viewlsts.aspx"

    def __init__(self):
        self._id = 10
        self.ws = None
        self._target_id = None
        self._browser_ws_url = None

    def _next(self) -> int:
        self._id += 1
        return self._id

    async def __aenter__(self):
        self._browser_ws_url = _http_json("/json/version")["webSocketDebuggerUrl"]
        async with websockets.connect(self._browser_ws_url, max_size=120_000_000) as bws:
            res = await self._call_on(bws, "Target.createTarget", {"url": self.NEWTAB_URL})
            self._target_id = res["targetId"]
            await self._call_on(bws, "Target.activateTarget", {"targetId": self._target_id})
        self.ws = await websockets.connect(
            f"ws://127.0.0.1:{CDP_PORT}/devtools/page/{self._target_id}",
            max_size=120_000_000,
        )
        await self.call("Page.enable")
        await self.call("Runtime.enable")
        await self.wait_ready()
        await asyncio.sleep(2)
        return self

    async def __aexit__(self, *exc):
        if self.ws:
            await self.ws.close()
        if self._target_id:
            try:
                async with websockets.connect(self._browser_ws_url, max_size=120_000_000) as bws:
                    await self._call_on(bws, "Target.closeTarget", {"targetId": self._target_id}, timeout=10)
            except Exception:
                pass

    async def _call_on(self, ws, method, params=None, timeout=60):
        _id = self._next()
        await ws.send(json.dumps({"id": _id, "method": method, "params": params or {}}))

        async def _wait():
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == _id:
                    if "error" in msg:
                        raise RuntimeError(json.dumps(msg["error"])[:300])
                    return msg.get("result")

        return await asyncio.wait_for(_wait(), timeout)

    async def call(self, method, params=None, timeout=60):
        return await self._call_on(self.ws, method, params, timeout)

    async def ev(self, expr: str, timeout=120):
        """Runtime.evaluate with awaitPromise; retries once on the documented
        context-destroyed race."""
        for attempt in (1, 2):
            try:
                r = await self.call(
                    "Runtime.evaluate",
                    {"expression": expr, "awaitPromise": True, "returnByValue": True},
                    timeout=timeout,
                )
                if r.get("exceptionDetails"):
                    raise RuntimeError("JS exc: " + str(r["exceptionDetails"])[:400])
                return r.get("result", {}).get("value")
            except RuntimeError as e:
                if attempt == 2 or "context" not in str(e).lower():
                    raise
                await asyncio.sleep(3)

    async def wait_ready(self, timeout=40) -> bool:
        for _ in range(int(timeout / 2)):
            try:
                if await self.ev("document.readyState", timeout=6) == "complete":
                    return True
            except Exception:
                pass
            await asyncio.sleep(2)
        return False

    async def assert_origin(self):
        origin = await self.ev("location.origin")
        if origin != "https://brisken.sharepoint.com":
            raise RuntimeError(f"tab origin is {origin!r}, not brisken.sharepoint.com — not signed in?")
