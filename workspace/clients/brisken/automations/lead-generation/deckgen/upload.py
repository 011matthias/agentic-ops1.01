# /// script
# dependencies = ["websockets"]
# ///
"""Upload a composed deck (pptx + pdf) to SharePoint — Asset Testing ONLY.

    CDP_PORT=9223 uv run upload.py mdh-commodities
    CDP_PORT=9223 uv run upload.py --all

Hard guard: this script can write to exactly ONE SharePoint folder,
2026_PPTX/Asset Testing (the reviewed-by-Dirk staging area announced in the
2026-07-17 folder-map mail). No other destination is expressible here; the
swap of an approved proposal into Brisken Product Assets is a separate,
owner-approved manual runbook step (see README.md).

Overwrites same-name files in Asset Testing (SharePoint version history
keeps priors). Verifies each upload by re-listing the folder and comparing
byte sizes (pdf is a stable fingerprint; SharePoint rewrites pptx on
upload, so pptx presence + plausible size is checked, not equality).
"""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
import sys
from pathlib import Path

_here = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("common", _here / "common.py")
common = importlib.util.module_from_spec(_spec)
sys.modules["common"] = common
_spec.loader.exec_module(common)

# The ONLY destination this script can write to.
DEST_FOLDER = common.PPTX_ROOT + "/Asset Testing"
assert DEST_FOLDER.endswith("/Asset Testing")


def digest_js():
    return """
(async () => {
  const r = await fetch(%s + "/_api/contextinfo", {method:'POST',
    headers:{'Accept':'application/json;odata=nometadata'}, credentials:'include'});
  if (!r.ok) return {ok:false, status:r.status};
  const j = await r.json();
  return {ok:true, digest: j.FormDigestValue};
})()
""" % (json.dumps(common.SITE),)


def upload_js(folder: str, name: str, digest: str):
    return """
(async () => {
  const folder = %s, name = %s, digest = %s;
  const encF = encodeURIComponent(folder).replace(/'/g, "''");
  const encN = encodeURIComponent(name).replace(/'/g, "''");
  const b64 = window.__up; delete window.__up;
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const u = %s + "/_api/web/GetFolderByServerRelativeUrl('" + encF +
    "')/Files/add(url='" + encN + "',overwrite=true)";
  const r = await fetch(u, {method:'POST', credentials:'include', body: bytes,
    headers:{'Accept':'application/json;odata=nometadata', 'X-RequestDigest': digest}});
  if (!r.ok) return {ok:false, status:r.status, err:(await r.text()).slice(0,300)};
  const j = await r.json();
  return {ok:true, url: j.ServerRelativeUrl, bytes: Number(j.Length)};
})()
""" % (json.dumps(folder), json.dumps(name), json.dumps(digest), json.dumps(common.SITE))


def list_js(folder: str):
    return """
(async () => {
  const enc = encodeURIComponent(%s).replace(/'/g, "''");
  const u = %s + "/_api/web/GetFolderByServerRelativeUrl('" + enc + "')/Files?$select=Name,Length,TimeLastModified&$top=200";
  const r = await fetch(u, {headers:{'Accept':'application/json;odata=nometadata'}, credentials:'include'});
  if (!r.ok) return {ok:false, status:r.status};
  const j = await r.json();
  return {ok:true, files:(j.value||[]).map(x=>({name:x.Name, bytes:Number(x.Length), modified:x.TimeLastModified}))};
})()
""" % (json.dumps(folder), json.dumps(common.SITE))


async def push_file(cdp, path: Path, digest: str) -> bool:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode()
    step = 4_000_000
    await cdp.ev("window.__up = '';")
    for start in range(0, len(b64), step):
        chunk = b64[start:start + step]
        await cdp.ev(f"(() => {{ window.__up += {json.dumps(chunk)}; return window.__up.length; }})()")
    res = await cdp.ev(upload_js(DEST_FOLDER, path.name, digest), timeout=300)
    if not res.get("ok"):
        print(f"  FAIL {path.name}: {res}")
        return False
    print(f"  OK {path.name} -> {res['url']}  ({res['bytes']:,} B local {len(data):,} B)")
    return True


async def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    if args == ["--all"]:
        deck_dirs = sorted(d for d in common.dist_dir().iterdir() if d.is_dir())
    else:
        deck_dirs = [common.dist_dir() / args[0]]

    files: list[Path] = []
    for d in deck_dirs:
        got = sorted(list(d.glob("*.pptx")) + list(d.glob("*.pdf")))
        if not got:
            print(f"nothing composed in {d}")
            return 1
        files.extend(got)

    async with common.Cdp() as cdp:
        await cdp.assert_origin()
        dig = await cdp.ev(digest_js())
        if not dig.get("ok"):
            print("contextinfo failed:", dig)
            return 1
        ok = 0
        for f in files:
            ok += bool(await push_file(cdp, f, dig["digest"]))

        listing = await cdp.ev(list_js(DEST_FOLDER))
        print(f"\nAsset Testing after upload ({'OK' if listing.get('ok') else 'LIST FAIL'}):")
        remote = {x["name"]: x for x in listing.get("files", [])}
        verified = 0
        for f in files:
            r = remote.get(f.name)
            if not r:
                print(f"  MISSING remote: {f.name}")
                continue
            if f.suffix == ".pdf" and r["bytes"] != f.stat().st_size:
                print(f"  SIZE MISMATCH {f.name}: remote {r['bytes']:,} vs local {f.stat().st_size:,}")
                continue
            verified += 1
            print(f"  VERIFIED {f.name}  ({r['bytes']:,} B, {r['modified']})")
        print(f"\n{ok}/{len(files)} uploaded, {verified}/{len(files)} verified in Asset Testing")
        return 0 if verified == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
