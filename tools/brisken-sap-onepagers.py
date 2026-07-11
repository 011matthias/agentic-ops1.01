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
#
# 2026-07-11 redesign after "bad quality, spacing and aesthetic" feedback:
# real Brisken logo (base64, white+cyan colorway for the dark ground) instead
# of the text stand-in, vertical rhythm distributed over the full sheet
# (space-between, no pooled dead bands), larger type scale, section kickers,
# framed 4-cell capability strip.
import argparse
import os, subprocess, tempfile, sys
from pathlib import Path
from pypdf import PdfReader

REPO = Path(__file__).resolve().parent.parent
OUT_DEFAULT = REPO / "workspace" / "clients" / "brisken" / "deliverables" / "lead-generation" / "sap-assets"
GATE = Path(__file__).resolve().parent / "validate-demo-material.py"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

# Brisken logo, white wordmark + cyan mark (790x173 PNG), inlined so the tool
# regenerates identically from a fresh clone.
LOGO_B64 = "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"

CSS = r"""
*{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
:root{
  --bg0:#081320;--text:#e8eef6;--muted:#9db0c8;--heading:#dbe8fa;
  --line:#1e3550;--line-strong:#2e4865;
  --cyan:#2fc6d6;--cyan-hi:#8fe6ef;--cyan-lo:#4fa8b5;--teal:#3fb9c4;--brandblue:#2f6fd0;
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
  padding:11mm 15mm 9mm;position:relative;overflow:hidden;
}
body::before{content:"";position:absolute;inset:0;
  background-image:linear-gradient(rgba(255,255,255,.022) 1px,transparent 1px),
    linear-gradient(90deg,rgba(255,255,255,.022) 1px,transparent 1px);
  background-size:11mm 11mm;pointer-events:none;}
.topline{position:absolute;top:0;left:0;right:0;height:1.1mm;
  background:linear-gradient(90deg,var(--cyan),var(--brandblue) 60%,transparent);}
.wrap{position:relative;z-index:1;display:flex;flex-direction:column;height:100%;}

header{display:flex;align-items:center;justify-content:space-between;
  padding-bottom:4mm;border-bottom:1px solid var(--line);}
.logo-img{height:7.5mm;display:block;}
.sap-partner{display:flex;align-items:center;gap:2mm;font-size:9.5pt;color:var(--muted);font-weight:600;letter-spacing:.03em;}
.sapbadge{background:#0a66c2;color:#fff;font-size:8pt;font-weight:800;letter-spacing:.05em;padding:.7mm 1.6mm;border-radius:1mm;}

.content{flex:1;display:flex;flex-direction:column;justify-content:space-between;
  gap:4mm;padding:5mm 0 5.5mm;}

.eyebrow{font-size:9pt;letter-spacing:.26em;text-transform:uppercase;color:var(--cyan);font-weight:700;margin-bottom:2.8mm;}
h1{font-size:33pt;font-weight:700;letter-spacing:-1px;color:#f2f7fd;line-height:1.04;}
h1 .ac{color:var(--cyan);}
.promise{font-size:14pt;color:var(--heading);margin-top:2.8mm;font-weight:400;line-height:1.35;max-width:168mm;}
.rename{font-size:9pt;color:var(--muted);margin-top:2.2mm;font-weight:500;}

.kicker{font-size:7.8pt;letter-spacing:.22em;text-transform:uppercase;color:var(--cyan-lo);font-weight:700;}
.sec-label{display:block;margin-bottom:2.6mm;}

.problem{padding:4mm 4.5mm;border-left:2.5px solid var(--cyan);
  background:linear-gradient(90deg, rgba(47,198,214,.09), rgba(47,198,214,.025));
  border-radius:0 2.5mm 2.5mm 0;}
.problem .kicker{display:block;margin-bottom:1.6mm;}
.problem p{font-size:11pt;color:#d5e0ef;line-height:1.45;}

.flow{display:flex;flex-direction:column;align-items:stretch;}
.tier{border:1px solid var(--line-strong);border-radius:3mm;
  background:linear-gradient(180deg, rgba(20,40,66,.78), rgba(12,26,45,.78));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05);padding:4mm 4.5mm;}
.tier.named{border-color:rgba(47,198,214,.45);}
.tier-head{display:flex;align-items:baseline;gap:3.5mm;margin-bottom:3mm;}
.tier-name{font-size:15.5pt;font-weight:700;color:var(--heading);letter-spacing:-.2px;}
.tier-name .ac{color:var(--cyan);}
.chips{display:flex;flex-wrap:wrap;gap:2.4mm;}
.chip{padding:2.3mm 3.4mm;border-radius:2mm;background:rgba(9,20,34,.7);border:1px solid var(--line-strong);
  font-size:10.5pt;font-weight:600;color:#e2ecf8;}
.band{border:1px solid var(--line-strong);border-radius:3mm;padding:3.4mm 4mm;text-align:center;
  background:rgba(9,20,34,.55);font-size:11.5pt;font-weight:600;color:#cfe0f3;letter-spacing:.4px;}
.target{border:1px solid rgba(47,198,214,.5);border-radius:3mm;padding:4mm 4.5mm;
  background:linear-gradient(160deg, rgba(47,198,214,.14), rgba(12,26,45,.45));
  box-shadow:0 0 6mm rgba(47,198,214,.10);display:flex;align-items:center;gap:3.5mm;}
.target .tb{font-size:14pt;font-weight:700;color:#eaf5f8;}
.target .ts{font-size:10pt;color:var(--muted);}
.conn{display:flex;justify-content:center;align-items:center;height:7mm;}
.conn::before{content:"";width:1.5px;height:7mm;background:linear-gradient(var(--cyan),rgba(47,198,214,.15));}
.conn .cv{position:absolute;color:var(--cyan);font-size:11pt;line-height:1;margin-top:5mm;}

.points{list-style:none;display:flex;flex-direction:column;gap:3.2mm;}
.points li{position:relative;padding-left:6.5mm;font-size:11pt;color:#d8e2f0;line-height:1.45;}
.points li::before{content:"";position:absolute;left:1mm;top:2.4mm;width:2.4mm;height:2.4mm;
  background:linear-gradient(135deg,var(--cyan-hi),var(--cyan));transform:rotate(45deg);border-radius:.5mm;}

.caps{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid rgba(47,198,214,.3);
  border-radius:3mm;overflow:hidden;
  background:linear-gradient(160deg, rgba(47,198,214,.08), rgba(12,26,45,.4));}
.cap{padding:3.4mm 2mm 3.2mm;text-align:center;font-size:9.5pt;font-weight:700;color:#eaf5f8;letter-spacing:.02em;}
.cap+.cap{border-left:1px solid rgba(47,198,214,.22);}
.cap::before{content:"";display:block;width:2.2mm;height:2.2mm;margin:0 auto 1.8mm;
  background:linear-gradient(135deg,var(--cyan-hi),var(--cyan));transform:rotate(45deg);border-radius:.5mm;}

footer{border-top:1px solid var(--line);padding-top:3.6mm;}
.trust{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;}
.tm{font-size:8.5pt;color:var(--muted);font-weight:500;padding:0 3mm;position:relative;}
.tm:not(:last-child)::after{content:"";position:absolute;right:0;top:50%;transform:translateY(-50%);width:1mm;height:1mm;border-radius:50%;background:var(--cyan-lo);}
.tm b{color:#c7d6ea;font-weight:700;}
.foot-url{text-align:center;margin-top:2.2mm;font-size:9pt;color:var(--cyan-lo);font-weight:700;letter-spacing:.04em;}
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
<body><div class="topline"></div><div class="wrap">
<header><img class="logo-img" src="data:image/png;base64,{LOGO_B64}" alt="Brisken">
<div class="sap-partner"><span class="sapbadge">SAP</span> Co-Innovation Partner</div></header>
<div class="content">
<div class="hero">
<div class="eyebrow">{eyebrow}</div>
<h1>{name_html}</h1>
<div class="promise">{promise}</div>{rn}
</div>
<div class="problem"><span class="kicker">The problem</span><p>{problem}</p></div>
<div class="flow-sec"><span class="kicker sec-label">How it works</span>{flow_html}</div>
<div class="points-sec"><span class="kicker sec-label">What it delivers</span><ul class="points">{pts}</ul></div>
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
