# /// script
# requires-python = ">=3.10"
# dependencies = ["websockets"]
# ///
"""Raw Chrome DevTools Protocol (CDP) helper for the signed-in Edge on :9222.

WHY THIS EXISTS
---------------
Playwright's `connect_over_cdp` HANGS (180s timeout) at context enumeration on a
heavy/busy Edge profile -- confirmed independently by two sessions the same hour
(2026-07-11) and warned about in memory `reference_user_edge_cdp_9222`
("go STRAIGHT to the raw-CDP own-tab pattern, don't retry playwright first").
Agents kept reaching for connect_over_cdp anyway. This is the structural kill:
one promoted, importable raw-CDP entry point so the reflex is "run edge_cdp.py",
not "try playwright again". It talks to the DevTools websocket directly (the
pattern proven in .scratch/cdp.py + grabtoken.py) -- no browser automation
framework, no context enumeration, no hang.

PREREQUISITE
------------
Edge must be launched with remote debugging, e.g.:
  msedge --remote-debugging-port=9222
The user's normal Edge is already CDP-attachable on :9222 (see the memory).

CONNECTION NOTE
---------------
We connect to each target's own `webSocketDebuggerUrl` with the asyncio
`websockets` client, which does not send an Origin header -- the pattern that
works on this machine. If a NEWER Edge build rejects the handshake with HTTP 403
(an Origin check), the confirmed fallback is the sync `websocket-client`
library: `websocket.create_connection(ws_url, suppress_origin=True)`. That path
is documented here so the next agent has the escape hatch without rediscovering
it (reference_user_edge_cdp_9222).

SUBCOMMANDS
-----------
  targets                 list page targets (url/title/ws) as JSON
  eval   --tab S --expr J run JS in the tab whose URL contains S; print result
  token  --tab S --match M --out F  capture a Bearer token from a request whose
                          URL contains M, by reloading the tab and sniffing the
                          Authorization header (grabtoken.py pattern)
  shot   --tab S --out F  screenshot the matched tab to a PNG

All reads are observational; `token` issues a soft page reload. Nothing here
mutates account data.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import urllib.request

DEFAULT_PORT = 9222


# --------------------------------------------------------------------------
# Target discovery (pure + testable; this is the part agents get wrong by
# reaching for a framework instead)
# --------------------------------------------------------------------------
def list_targets(port: int = DEFAULT_PORT, timeout: float = 6.0) -> list[dict]:
    """GET /json/list from the DevTools endpoint. Raises on connection failure
    (so the caller sees 'is Edge running with --remote-debugging-port?')."""
    with urllib.request.urlopen(f"http://localhost:{port}/json/list", timeout=timeout) as r:
        data = json.load(r)
    return data if isinstance(data, list) else []


def select_target(targets: list[dict], match: str | None = None,
                  ttype: str = "page") -> dict | None:
    """Pick the first target of `ttype` whose URL (or title) contains `match`.
    `match=None` returns the first target of that type. Pure -- unit-tested."""
    for t in targets:
        if ttype and t.get("type") != ttype:
            continue
        if match is None:
            return t
        hay = (t.get("url", "") or "") + " " + (t.get("title", "") or "")
        if match in hay:
            return t
    return None


def _resolve(port: int, tab: str | None, ttype: str = "page") -> dict:
    targets = list_targets(port)
    t = select_target(targets, tab, ttype)
    if not t:
        avail = [{"type": x.get("type"), "url": (x.get("url") or "")[:80]} for x in targets]
        raise SystemExit(json.dumps({"error": "no matching target",
                                     "tab": tab, "available": avail}))
    return t


# --------------------------------------------------------------------------
# Minimal CDP driver over the target's own websocket
# --------------------------------------------------------------------------
class EdgeCDP:
    """One websocket, id-matched request/response. Mirrors .scratch/cdp.py."""

    def __init__(self, ws):
        self.ws = ws
        self._id = 0

    async def call(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        mid = self._id
        await self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(json.dumps(msg["error"])[:300])
                return msg.get("result", {})

    async def evaluate(self, expr: str):
        r = await self.call("Runtime.evaluate", {
            "expression": expr, "awaitPromise": True, "returnByValue": True,
        })
        if r.get("exceptionDetails"):
            return {"__exc": str(r["exceptionDetails"])[:300]}
        return r.get("result", {}).get("value")


def _connect(ws_url: str):
    """websockets.connect with a large max frame (CDP screenshots are big).
    Imported lazily so `targets`/`select_target` work without the dependency."""
    import websockets
    return websockets.connect(ws_url, max_size=60_000_000)


async def _do_eval(port: int, tab: str | None, expr: str) -> None:
    t = _resolve(port, tab)
    async with _connect(t["webSocketDebuggerUrl"]) as ws:
        cdp = EdgeCDP(ws)
        await cdp.call("Runtime.enable")
        print(json.dumps({"tab": t.get("url"), "result": await cdp.evaluate(expr)},
                         ensure_ascii=False)[:6000])


async def _do_shot(port: int, tab: str | None, out: str) -> None:
    t = _resolve(port, tab)
    async with _connect(t["webSocketDebuggerUrl"]) as ws:
        cdp = EdgeCDP(ws)
        await cdp.call("Page.enable")
        r = await cdp.call("Page.captureScreenshot", {"format": "png"})
        with open(out, "wb") as f:
            f.write(base64.b64decode(r["data"]))
    print(json.dumps({"ok": True, "out": out}))


async def _do_token(port: int, tab: str | None, match: str, out: str | None,
                    timeout: float) -> None:
    """Reload the matched tab and capture the first Bearer token on a request
    whose URL contains `match` (grabtoken.py pattern)."""
    t = _resolve(port, tab)
    token = None
    async with _connect(t["webSocketDebuggerUrl"]) as ws:
        cdp = EdgeCDP(ws)
        await cdp.call("Network.enable")
        await cdp.call("Page.enable")
        await cdp.call("Page.reload", {"ignoreCache": False})
        loop = asyncio.get_event_loop()
        end = loop.time() + timeout
        while loop.time() < end and token is None:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
            except asyncio.TimeoutError:
                continue
            msg = json.loads(raw)
            if msg.get("method") != "Network.requestWillBeSent":
                continue
            req = msg["params"]["request"]
            if match not in req.get("url", ""):
                continue
            hdrs = req.get("headers", {})
            auth = hdrs.get("Authorization") or hdrs.get("authorization")
            if auth and auth.lower().startswith("bearer "):
                token = auth.split(None, 1)[1]
    if not token:
        print(json.dumps({"error": "no token captured", "match": match, "tab": t.get("url")}))
        raise SystemExit(3)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(token)
    # decode aud/scp/upn for confirmation (no secret printed)
    info = {"ok": True, "tlen": len(token), "out": out}
    try:
        seg = token.split(".")[1]
        seg = seg.replace("-", "+").replace("_", "/") + "=" * (-len(seg) % 4)
        claims = json.loads(base64.b64decode(seg))
        info.update({"aud": claims.get("aud"), "scp": claims.get("scp"),
                     "upn": claims.get("upn") or claims.get("unique_name")})
    except Exception:
        pass
    print(json.dumps(info, ensure_ascii=False))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Raw CDP helper for Edge on :9222.")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("targets")
    pe = sub.add_parser("eval"); pe.add_argument("--tab"); pe.add_argument("--expr", required=True)
    ps = sub.add_parser("shot"); ps.add_argument("--tab"); ps.add_argument("--out", required=True)
    pt = sub.add_parser("token")
    pt.add_argument("--tab"); pt.add_argument("--match", required=True)
    pt.add_argument("--out"); pt.add_argument("--timeout", type=float, default=22.0)

    args = ap.parse_args(argv)

    try:
        if args.cmd == "targets":
            ts = [{"type": t.get("type"), "title": t.get("title"), "url": t.get("url"),
                   "ws": t.get("webSocketDebuggerUrl")} for t in list_targets(args.port)]
            print(json.dumps(ts, ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "eval":
            asyncio.run(_do_eval(args.port, args.tab, args.expr)); return 0
        if args.cmd == "shot":
            asyncio.run(_do_shot(args.port, args.tab, args.out)); return 0
        if args.cmd == "token":
            asyncio.run(_do_token(args.port, args.tab, args.match, args.out, args.timeout)); return 0
    except urllib.error.URLError as e:
        print(json.dumps({"error": "cannot reach Edge DevTools on "
                          f"port {args.port} -- launch Edge with "
                          "--remote-debugging-port=9222", "detail": str(e)}))
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
