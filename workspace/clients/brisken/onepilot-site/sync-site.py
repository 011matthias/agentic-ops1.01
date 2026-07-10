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
DELIVERABLES = APP.parent / "deliverables"
SITE = APP / "site"
SITE.mkdir(parents=True, exist_ok=True)

# (source deliverable, served file name)
PAGES = [
    ("brisken-onepilot-website-prototype.html", "index.html"),
    ("brisken-onepilot-website-prototype.html", "brisken-onepilot-website-prototype.html"),
    ("brisken-onepilot-platform.html", "brisken-onepilot-platform.html"),
]
for src_name, dst_name in PAGES:
    src = DELIVERABLES / src_name
    dst = SITE / dst_name
    shutil.copyfile(src, dst)
    print(f"synced {src_name} -> site/{dst_name} ({dst.stat().st_size} bytes)")
