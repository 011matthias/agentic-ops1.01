# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf"]
# ///
# Source of truth for the 6 Brisken SAP Resources one-pagers (visual,
# dark-cockpit brand). Renders each HTML -> A4-portrait single-page PDF via
# Chrome headless (Edge headless silently fails while Edge is open, so Chrome
# + isolated profile is the working engine), verifies each PDF is exactly
# 1 page, then runs the banned-content gate (validate-demo-material.py,
# --client brisken) on the rendered PDFs. Dirk's "Exclude BTP from all demos"
# directive was fixed HERE on 2026-07-09; regenerating from any older copy of
# this file would silently reintroduce the term, which is why the gate run is
# part of the render, not a separate step.
#
# Promoted from gitignored .scratch/brisken-sap-assets/gen_onepagers.py on
# 2026-07-10 so the BTP fix is versioned.
import argparse
import os, subprocess, tempfile, sys
from pathlib import Path
from pypdf import PdfReader

REPO = Path(__file__).resolve().parent.parent
OUT_DEFAULT = REPO / "workspace" / "clients" / "brisken" / "deliverables" / "lead-generation" / "sap-assets"
GATE = Path(__file__).resolve().parent / "validate-demo-material.py"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

CSS = r"""
*{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
:root{
  --bg0:#081320;--text:#e8eef6;--muted:#9db0c8;--heading:#dbe8fa;
  --line:#1e3550;--line-strong:#2e4865;
  --cyan:#2fc6d6;--cyan-hi:#8fe6ef;--cyan-lo:#3f96a3;--teal:#3fb9c4;--brandblue:#2f6fd0;
}
@page{size:A4;margin:0;}
html,body{width:210mm;height:297mm;}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact;}
body{
  font-family:"Segoe UI",system-ui,-apple-system,sans-serif;
  background:
    radial-gradient(150mm 70mm at 50% -6%, rgba(47,198,214,.16), transparent 60%),
    radial-gradient(130mm 85mm at 108% 118%, rgba(45,111,208,.14), transparent 55%),
    linear-gradient(160deg,#0a1728 0%, var(--bg0) 55%, #060f1c 100%);
  color:var(--text);-webkit-font-smoothing:antialiased;
  padding:13mm 14mm 10mm;position:relative;overflow:hidden;
}
body::before{content:"";position:absolute;inset:0;
  background-image:linear-gradient(rgba(255,255,255,.022) 1px,transparent 1px),
    linear-gradient(90deg,rgba(255,255,255,.022) 1px,transparent 1px);
  background-size:11mm 11mm;pointer-events:none;}
.wrap{position:relative;z-index:1;display:flex;flex-direction:column;height:100%;}

header{display:flex;align-items:center;justify-content:space-between;margin-bottom:6mm;}
.brand{display:flex;align-items:center;gap:2.5mm;}
.logo{font-size:20pt;font-weight:700;letter-spacing:-.5px;color:#eef4fb;}
.dia{width:3.2mm;height:3.2mm;background:linear-gradient(135deg,var(--cyan-hi),var(--cyan));transform:rotate(45deg);border-radius:.7mm;box-shadow:0 0 4mm rgba(47,198,214,.55);}
.sap-partner{display:flex;align-items:center;gap:2mm;font-size:9.5pt;color:var(--muted);font-weight:600;letter-spacing:.03em;}
.sapbadge{background:#0a66c2;color:#fff;font-size:8pt;font-weight:800;letter-spacing:.05em;padding:.7mm 1.6mm;border-radius:1mm;}

.eyebrow{font-size:8.5pt;letter-spacing:.22em;text-transform:uppercase;color:var(--cyan-lo);font-weight:700;margin-bottom:2.5mm;}
h1{font-size:29pt;font-weight:700;letter-spacing:-1px;color:#f2f7fd;line-height:1.02;}
h1 .ac{color:var(--cyan);}
.promise{font-size:13pt;color:var(--heading);margin-top:2.5mm;font-weight:400;line-height:1.3;}
.rename{font-size:8.5pt;color:var(--muted);margin-top:2mm;font-weight:500;}

.problem{margin:6mm 0 5mm;padding:3.4mm 4mm;border-left:2.5px solid var(--cyan);
  background:rgba(47,198,214,.07);border-radius:0 2mm 2mm 0;font-size:10.5pt;color:#cdd9ea;line-height:1.4;}

.flow{display:flex;flex-direction:column;align-items:stretch;margin:1mm 0 3mm;}
.tier{border:1px solid var(--line);border-radius:3mm;
  background:linear-gradient(180deg, rgba(20,40,66,.72), rgba(12,26,45,.72));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);padding:3.6mm 4mm;}
.tier.named{border-color:rgba(47,198,214,.42);}
.tier-head{display:flex;align-items:baseline;gap:3.5mm;margin-bottom:3mm;}
.tier-name{font-size:15pt;font-weight:700;color:var(--heading);letter-spacing:-.2px;}
.tier-name .ac{color:var(--cyan);}
.kicker{font-size:7.5pt;letter-spacing:.18em;text-transform:uppercase;color:var(--cyan-lo);font-weight:700;}
.chips{display:flex;flex-wrap:wrap;gap:2.2mm;}
.chip{padding:2mm 3mm;border-radius:2mm;background:rgba(9,20,34,.66);border:1px solid var(--line);
  font-size:10pt;font-weight:600;color:#dbe7f6;}
.band{border:1px solid var(--line);border-radius:3mm;padding:3mm 4mm;text-align:center;
  background:rgba(9,20,34,.5);font-size:11pt;font-weight:600;color:#cfe0f3;letter-spacing:.2px;}
.target{border:1px solid rgba(47,198,214,.4);border-radius:3mm;padding:3.4mm 4mm;
  background:linear-gradient(160deg, rgba(47,198,214,.12), rgba(12,26,45,.4));
  display:flex;align-items:center;gap:3.5mm;}
.target .tb{font-size:13.5pt;font-weight:700;color:#eaf5f8;}
.target .ts{font-size:9.5pt;color:var(--muted);}
.conn{display:flex;justify-content:center;align-items:center;height:6mm;}
.conn::before{content:"";width:1.5px;height:6mm;background:linear-gradient(var(--cyan),rgba(47,198,214,.15));}
.conn .cv{position:absolute;color:var(--cyan);font-size:11pt;line-height:1;margin-top:4mm;}

.points{list-style:none;margin:1mm 0 0;display:flex;flex-direction:column;gap:2.6mm;}
.points li{position:relative;padding-left:6mm;font-size:10.5pt;color:#d3ddec;line-height:1.4;}
.points li::before{content:"";position:absolute;left:1mm;top:2.2mm;width:2.2mm;height:2.2mm;
  background:linear-gradient(135deg,var(--cyan-hi),var(--cyan));transform:rotate(45deg);border-radius:.5mm;}

.content{flex:1;display:flex;flex-direction:column;justify-content:center;padding:3mm 0;}
.caps{display:flex;gap:2.2mm;flex-wrap:wrap;margin:5mm 0 0;}
.cap{flex:1;min-width:32mm;text-align:center;padding:2.6mm 2mm;border-radius:2mm;
  background:linear-gradient(160deg, rgba(47,198,214,.10), rgba(12,26,45,.4));
  border:1px solid rgba(47,198,214,.26);font-size:9pt;font-weight:700;color:#eaf5f8;letter-spacing:.02em;}

footer{border-top:1px solid var(--line);padding-top:3.5mm;}
.trust{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;}
.tm{font-size:8pt;color:var(--muted);font-weight:500;padding:0 3mm;position:relative;}
.tm:not(:last-child)::after{content:"";position:absolute;right:0;top:50%;transform:translateY(-50%);width:1mm;height:1mm;border-radius:50%;background:var(--cyan-lo);}
.tm b{color:#c7d6ea;font-weight:700;}
.foot-url{text-align:center;margin-top:2.5mm;font-size:8.5pt;color:var(--cyan-lo);font-weight:700;letter-spacing:.04em;}
"""

def chips(items):
    return '<div class="chips">' + "".join(f'<span class="chip">{c}</span>' for c in items) + "</div>"

def tier(items, label=None, name=None):
    head = ""
    if name or label:
        parts = []
        if name: parts.append(f'<span class="tier-name">{name}</span>')
        if label: parts.append(f'<span class="kicker">{label}</span>')
        head = '<div class="tier-head">' + "".join(parts) + "</div>"
    cls = "tier named" if name else "tier"
    return f'<div class="{cls}">{head}{chips(items)}</div>'

def band(text):
    return f'<div class="band">{text}</div>'

def target(big, sub):
    return (f'<div class="target"><span class="sapbadge">SAP</span>'
            f'<span class="tb">{big}</span><span class="ts">{sub}</span></div>')

def conn():
    return '<div class="conn"><span class="cv">&#9660;</span></div>'

def flow(*parts):
    return '<div class="flow">' + conn().join(parts) + "</div>"

TRUST = ["<b>SAP</b> Co-Innovation Partner","SAP Store","<b>ISO 27001</b>","<b>SOC 1 Type II</b>","live with customers today"]

def page(name_html, eyebrow, promise, problem, flow_html, points, caps, rename=None):
    rn = f'<div class="rename">{rename}</div>' if rename else ""
    pts = "".join(f"<li>{p}</li>" for p in points)
    cps = "".join(f'<span class="cap">{c}</span>' for c in caps)
    tms = "".join(f'<span class="tm">{t}</span>' for t in TRUST)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>{CSS}</style></head>
<body><div class="wrap">
<header><div class="brand"><span class="logo">brisken</span><span class="dia"></span></div>
<div class="sap-partner"><span class="sapbadge">SAP</span> Co-Innovation Partner</div></header>
<div class="content">
<div class="eyebrow">{eyebrow}</div>
<h1>{name_html}</h1>
<div class="promise">{promise}</div>{rn}
<div class="problem">{problem}</div>
{flow_html}
<ul class="points">{pts}</ul>
<div class="caps">{cps}</div>
</div>
<footer><div class="trust">{tms}</div><div class="foot-url">www.brisken.com</div></footer>
</div></body></html>"""

PRODUCTS = [
 dict(slug="brisken-market-data-hub-onepager",
   name_html="Market Data Hub", eyebrow="Market data &middot; on your SAP data",
   promise="One point of control for market data, into SAP, no code.",
   problem="Rates, curves and prices arrive from every provider in a different shape, and most of it still lands in SAP as a hand-keyed upload.",
   flow_html=flow(
     tier(["Bloomberg","Refinitiv","CME Group","360T","Deutsche Boerse","OANDA","central banks"], label="Providers"),
     band("govern &middot; transform &middot; distribute"),
     target("SAP and non-SAP","ECC / S/4HANA, both ways, no code")),
   points=[
     "Ingest rates, curves and prices from every provider through one managed feed.",
     "Govern entitlements and usage centrally, so the same number reaches every system that needs it.",
     "Retire the brittle point-to-point scripts and hand-keyed uploads for a single source of truth."],
   caps=["no code","one governed feed","SAP + non-SAP","full audit"]),

 dict(slug="brisken-smart-trading-onepager",
   name_html="Brisken Smart Trading", eyebrow="Trade capture &middot; into SAP TRM",
   promise="The trade lifecycle end to end, from the venue into SAP, no re-key.",
   rename="Formerly Trade Automation / TraderPlus, now Brisken Smart Trading (BST).",
   problem="Treasury desks still re-key trades from the execution venue into SAP TRM by hand. It is slow, it is a control risk, and it breaks the moment a venue changes a field.",
   flow_html=flow(
     band("decision &middot; approval &middot; execution"),
     tier(["FXall","Bloomberg FX GO","360T","BidFX"], label="Execution venues"),
     target("SAP TRM &amp; FAM","deal created straight through")),
   points=[
     "Capture the trade at the execution venue and create the deal in SAP straight through, validated.",
     "Trading-venue and TMS agnostic, so a new venue is configuration, not a rebuild.",
     "Four-eye approval, segregation of duties and a full audit trail, with no ABAP and no per-venue interface to maintain."],
   caps=["no re-key","venue + TMS agnostic","governed by design","configured, not coded"]),

 dict(slug="brisken-remittance-advice-gate-onepager",
   name_html="Remittance Advice Gate", eyebrow="Remittance &middot; into SAP S/4HANA",
   promise="Remittances read by AI, straight into SAP. Nobody retypes anything.",
   problem="Remittance advices arrive as unstructured emails and attachments, and someone has to read each one and key it into SAP.",
   flow_html=flow(
     tier(["remittance emails","attachments"], label="Unstructured in"),
     band("AI reads &middot; structures &middot; matches"),
     target("SAP S/4HANA","posted, matched, governed")),
   points=[
     "An LLM reads unstructured remittance emails and attachments, structures them, and posts to SAP S/4HANA.",
     "Matched and governed on the way in, so exceptions surface and the rest flows through.",
     "Live in production today: one S/4HANA customer removed the manual step from remittance processing entirely."],
   caps=["LLM-read","matched + governed","no manual keying","full audit"]),

 dict(slug="brisken-bank-fee-portal-onepager",
   name_html="Bank Fee Portal", eyebrow="Bank fees &middot; inside SAP",
   promise="Analyze and validate bank fees against your agreements, inside SAP.",
   problem="Bank fees are hard to check against what was actually agreed, and overcharges slip through because nobody reconciles them line by line.",
   flow_html=flow(
     tier(["bank fee statements"], label="In"),
     band("validate against your agreements"),
     target("Inside SAP","variance flags, full audit trail")),
   points=[
     "Compare charged fees against your negotiated agreements and flag the variances.",
     "Keep the whole check inside SAP, with a full audit trail on every line."],
   caps=["inside SAP","agreement-checked","variance flags","full audit"]),

 dict(slug="brisken-treasurycentral-onepager",
   name_html="Treasury<span class='ac'>Central</span>", eyebrow="The cockpit &middot; on your SAP data",
   promise="The single screen treasury works in, on your SAP data.",
   problem="Treasury runs across cash, investments, debt, FX and market data in separate tools, with governance bolted on after the fact.",
   flow_html=flow(
     tier(["Cash","Investments","Debt","FX","Market Data","Governance"],
          name="Treasury<span class='ac'>Central</span>", label="the cockpit"),
     target("On your SAP data","SAP ECC / S/4HANA, every move governed and logged")),
   points=[
     "See the position and act on it in one place, across cash, investments, debt, FX, market data and governance.",
     "Every move governed and logged, on your SAP data, with no separate data store to reconcile."],
   caps=["one screen","six domains","governed + logged","on your SAP data"]),

 dict(slug="brisken-onepilot-onepager",
   name_html="One<span class='ac'>Pilot</span>", eyebrow="The AI layer &middot; on your SAP data",
   promise="The governed AI layer that operates your SAP treasury apps, in production today.",
   problem="Automation across treasury usually means bespoke code, and the more you build the more there is to maintain and audit.",
   flow_html=flow(
     tier(["Market Data Hub","Smart Trading","Remittance Advice Gate","Bank Fee Portal"],
          name="One<span class='ac'>Pilot</span>", label="the governed AI layer"),
     target("SAP and non-SAP","bi-directional, across your landscape")),
   points=[
     "The autonomous layer across the applications: it asks, automates and acts on your treasury operations, inside your controls.",
     "Validation, anomaly detection, segregation of duties and four-eye approval, with a full audit trail.",
     "Codeless framework: build your own apps and automation without a line of code.",
     "Manage by exception; your team stays in command."],
   caps=["on your SAP data","SAP + non-SAP","four-eye + SoD","manage by exception"]),
]

def render(html_path: Path, pdf_path: Path):
    tmp_out = pdf_path.with_name(pdf_path.name + ".tmp")
    tmp_out.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="sap-onepager-") as prof:
        cmd = [str(CHROME),"--headless=new","--disable-gpu","--no-pdf-header-footer",
               "--no-first-run","--no-default-browser-check",
               f"--user-data-dir={prof}",f"--print-to-pdf={tmp_out}",html_path.as_uri()]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            sys.stderr.write(r.stdout + r.stderr)
            raise SystemExit(f"chrome exit {r.returncode} on {html_path.name}")
    if not tmp_out.is_file() or tmp_out.stat().st_size == 0:
        raise SystemExit(f"chrome produced nothing for {html_path.name}")
    os.replace(tmp_out, pdf_path)

def run_gate(pdfs: list[Path]) -> bool:
    r = subprocess.run(
        ["uv", "run", str(GATE), "--client", "brisken", "--quiet", *map(str, pdfs)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
    return r.returncode == 0

def main() -> int:
    ap = argparse.ArgumentParser(description="Render the 6 Brisken SAP one-pagers and gate them.")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT,
                    help=f"PDF output dir (default: {OUT_DEFAULT})")
    args = ap.parse_args()

    if not CHROME.is_file():
        sys.exit(f"Chrome not found at {CHROME}; it is the only render engine that works while Edge is open")

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    print("PRODUCT | pages | size KB")
    all_ok = True
    pdfs: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="sap-onepager-html-") as html_dir:
        for p in PRODUCTS:
            html = page(p["name_html"], p["eyebrow"], p["promise"], p["problem"],
                        p["flow_html"], p["points"], p["caps"], p.get("rename"))
            hp = Path(html_dir) / f'{p["slug"]}.html'
            hp.write_text(html, encoding="utf-8")
            pdf = out / f'{p["slug"]}.pdf'
            render(hp, pdf)
            pdfs.append(pdf)
            pages = len(PdfReader(str(pdf)).pages)
            kb = round(pdf.stat().st_size/1024)
            flag = "" if pages == 1 else "  <-- NOT 1 PAGE"
            if pages != 1: all_ok = False
            print(f'{p["slug"]:42s} | {pages} | {kb}{flag}')
    print("ALL SINGLE-PAGE" if all_ok else "PAGE-COUNT FAILURE")

    if not run_gate(pdfs):
        print("BANNED-CONTENT GATE FAILED on the rendered PDFs; do not ship them")
        return 1
    print("banned-content gate: PASS")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
