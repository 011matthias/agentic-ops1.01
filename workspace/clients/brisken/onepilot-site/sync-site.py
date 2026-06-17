# /// script
# requires-python = ">=3.11"
# ///
"""Copy the canonical prototype HTML into ./site/index.html for the build.

Run before every `flyctl deploy`. The served copy under ./site is gitignored;
the single source of truth is the deliverable HTML one directory up.
"""
from pathlib import Path
import shutil

APP = Path(__file__).resolve().parent
SRC = APP.parent / "deliverables" / "brisken-onepilot-website-prototype.html"
DST = APP / "site" / "index.html"

DST.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(SRC, DST)
print(f"synced {SRC.name} -> site/index.html ({DST.stat().st_size} bytes)")
