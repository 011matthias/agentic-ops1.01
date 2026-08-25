# /// script
# dependencies = ["pypdf"]
# ///
"""Task-3: rebuild the TreasuryCentral one-pager without the 'SAP BTP' trust chip.

Reads the shared source HTML read-only, writes a task-scoped copy + PDF.
Chrome headless (not Edge) because the user's Edge is open as the PDF viewer.
"""
import os, re, subprocess, sys, tempfile
from pathlib import Path
from pypdf import PdfReader

SRC = Path(r"C:\Users\neuma_p1qrsic\Repo\agentic-ops1\.scratch\brisken-sap-assets\brisken-treasurycentral-onepager.html")
TASK = Path(r"C:\Users\neuma_p1qrsic\Repo\agentic-ops1-leadgen-task-3\output\leadgen-task-3")
HTML = TASK / "build" / "brisken-treasurycentral-onepager-btp-clean.html"
PDF = TASK / "collateral-pack" / "brisken-treasurycentral-onepager.pdf"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

html = SRC.read_text(encoding="utf-8")
before = len(re.findall(r"BTP", html, re.I))
# Remove ONLY the BTP trust chip; leave every other chip and all body copy intact.
html2, n = re.subn(r'<span class="tm">\s*SAP BTP\s*</span>', "", html)
after = len(re.findall(r"BTP", html2, re.I))
print(f"source BTP refs={before}  chips removed={n}  remaining={after}")
if after != 0:
    sys.exit(f"FAIL: {after} BTP refs still in HTML")
HTML.write_text(html2, encoding="utf-8")

tmp = PDF.with_name(PDF.name + ".tmp")
tmp.unlink(missing_ok=True)
with tempfile.TemporaryDirectory(prefix="tc-onepager-") as prof:
    cmd = [str(CHROME), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           "--no-first-run", "--no-default-browser-check",
           f"--user-data-dir={prof}", f"--print-to-pdf={tmp}", HTML.as_uri()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"chrome exit {r.returncode}")
if not tmp.is_file() or tmp.stat().st_size == 0:
    raise SystemExit("chrome produced nothing")
os.replace(tmp, PDF)

rd = PdfReader(str(PDF))
txt = "\n".join((p.extract_text() or "") for p in rd.pages)
btp = len(re.findall(r"\bBTP\b", txt, re.I))
print(f"PDF pages={len(rd.pages)} size={round(PDF.stat().st_size/1024)}KB BTP_in_pdf={btp}")
for chip in ["Co-Innovation", "SAP Store", "ISO 27001", "SOC 1"]:
    print(f"  kept '{chip}': {chip.lower() in txt.lower()}")
if len(rd.pages) != 1:
    raise SystemExit("FAIL: not single-page")
if btp != 0:
    raise SystemExit("FAIL: BTP survived into PDF")
print("OK single-page, BTP-free")
