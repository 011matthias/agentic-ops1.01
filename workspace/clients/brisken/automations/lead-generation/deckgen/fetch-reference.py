# /// script
# dependencies = ["websockets"]
# ///
"""Fetch the pristine reference deck (Dirk's OnePilot Solutions Overview)
from SharePoint into the gitignored client context. READ-ONLY on SharePoint.

    CDP_PORT=9223 uv run fetch-reference.py

Idempotent: re-downloads and overwrites the local copy; prints version +
size so drift vs the previous copy is visible. Requires the automation Edge
(tools/launch-edge-cdp.ps1) signed in to brisken.sharepoint.com.
"""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("common", Path(__file__).parent / "common.py")
common = importlib.util.module_from_spec(_spec)
sys.modules["common"] = common
_spec.loader.exec_module(common)


META_JS = """
(async () => {
  const enc = encodeURIComponent(%s).replace(/'/g, "''");
  const u = %s + "/_api/web/GetFileByServerRelativeUrl('" + enc + "')?$select=Name,Length,TimeLastModified,UIVersionLabel";
  const r = await fetch(u, {headers:{'Accept':'application/json;odata=nometadata'}, credentials:'include'});
  if (!r.ok) return {ok:false, status:r.status, err:(await r.text()).slice(0,300)};
  return {ok:true, meta: await r.json()};
})()
""" % (json.dumps(common.REFERENCE_SR_URL), json.dumps(common.SITE))

FETCH_JS = """
(async () => {
  const enc = encodeURIComponent(%s).replace(/'/g, "''");
  const u = %s + "/_api/web/GetFileByServerRelativeUrl('" + enc + "')/$value";
  const r = await fetch(u, {credentials:'include'});
  if (!r.ok) return {ok:false, status:r.status};
  const bytes = new Uint8Array(await r.arrayBuffer());
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000)
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  window.__dl = btoa(bin);
  return {ok:true, b64len: window.__dl.length, bytes: bytes.length};
})()
""" % (json.dumps(common.REFERENCE_SR_URL), json.dumps(common.SITE))


async def main() -> int:
    dest = common.reference_path()
    async with common.Cdp() as cdp:
        await cdp.assert_origin()
        meta = await cdp.ev(META_JS)
        if not meta.get("ok"):
            print("META FAIL", meta)
            return 1
        m = meta["meta"]
        print(f"remote: {m['Name']}  v{m.get('UIVersionLabel')}  {int(m['Length']):,} B  modified {m['TimeLastModified']}")
        if dest.exists():
            print(f"local:  {dest.stat().st_size:,} B (will overwrite)")

        got = await cdp.ev(FETCH_JS, timeout=240)
        if not got.get("ok"):
            print("FETCH FAIL", got)
            return 1
        parts, step = [], 4_000_000
        for start in range(0, got["b64len"], step):
            parts.append(await cdp.ev(f"window.__dl.slice({start},{start + step})"))
        await cdp.ev("(() => { delete window.__dl; return 1; })()")
        data = base64.b64decode("".join(parts))
        dest.write_bytes(data)
        ok = len(data) == int(m["Length"])
        print(f"saved {dest}  ({len(data):,} B) match={ok}")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
