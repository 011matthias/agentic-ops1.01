# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf"]
# ///
# Source of truth for the 6 Brisken SAP Resources one-pagers (visual brand),
# served at resources.brisken.com under the "Product Deck" heading.
#
# Renders each HTML -> A4-portrait single-page PDF via Chrome headless (Edge
# headless silently fails while Edge is open, so Chrome + isolated profile is
# the working engine), verifies each PDF is exactly 1 page, then runs the
# banned-content gate (validate-demo-material.py, --client brisken) on the
# rendered PDFs. Dirk's "Exclude BTP from all demos" directive is honored here;
# no BTP / Evonik / RWZ strings anywhere in the copy.
#
# 2026-07-14 REDESIGN (client dissatisfied with the 07-13 set; owner direction
# "this direction, light system, roll to all 6"). Fixes applied to every sheet:
#   1. REAL brand logos where a product genuinely aggregates named systems
#      (Market Data Hub provider strip = Bloomberg / LSEG / ICE / CME, the exact
#      set on Dirk's approved MDH deck; the real SAP logo on SAP destination
#      nodes). Logos load from tools/fixtures/brisken-sap-logos/ (committed, so
#      the tool stays reproducible; earlier versions embedded one logo inline).
#      Chips are fixed-height / width:auto so aspect is never stretched
#      (Dirk's "kein verzerren").
#   2. NO REPETITION. The prior set restated the same 3-4 points as promise,
#      then bullets, then how-it-works, then caps. Each sheet now runs ONE
#      narrative: promise -> a primary VISUAL -> mechanism -> one DISTINCT band
#      (what retires / what it replaces / the production proof), never a
#      restatement of an earlier line.
#   3. FILLS the page with signal, not stretched gaps. main uses
#      justify-content:space-between across solid blocks, so the sheet reads as
#      deliberate bands rather than "ran out of content".
# The header (brisken logo + SAP Co-Innovation Partner), footer, font pairing
# (IBM Plex Sans + Space Grotesk) and per-product accent stay constant: this is
# a product FAMILY, so the frame is shared and the body composition varies.
# All copy claims trace to the gated 2026-07-12 set (same claims, reorganized).
import argparse
import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader

REPO = Path(__file__).resolve().parent.parent
OUT_DEFAULT = REPO / "workspace" / "clients" / "brisken" / "deliverables" / "lead-generation" / "sap-assets"
WEB_OUT_DEFAULT = REPO / "workspace" / "clients" / "brisken" / "resources-site"
GATE = REPO / "tools" / "validate-demo-material.py"
LOGO_DIR = REPO / "tools" / "fixtures" / "brisken-sap-logos"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def _b64(name: str) -> str:
    return base64.b64encode((LOGO_DIR / f"{name}.png").read_bytes()).decode()


LOGOS = {k: _b64(k) for k in ("brisken", "bloomberg", "lseg", "ice", "cme", "sap")}
# Square Brisken mark for the browser-tab favicon (150x150). Every served page
# carries it so the tab reads "Brisken" with the logo, not a default globe.
FAVICON = _b64("brisken-favicon")


def lchip(key: str) -> str:
    return (f'<span class="lchip"><img src="data:image/png;base64,{LOGOS[key]}" alt=""></span>')


# --------------------------------------------------------------------------- #
BASE_CSS = r"""
*{box-sizing:border-box;margin:0;padding:0;}
@page{size:A4;margin:0;}
html,body{width:210mm;height:297mm;font-family:'IBM Plex Sans',sans-serif;color:#0f172a;background:#fff;}
.topline{position:absolute;top:0;left:0;right:0;height:1.3mm;background:linear-gradient(90deg,var(--ac),var(--ac2));}
.sheet{position:relative;height:100%;display:flex;flex-direction:column;padding:11mm 13mm 8mm;}
header{display:flex;justify-content:space-between;align-items:center;padding-bottom:5mm;border-bottom:1px solid #e6ebf2;}
.logo-img{height:8mm;}
.partner{font-size:11pt;color:#475569;font-weight:500;display:flex;align-items:center;gap:2.4mm;}
.sapbadge{background:#0a6ed1;color:#fff;font-weight:700;font-size:9pt;padding:1mm 2mm;border-radius:1.2mm;letter-spacing:.5px;}
main{flex:1;display:flex;flex-direction:column;padding-top:6mm;justify-content:space-between;gap:6mm;min-height:0;}
.eyebrow{font-family:'Space Grotesk';font-size:10.5pt;font-weight:600;letter-spacing:2.4px;text-transform:uppercase;color:var(--ac);}
h1{font-family:'Space Grotesk';font-size:37pt;font-weight:700;line-height:1.02;letter-spacing:-1px;margin:3mm 0 4mm;}
h1 .ac{color:var(--ac);}
.promise{font-size:13pt;color:#475569;line-height:1.4;}
.rename{font-size:9.6pt;color:#94a3b8;margin-top:3mm;}
.band-lab{font-family:'Space Grotesk';font-size:10.5pt;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--ac);margin-bottom:3.5mm;}
.p{font-size:11.4pt;color:#334155;line-height:1.5;}

/* hero: text left, visual right */
.hero{display:grid;grid-template-columns:.82fr 1.18fr;gap:11mm;align-items:center;}
.hero.stack{display:block;}
.hero.stack h1{font-size:33pt;}

/* light bordered visual panel + small caption label */
.panel{background:#f6f9fc;border:1px solid #e6ebf2;border-radius:4mm;padding:7mm;}
.vlab{font-family:'Space Grotesk';font-size:9.2pt;font-weight:600;letter-spacing:1.6px;text-transform:uppercase;color:#64748b;text-align:center;margin-bottom:5mm;}

/* logo strip */
.logos{display:grid;grid-template-columns:repeat(4,1fr);gap:3.5mm;}
.lchip{background:#fff;border:1px solid #e6ebf2;border-radius:2.4mm;height:15mm;display:flex;align-items:center;justify-content:center;padding:3mm 3.5mm;box-shadow:0 1px 3px rgba(15,23,42,.05);}
.lchip img{max-height:8mm;max-width:100%;width:auto;object-fit:contain;}

/* MDH convergence funnel */
.funnel{display:flex;flex-direction:column;align-items:center;margin-top:5mm;gap:3mm;}
.stem{width:1.4px;height:6mm;background:var(--ac);opacity:.55;}
.feed{background:var(--ac);color:#fff;font-family:'Space Grotesk';font-weight:700;font-size:14pt;padding:3.6mm 9mm;border-radius:99px;box-shadow:0 3px 10px var(--glow);}
.outs{display:flex;gap:4mm;margin-top:1mm;}
.out{border:1.4px solid var(--ac);color:#0f172a;font-weight:600;font-size:11pt;padding:2mm 6mm;border-radius:99px;background:#fff;}
.vcap{text-align:center;font-size:10pt;color:#64748b;margin-top:5mm;}

/* how it works / numbered steps */
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:8mm;}
.step{border-top:2px solid var(--ac);padding-top:3.5mm;}
.sn{font-family:'Space Grotesk';font-size:15pt;font-weight:700;color:var(--ac);}
.st{font-size:12.2pt;font-weight:700;margin:1.5mm 0;}
.sd{font-size:10pt;color:#64748b;line-height:1.45;}

/* two columns */
.cols2{display:grid;grid-template-columns:1fr 1fr;gap:11mm;}

/* bullet list */
.dots{list-style:none;display:flex;flex-direction:column;gap:2.6mm;margin-top:1mm;}
.dots li{font-size:10.8pt;color:#334155;line-height:1.44;padding-left:5.6mm;position:relative;}
.dots li::before{content:"";position:absolute;left:0;top:1.7mm;width:2.1mm;height:2.1mm;background:var(--ac);border-radius:.5mm;transform:rotate(45deg);}

/* distinct dark band (retire / built-in / proof) */
.dark{background:#0f172a;border-radius:4mm;padding:6.5mm 8mm;color:#e2e8f0;display:grid;grid-template-columns:.62fr 1.38fr;gap:9mm;align-items:center;}
.dark h3{font-family:'Space Grotesk';font-size:16pt;font-weight:700;color:#fff;line-height:1.12;}
.dark h3 span{color:var(--ac2);}
.rlist{display:flex;flex-direction:column;gap:3mm;}
.ritem{display:flex;align-items:flex-start;gap:3.5mm;font-size:11.2pt;color:#cbd5e1;line-height:1.35;}
.rmk{color:var(--ac2);font-weight:700;font-size:12.5pt;flex:0 0 auto;line-height:1.1;}
.darkfull{grid-template-columns:1fr;text-align:center;gap:3mm;}
.darkfull p{font-size:12.5pt;color:#cbd5e1;line-height:1.4;}
.darkfull b{color:#fff;}

/* remittance vertical flow */
.rflow{display:flex;flex-direction:column;align-items:center;gap:3.4mm;}
.rrow{display:flex;flex-wrap:wrap;justify-content:center;gap:2.5mm;}
.dpill{background:#fff;border:1px solid #e6ebf2;border-radius:2mm;padding:2.4mm 4mm;font-size:10.4pt;color:#475569;box-shadow:0 1px 2px rgba(15,23,42,.04);}
.rside{font-size:9.4pt;color:#94a3b8;}
.dai{background:var(--ac);color:#fff;font-family:'Space Grotesk';font-weight:700;font-size:11pt;text-align:center;padding:2.8mm 6mm;border-radius:99px;box-shadow:0 3px 10px var(--glow);}
.sapnode{display:flex;align-items:center;gap:3mm;background:#fff;border:1.4px solid var(--ac);border-radius:2.4mm;padding:3mm 5mm;}
.sapnode img{height:6.4mm;width:auto;}
.sapnode b{font-size:12.5pt;}

/* bank fee chart + ledger */
.fee{display:grid;grid-template-columns:.78fr 1.22fr;gap:6mm;}
.chart{display:flex;align-items:flex-end;justify-content:center;gap:6mm;height:56mm;padding-bottom:2mm;border-bottom:1px solid #e6ebf2;}
.cbar{display:flex;flex-direction:column;align-items:center;gap:2.4mm;}
.col{width:13mm;border-radius:1.6mm 1.6mm 0 0;position:relative;}
.col .over{position:absolute;top:0;left:0;right:0;height:40%;background:repeating-linear-gradient(45deg,rgba(234,88,12,.55),rgba(234,88,12,.55) 1.4mm,transparent 1.4mm,transparent 2.8mm);border-bottom:1px dashed #ea580c;}
.clab{font-size:9pt;color:#64748b;text-align:center;line-height:1.3;}
.clab b{display:block;font-size:10.6pt;color:#0f172a;}
.ledger{border:1px solid #e6ebf2;border-radius:3mm;overflow:hidden;}
.lhead{background:#f6f9fc;font-family:'Space Grotesk';font-size:9pt;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:#64748b;padding:2.6mm 4mm;border-bottom:1px solid #e6ebf2;}
.lrow{display:flex;justify-content:space-between;align-items:center;gap:2.5mm;padding:2.5mm 3.4mm;font-size:9.8pt;border-bottom:1px solid #eef2f7;}
.lrow:last-child{border-bottom:none;}
.lrow>span:first-child{flex:1;min-width:0;}
.ltag{font-size:8.2pt;font-weight:600;padding:.7mm 2.2mm;border-radius:99px;white-space:nowrap;}
.ltag.ok{background:#ecfdf5;color:#059669;}
.ltag.flag{background:#fff7ed;color:#ea580c;}

/* treasurycentral radial (full-width, stacked) */
.radial{position:relative;height:82mm;}
.radial svg{position:absolute;inset:0;width:100%;height:100%;}
.rad-core{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:34mm;height:34mm;border-radius:50%;background:var(--ac);color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 4px 16px var(--glow);z-index:2;}
.rad-core .c1{font-family:'Space Grotesk';font-weight:700;font-size:12pt;line-height:1;}
.rad-core .c1 .ac{color:#fff;opacity:.85;}
.rad-core .c2{font-size:8.4pt;opacity:.85;margin-top:1mm;}
.rad-node{position:absolute;transform:translate(-50%,-50%);background:#fff;border:1px solid #e6ebf2;border-radius:99px;padding:2mm 4.5mm;font-size:10pt;font-weight:600;color:#0f172a;box-shadow:0 1px 3px rgba(15,23,42,.06);white-space:nowrap;z-index:1;}

/* onepilot architecture (dark panel is the primary visual) */
.arch{background:#0f172a;border-radius:4mm;padding:7mm;position:relative;overflow:hidden;}
.arch::before{content:"";position:absolute;top:-40mm;left:50%;transform:translateX(-50%);width:120mm;height:80mm;background:radial-gradient(ellipse at center,var(--glow),transparent 70%);}
.arch-top{position:relative;text-align:center;border:1.4px solid var(--ac);border-radius:3mm;padding:3.6mm;color:#fff;font-family:'Space Grotesk';font-weight:700;font-size:15pt;background:rgba(147,51,234,.12);}
.arch-top .ac{color:var(--ac2);}
.arch-top .lab{display:block;font-family:'IBM Plex Sans';font-weight:600;font-size:9pt;letter-spacing:1.6px;text-transform:uppercase;color:#94a3b8;margin-top:1.4mm;}
.arch-conn{position:relative;width:1.4px;height:5mm;background:var(--ac);opacity:.55;margin:0 auto;}
.arch-pillars{position:relative;display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;}
.pil{border:1px solid rgba(148,163,184,.4);border-radius:2.4mm;background:rgba(255,255,255,.03);color:#e2e8f0;text-align:center;font-weight:600;font-size:10.4pt;padding:5mm 2mm;}
.arch-base{position:relative;text-align:center;color:#94a3b8;font-size:10.4pt;margin-top:4.5mm;padding-top:4mm;border-top:1px solid rgba(148,163,184,.25);}
.arch-base b{color:#e2e8f0;}

/* proof + footer */
.proof{display:flex;justify-content:center;flex-wrap:wrap;gap:3mm;}
.pchip{border:1px solid #e6ebf2;border-radius:99px;padding:2mm 5mm;font-size:9.6pt;color:#475569;display:flex;align-items:center;gap:2mm;}
footer{text-align:center;font-size:9.6pt;color:#94a3b8;padding-top:5mm;margin-top:5mm;border-top:1px solid #e6ebf2;}
footer b{color:#475569;}
"""


PROOF = ('<div class="proof">'
         '<span class="pchip"><span class="sapbadge">SAP</span> Co-Innovation Partner</span>'
         '<span class="pchip">SAP Store</span>'
         '<span class="pchip">ISO 27001</span>'
         '<span class="pchip">SOC 1 Type II</span>'
         '<span class="pchip">Live with customers today</span>'
         '</div>')


def dots(points):
    return '<ul class="dots">' + "".join(f"<li>{p}</li>" for p in points) + "</ul>"


def dark_band(title_html, items, mark="&times;"):
    lis = "".join(f'<div class="ritem"><span class="rmk">{mark}</span>{t}</div>' for t in items)
    return (f'<div class="dark"><h3>{title_html}</h3>'
            f'<div class="rlist">{lis}</div></div>')


# ---- per-product body builders (each a distinct composition) --------------
def body_market_data_hub():
    return f'''<main>
  <div class="hero">
    <div>
      <div class="eyebrow">Market data</div>
      <h1>Market<br>Data Hub</h1>
      <p class="promise">Every rate, curve and price through one managed feed. No hand-keyed uploads.</p>
    </div>
    <div class="panel">
      <div class="vlab">Every provider &middot; one feed</div>
      <div class="logos">{lchip("bloomberg")}{lchip("lseg")}{lchip("ice")}{lchip("cme")}</div>
      <div class="funnel">
        <div class="stem"></div>
        <div class="feed">one governed feed</div>
        <div class="stem"></div>
        <div class="outs"><span class="out">SAP</span><span class="out">non-SAP</span></div>
      </div>
      <div class="vcap">Both directions, no code. Central banks included.</div>
    </div>
  </div>
  <div>
    <div class="band-lab">How it works</div>
    <div class="steps">
      <div class="step"><div class="sn">1</div><div class="st">Ingest</div><div class="sd">Every provider's rates, curves and prices, each in its own format.</div></div>
      <div class="step"><div class="sn">2</div><div class="st">Govern</div><div class="sd">One managed feed controls entitlements and usage in a single place.</div></div>
      <div class="step"><div class="sn">3</div><div class="st">Distribute</div><div class="sd">The same number to SAP and non-SAP, both ways, straight through.</div></div>
    </div>
  </div>
  {dark_band("What it <span>retires</span>", [
      "Per-provider upload scripts, maintained by hand",
      "Rates re-keyed into spreadsheets before they reach SAP",
      "Point-to-point integrations that break when a feed changes"])}
</main>'''


def body_smart_trading():
    return f'''<main>
  <div class="hero">
    <div>
      <div class="eyebrow">Trade capture</div>
      <h1>Brisken<br>Smart Trading</h1>
      <p class="promise">The trade lifecycle from venue to booked deal, straight through. No re-keying.</p>
      <p class="rename">Formerly Trade Automation / TraderPlus. Now Brisken Smart Trading (BST).</p>
    </div>
    <div class="panel">
      <div class="vlab">Venue to SAP, straight through</div>
      <div class="steps" style="grid-template-columns:1fr;gap:4mm;">
        <div class="step"><div class="sn">01</div><div class="st">Decide &amp; approve</div><div class="sd">Decision, approval and execution, with the controls applied up front.</div></div>
        <div class="step"><div class="sn">02</div><div class="st">Execution venues</div><div class="sd">Captured at the venue: Bloomberg FX GO, FXall, 360T, BidFX and more.</div></div>
        <div class="step"><div class="sn">03</div><div class="st">SAP TRM</div><div class="sd">The deal is created in SAP TRM straight through, validated on the way in.</div></div>
      </div>
    </div>
  </div>
  <div class="cols2">
    <div>
      <div class="band-lab">Why it matters</div>
      <p class="p">Treasury desks still re-key trades from the venue into SAP TRM by hand: slow, a control risk, and it breaks the moment a venue changes a field.</p>
    </div>
    <div>
      <div class="band-lab">What it delivers</div>
      {dots(["Captured at the venue and created in SAP TRM straight through, validated on the way in.",
             "Venue and TMS agnostic, so a new venue is a configuration change, not a rebuild."])}
    </div>
  </div>
  {dark_band("Built <span>in</span>", [
      "Four-eye approval and segregation of duties, as standard",
      "No ABAP and no per-venue interface to maintain",
      "Straight-through capture, so the manual re-key is gone"], mark="+")}
</main>'''


def body_remittance():
    return f'''<main>
  <div class="hero">
    <div>
      <div class="eyebrow">Remittance processing</div>
      <h1>Remittance<br>Advice Gate</h1>
      <p class="promise">AI reads the remittance and posts it. No one retypes anything.</p>
    </div>
    <div class="panel">
      <div class="vlab">Unstructured in &middot; posted out</div>
      <div class="rflow">
        <div class="rrow"><span class="dpill">Email body</span><span class="dpill">PDF attachment</span><span class="dpill">Scanned advice</span></div>
        <div class="rside">Unstructured emails and attachments</div>
        <div class="stem"></div>
        <div class="dai">AI reads &middot; structures &middot; matches</div>
        <div class="stem"></div>
        <div class="sapnode"><img src="data:image/png;base64,{LOGOS['sap']}" alt="SAP"><b>SAP S/4HANA</b></div>
        <div class="vcap">Posted, matched, exceptions surfaced.</div>
      </div>
    </div>
  </div>
  <div class="cols2">
    <div>
      <div class="band-lab">How it works</div>
      <p class="p">An LLM reads the unstructured email or attachment, structures it, and posts to SAP S/4HANA. Matches happen on the way in, so clean items flow through and only exceptions surface.</p>
    </div>
    <div>
      <div class="band-lab">What it delivers</div>
      {dots(["Clean items post straight through, untouched by a person.",
             "Only genuine exceptions reach the team, with the source advice attached."])}
    </div>
  </div>
  <div class="dark darkfull"><p>Already in production: <b>one S/4HANA customer removed the manual step entirely.</b></p></div>
</main>'''


def body_bank_fee_portal():
    return f'''<main>
  <div class="hero">
    <div>
      <div class="eyebrow">Bank fee control</div>
      <h1>Bank Fee<br>Portal</h1>
      <p class="promise">Check every bank charge against what you actually agreed, line by line.</p>
      <p class="rename">Overcharges slip through because nobody reconciles fees against the agreement.</p>
    </div>
    <div class="panel">
      <div class="vlab">Charged vs agreed</div>
      <div class="fee">
        <div class="chart">
          <div class="cbar"><div class="col" style="height:52mm;background:linear-gradient(180deg,#cbd5e1,#94a3b8);"><div class="over"></div></div><div class="clab"><b>Charged</b>what the bank billed</div></div>
          <div class="cbar"><div class="col" style="height:31mm;background:var(--ac);"></div><div class="clab"><b>Agreed</b>what you negotiated</div></div>
        </div>
        <div class="ledger">
          <div class="lhead">Line by line</div>
          <div class="lrow"><span>Wire transfer fee</span><span class="ltag ok">matches</span></div>
          <div class="lrow"><span>FX conversion margin</span><span class="ltag flag">flagged</span></div>
          <div class="lrow"><span>Custody fee</span><span class="ltag ok">matches</span></div>
          <div class="lrow"><span>Cash management</span><span class="ltag ok">matches</span></div>
          <div class="lrow"><span>Payment processing</span><span class="ltag flag">flagged</span></div>
        </div>
      </div>
    </div>
  </div>
  <div>
    <div class="band-lab">How it works</div>
    <div class="steps">
      <div class="step"><div class="sn">1</div><div class="st">Load</div><div class="sd">Every bank statement and fee line, from every account.</div></div>
      <div class="step"><div class="sn">2</div><div class="st">Match</div><div class="sd">Each charge against your negotiated agreement.</div></div>
      <div class="step"><div class="sn">3</div><div class="st">Flag</div><div class="sd">Every variance, with a line-level trail behind it.</div></div>
    </div>
  </div>
  {dark_band("What it <span>recovers</span>", [
      "Overcharges that would otherwise be paid without a second look",
      "The audit trail behind every fee, in one place, not scattered across statements"], mark="+")}
</main>'''


def body_treasurycentral():
    import math
    nodes = ["Cash", "Investments", "Debt", "FX", "Market Data", "Governance"]
    cx, cy = 75.0, 37.0
    rx, ry = 56.0, 28.0
    core_r = 18.0
    node_html, spokes = "", ""
    for i, name in enumerate(nodes):
        ang = -90 + i * 60
        rad = math.radians(ang)
        x = cx + rx * math.cos(rad)
        y = cy + ry * math.sin(rad)
        spokes += (f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}" '
                   f'stroke="var(--ac)" stroke-width="0.5" stroke-opacity="0.35"/>')
        node_html += (f'<div class="rad-node" style="left:{x / 150 * 100:.1f}%;top:{y / 74 * 100:.1f}%;">{name}</div>')
    svg = f'<svg viewBox="0 0 150 74" preserveAspectRatio="none" fill="none">{spokes}</svg>'
    return f'''<main>
  <div class="hero stack">
    <div class="eyebrow">The treasury cockpit</div>
    <h1>Treasury<span class="ac">Central</span></h1>
    <p class="promise">Cash, investments, debt, FX and market data in one screen, on your SAP data.</p>
  </div>
  <div class="panel">
    <div class="vlab">One cockpit &middot; six domains</div>
    <div class="radial">
      {svg}
      <div class="rad-core"><div class="c1">Treasury<span class="ac">Central</span></div><div class="c2">the cockpit</div></div>
      {node_html}
    </div>
  </div>
  <div class="cols2">
    <div>
      <div class="band-lab">One place to act</div>
      <p class="p">See the position and act on it in one screen, across all six treasury domains. Governance is built in, not bolted on afterwards.</p>
    </div>
    <div>
      <div class="band-lab">What it delivers</div>
      {dots(["No separate data store to reconcile; it works on the SAP data you already trust.",
             "Every move logged, every action inside your controls."])}
    </div>
  </div>
</main>'''


def body_onepilot():
    pillars = "".join(f'<div class="pil">{p}</div>'
                      for p in ["Market Data Hub", "Smart Trading", "Remittance Gate", "Bank Fee Portal"])
    return f'''<main>
  <div class="hero stack">
    <div class="eyebrow">The AI operating layer</div>
    <h1>One<span class="ac">Pilot</span></h1>
    <p class="promise">The governed AI layer that runs your treasury apps. In production now.</p>
  </div>
  <div class="arch">
    <div class="arch-top">One<span class="ac">Pilot</span><span class="lab">the governed AI layer</span></div>
    <div class="arch-conn"></div>
    <div class="arch-pillars">{pillars}</div>
    <div class="arch-base">out to <b>SAP</b> and non-SAP, bi-directional, across your landscape</div>
  </div>
  <div class="cols2">
    <div>
      <div class="band-lab">What it does</div>
      {dots(["It asks, automates and acts across the applications, always inside your controls.",
             "Build your own apps and automations without writing a line of code."])}
    </div>
    <div>
      <div class="band-lab">Governed by design</div>
      {dots(["Anomaly detection, segregation of duties and four-eye approval come as standard.",
             "Run by exception; your team stays in command."])}
    </div>
  </div>
</main>'''


# Web-page layout (appended after BASE_CSS so it overrides the print A4 sizing).
# The PDF (page()) stays a fixed A4 sheet; the native page served on
# resources.brisken.com is a full-bleed, responsive product page that fills the
# viewport and carries more content (how-it-works, delivers, FAQ, integrations,
# production proof) rather than a scaled A4 sheet floating in a grey stage.
# The atomic brand visuals (.funnel/.radial/.arch/.fee/.rflow/.dark/.steps/.dots)
# are reused from BASE_CSS so the web page and the PDF share the same visual DNA.
WEB_CSS = r"""
html{width:auto;height:auto;scroll-behavior:smooth;}
body{width:auto;height:auto;min-height:100vh;background:#f4f7fb;color:#334155;
  font-family:'IBM Plex Sans',sans-serif;-webkit-font-smoothing:antialiased;}
.wnav{position:sticky;top:0;z-index:40;display:flex;justify-content:space-between;align-items:center;
  gap:16px;padding:11px 26px;background:rgba(255,255,255,.92);border-bottom:1px solid #e6ebf2;}
.wnav .nl{display:flex;align-items:center;gap:11px;min-width:0;}
.wnav .nl .nlogo{height:22px;display:block;}
.wnav .nl .sep{color:#cbd5e1;}
.wnav .nl .plabel{font-family:'Space Grotesk';font-weight:600;font-size:14px;color:#475569;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.wnav .nr{display:flex;align-items:center;gap:14px;flex:0 0 auto;}
.wnav a{text-decoration:none;font-size:13.5px;font-weight:600;}
.wnav .nback{color:#64748b;}
.wnav .ndl{background:var(--ac);color:#fff;padding:8px 16px;border-radius:99px;}
.inner{max-width:1160px;margin:0 auto;padding:0 26px;}

/* hero fills the first screen */
.whero{position:relative;overflow:hidden;border-bottom:1px solid #e6ebf2;
  background:radial-gradient(1100px 480px at 82% -12%,var(--glow),transparent 60%),linear-gradient(180deg,#ffffff,#f4f7fb);}
.whero::before{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--ac),var(--ac2));}
.whero .inner{display:grid;grid-template-columns:1.04fr .96fr;gap:52px;align-items:center;
  padding-top:56px;padding-bottom:64px;}
.weyebrow{font-family:'Space Grotesk';font-size:13px;font-weight:600;letter-spacing:.22em;text-transform:uppercase;color:var(--ac);margin-bottom:14px;}
.whero h1{font-family:'Space Grotesk';font-size:52px;line-height:1.03;letter-spacing:-1.2px;font-weight:700;color:#0f172a;margin:0 0 18px;}
.whero h1 .ac{color:var(--ac);}
.wpromise{font-size:22px;line-height:1.5;color:#475569;max-width:40ch;}
.wrename{font-size:14px;color:#94a3b8;margin-top:12px;}
.wpoints{list-style:none;margin:28px 0 0;padding:0;display:flex;flex-direction:column;gap:14px;}
.wpoints li{position:relative;padding-left:26px;font-size:16.5px;line-height:1.55;color:#334155;}
.wpoints li::before{content:"";position:absolute;left:0;top:7px;width:9px;height:9px;background:var(--ac);border-radius:2px;transform:rotate(45deg);}
.wcta{display:flex;flex-wrap:wrap;gap:12px;margin-top:32px;}
.wbtn{display:inline-block;text-decoration:none;font-weight:600;font-size:14px;border-radius:99px;padding:12px 22px;transition:transform .15s ease,box-shadow .15s ease;}
.wbtn.primary{background:var(--ac);color:#fff;box-shadow:0 6px 18px var(--glow);}
.wbtn.ghost{background:#fff;color:#0f172a;border:1px solid #e6ebf2;}
.wbtn:hover{transform:translateY(-2px);}
.wvisual{background:#fff;border:1px solid #e6ebf2;border-radius:18px;padding:26px;box-shadow:0 16px 44px rgba(15,23,42,.09);}
.wvisual.bare{background:none;border:none;padding:0;box-shadow:none;}
.wvlab{font-family:'Space Grotesk';font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#64748b;text-align:center;margin-bottom:18px;}

/* content bands */
.wband{border-bottom:1px solid #eef2f7;padding:58px 0;}
.wband.alt{background:#ffffff;}
.wlab{font-family:'Space Grotesk';font-size:12.5px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--ac);margin-bottom:10px;}
.wh2{font-family:'Space Grotesk';font-size:28px;font-weight:700;color:#0f172a;letter-spacing:-.4px;margin-bottom:8px;}
.wlede{font-size:17.5px;line-height:1.7;color:#475569;max-width:74ch;margin-bottom:26px;}
.wband .steps{margin-top:6px;}
.wband .steps .st{font-size:16.5px;}
.wband .steps .sd{font-size:14.5px;line-height:1.6;}
.wband .dark{margin-top:6px;}
.wband .dark .ritem{font-size:15.5px;}
.wcols2{display:grid;grid-template-columns:1fr 1fr;gap:44px;margin-top:6px;}
.wcols2 .band-lab{font-family:'Space Grotesk';font-size:12.5px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--ac);margin-bottom:10px;}
.wcols2 .p{font-size:16.5px;line-height:1.65;color:#475569;}
.wband .dots li{font-size:15.5px;line-height:1.6;}

/* cards (capabilities / governance / proof) */
.wcards{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:6px;}
.wcard{background:#fff;border:1px solid #e6ebf2;border-radius:14px;padding:26px;border-top:3px solid var(--ac);box-shadow:0 1px 2px rgba(15,23,42,.04);}
.wcard .ct{font-family:'Space Grotesk';font-size:17.5px;font-weight:600;color:#0f172a;margin-bottom:9px;}
.wcard .cd{font-size:15.5px;line-height:1.6;color:#64748b;}
.wcard .cs{font-family:'Space Grotesk';font-size:12px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--ac);margin-bottom:12px;display:block;}

/* faq */
.wfaq{margin-top:6px;}
.wfaq details{border-top:1px solid #e6ebf2;padding:18px 2px;}
.wfaq details:last-child{border-bottom:1px solid #e6ebf2;}
.wfaq summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:18px;
  font-family:'Space Grotesk';font-weight:600;font-size:18px;color:#0f172a;}
.wfaq summary::-webkit-details-marker{display:none;}
.wfaq summary::after{content:"+";color:var(--ac);font-size:24px;line-height:1;font-weight:700;flex:0 0 auto;transition:transform .18s ease;}
.wfaq details[open] summary::after{transform:rotate(45deg);}
.wfaq p{margin-top:13px;font-size:16.5px;line-height:1.72;color:#475569;max-width:90ch;}

/* works-with chips */
.wchips{display:flex;flex-wrap:wrap;gap:12px;margin-top:6px;}
.wchip{background:#fff;border:1px solid #e6ebf2;border-radius:10px;padding:12px 18px;font-size:15px;font-weight:600;
  color:#334155;box-shadow:0 1px 2px rgba(15,23,42,.04);display:flex;align-items:center;gap:9px;}
.wchip img{height:19px;width:auto;display:block;}
.wchip .arrow{color:#cbd5e1;font-weight:700;margin:0 2px;}

/* accent callout */
.wcallout{background:var(--glow);border-left:4px solid var(--ac);border-radius:0 12px 12px 0;padding:22px 26px;margin-top:6px;}
.wcallout .ct{font-family:'Space Grotesk';font-size:20px;font-weight:700;color:#0f172a;letter-spacing:-.2px;margin-bottom:8px;}
.wcallout p{font-size:17px;line-height:1.65;color:#475569;max-width:84ch;}

/* horizontal process flow (wraps) */
.wflow{display:flex;flex-wrap:wrap;align-items:center;gap:9px;margin-top:6px;}
.wflow .fstep{background:#fff;border:1px solid #e6ebf2;border-radius:10px;padding:11px 15px;font-size:13.5px;font-weight:600;color:#334155;box-shadow:0 1px 2px rgba(15,23,42,.04);}
.wflow .fnum{color:var(--ac);font-family:'Space Grotesk';font-weight:700;margin-right:8px;}
.wflow .farrow{color:#cbd5e1;font-weight:700;}

/* two-column dots (delivers) */
.wdots2{display:grid;grid-template-columns:1fr 1fr;gap:16px 44px;margin-top:6px;}
.wdots2 .d{position:relative;padding-left:24px;font-size:16.5px;line-height:1.6;color:#334155;}
.wdots2 .d::before{content:"";position:absolute;left:0;top:7px;width:8px;height:8px;background:var(--ac);border-radius:2px;transform:rotate(45deg);}
@media(max-width:900px){.wdots2{grid-template-columns:1fr;}}

/* stat tiles (market-research benchmark) */
.wstats{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:6px;}
.wstat{background:#fff;border:1px solid #e6ebf2;border-radius:14px;padding:26px;box-shadow:0 1px 2px rgba(15,23,42,.04);border-top:3px solid var(--ac);}
.wstat .n{font-family:'Space Grotesk';font-size:46px;font-weight:700;color:var(--ac);letter-spacing:-1.5px;line-height:1;}
.wstat .l{font-size:15px;line-height:1.55;color:#475569;margin-top:13px;}
.wstat-src{font-size:13.5px;color:#94a3b8;margin-top:18px;line-height:1.5;}
@media(max-width:900px){.wstats{grid-template-columns:1fr;}}

/* comparison table */
.wtable-wrap{overflow-x:auto;margin-top:6px;border:1px solid #e6ebf2;border-radius:14px;}
.wtable{width:100%;border-collapse:collapse;font-size:15px;min-width:660px;}
.wtable th,.wtable td{text-align:left;padding:15px 18px;border-bottom:1px solid #eef2f7;vertical-align:top;line-height:1.5;}
.wtable tr:last-child th,.wtable tr:last-child td{border-bottom:none;}
.wtable thead th{background:#f6f9fc;font-family:'Space Grotesk';font-weight:600;font-size:14px;color:#0f172a;white-space:nowrap;}
.wtable thead th:first-child{color:#64748b;}
.wtable tbody th{font-weight:600;color:#0f172a;background:#fcfdfe;font-size:14.5px;}
.wtable td{color:#475569;}
.wtable td.hl{color:#0f172a;font-weight:500;background:var(--glow);}
.wtable-note{font-size:14px;color:#94a3b8;margin-top:14px;line-height:1.55;}

/* proof strip + closing CTA + footer */
.wproof{padding:44px 0;text-align:center;}
.wproof .proof{margin-top:0;}
.wcta-band{background:#0f172a;color:#e2e8f0;padding:56px 0;text-align:center;}
.wcta-band h2{font-family:'Space Grotesk';color:#fff;font-size:26px;letter-spacing:-.3px;margin-bottom:10px;}
.wcta-band p{color:#94a3b8;font-size:16px;margin:0 auto 26px;max-width:52ch;}
.wcta-band .wbtn.ghost{background:transparent;color:#fff;border-color:rgba(148,163,184,.5);}
.wfoot{padding:26px;text-align:center;font-size:13px;color:#94a3b8;background:#f4f7fb;line-height:1.7;}
.wfoot a{color:var(--ac);text-decoration:none;font-weight:600;}

@media(max-width:900px){
  .whero .inner{grid-template-columns:1fr;gap:34px;}
  .whero h1{font-size:40px;}
  .wcards{grid-template-columns:1fr;}
  .wcols2{grid-template-columns:1fr;gap:26px;}
  .wnav .nback{display:none;}
}

/* print: the downloadable PDF is a render of this same page, identical content */
@page{size:A4;margin:12mm 13mm;}
@media print{
  *{-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important;}
  html,body{background:#fff !important;}
  .wnav,.wcta-band{display:none !important;}
  .inner{max-width:none !important;padding:0 !important;}
  section,.wband,.whero,.wproof{border-bottom:none !important;}
  .whero{background:none !important;}
  .whero::before{display:none;}
  .whero .inner{grid-template-columns:1fr !important;gap:20px !important;padding:0 0 8mm !important;break-after:avoid;}
  .whero h1{font-size:30px !important;}
  .wpromise{font-size:16px !important;}
  .wvisual{box-shadow:none !important;}
  .wband{padding:7mm 0 5mm !important;break-inside:avoid;}
  .wband.alt{background:#fff !important;}
  .wh2{font-size:19px !important;}
  .wlede{font-size:13px !important;max-width:none !important;}
  .wcard,.wstat,.wcallout,.dark,.wfaq details,.wtable tr,.wchip,.step{break-inside:avoid;}
  .wtable-wrap{overflow:visible !important;}
  .wtable{min-width:0 !important;font-size:11px !important;}
  .wtable th,.wtable td{padding:8px 10px !important;}
  .wstat .n{font-size:34px !important;}
  .wfaq p{font-size:12.5px !important;max-width:none !important;}
  .wfaq details{padding:12px 0 !important;}
  .wcard .cd{font-size:12px !important;}
  .wproof{padding:6mm 0 !important;}
  .wfoot{background:#fff !important;padding:6mm 0 0 !important;}
  a{color:inherit !important;}
}
"""

# Extra CSS for the full-deck pages: the same nav/hero/band system as the
# one-pagers, plus a stacked-slide hero visual and a large embedded deck viewer.
DECK_CSS = r"""
/* hero visual: a reliable stack of slide cards (no live-PDF dependency) */
.deckcard{background:#fff;overflow:hidden;}
.deckstack{position:relative;height:250px;margin-top:4px;}
.deckstack .sl{position:absolute;left:0;right:0;margin:0 auto;top:11%;width:66%;height:78%;border-radius:12px;
  background:#fff;border:1px solid #e6ebf2;box-shadow:0 12px 34px rgba(15,23,42,.10);}
.deckstack .s3{transform:translate(30px,15px) rotate(4deg);opacity:.42;}
.deckstack .s2{transform:translate(15px,8px) rotate(2deg);opacity:.7;}
.deckstack .s1{border-top:4px solid var(--ac);display:flex;flex-direction:column;justify-content:center;
  gap:14px;padding:26px 30px;background:linear-gradient(162deg,#fff,#f8fafc);}
.deckstack .slrow{height:13px;border-radius:6px;background:linear-gradient(90deg,var(--ac),var(--ac2));opacity:.92;}
.deckstack .slrow.w70{width:70%;}
.deckstack .slrow.w45{width:45%;background:#e2e8f0;}

/* full embedded deck viewer */
.deckframe{margin-top:6px;border:1px solid #e6ebf2;border-radius:16px;overflow:hidden;
  box-shadow:0 18px 50px rgba(15,23,42,.12);background:#334155;}
.deckview{display:block;width:100%;height:80vh;min-height:520px;border:0;background:#334155;}
.deck-fallback{display:none;}
@media(max-width:640px){
  .deckview{display:none;}
  .deck-fallback{display:block;margin-top:6px;padding:34px 22px;text-align:center;color:#475569;
    font-size:15px;line-height:1.7;border:1px dashed #cbd5e1;border-radius:14px;}
  .deck-fallback a{color:var(--ac);font-weight:600;}
}
@media print{.deckframe,.deckview{display:none !important;}}
"""

# --------------------------------------------------------------------------- #
# Web-page building blocks. All copy below traces to the internal sourced set
# (the qa-clusters, the onepilot platform/prototype pages, and the approved
# one-pager copy in this file). No new claims; Bank Fee and TreasuryCentral keep
# the restraint of the shipped one-pagers (no unbacked "live customer" line).
LAST_UPDATED = "2026-07-14"


def _cta_buttons(p, hero=True):
    pdf = f'/{p["short"]}.pdf'
    deck = p.get("deck")
    if deck:
        primary = f'<a class="wbtn primary" href="{deck}">See the full deck &rarr;</a>'
        second = f'<a class="wbtn ghost" href="{pdf}" download>Download as PDF</a>'
    else:
        primary = f'<a class="wbtn primary" href="{pdf}" download>Download as PDF</a>'
        second = '<a class="wbtn ghost" href="/">All resources</a>'
    return primary + second


def web_hero(p, eyebrow, h1, promise, points, visual, rename="", bare=False):
    rn = f'<p class="wrename">{rename}</p>' if rename else ""
    pts = "".join(f"<li>{x}</li>" for x in points)
    vcls = "wvisual bare" if bare else "wvisual"
    return f'''<section class="whero"><div class="inner">
  <div class="hcopy">
    <div class="weyebrow">{eyebrow}</div>
    <h1>{h1}</h1>
    <p class="wpromise">{promise}</p>
    {rn}
    <ul class="wpoints">{pts}</ul>
    <div class="wcta">{_cta_buttons(p)}</div>
  </div>
  <div class="{vcls}">{visual}</div>
</div></section>'''


def web_band(label, inner, h2="", lede="", alt=False):
    cls = "wband alt" if alt else "wband"
    h2h = f'<h2 class="wh2">{h2}</h2>' if h2 else ""
    ledeh = f'<p class="wlede">{lede}</p>' if lede else ""
    return f'<section class="{cls}"><div class="inner"><div class="wlab">{label}</div>{h2h}{ledeh}{inner}</div></section>'


def web_steps(steps, cols=3):
    body = "".join(f'<div class="step"><div class="sn">{n}</div><div class="st">{t}</div><div class="sd">{d}</div></div>'
                   for n, t, d in steps)
    return f'<div class="steps" style="grid-template-columns:repeat({cols},1fr);">{body}</div>'


def web_cards(cards):
    out = []
    for s, t, d in cards:
        cs = f'<span class="cs">{s}</span>' if s else ""
        out.append(f'<div class="wcard">{cs}<div class="ct">{t}</div><div class="cd">{d}</div></div>')
    return f'<div class="wcards">{"".join(out)}</div>'


def web_cols2(left, right):
    return f'<div class="wcols2">{left}{right}</div>'


def web_faq(items):
    # open by default: the answers are informative text that should fill the
    # page, not hide behind a collapsed row. The toggle still collapses them.
    body = "".join(f'<details open><summary>{q}</summary><p>{a}</p></details>' for q, a in items)
    return f'<div class="wfaq">{body}</div>'


def web_callout(title, body):
    return f'<div class="wcallout"><div class="ct">{title}</div><p>{body}</p></div>'


def web_flow(items):
    parts = []
    for i, it in enumerate(items):
        if i:
            parts.append('<span class="farrow">&rarr;</span>')
        parts.append(f'<span class="fstep"><span class="fnum">{i + 1}</span>{it}</span>')
    return f'<div class="wflow">{"".join(parts)}</div>'


def web_dots2(points):
    inner = "".join(f'<div class="d">{p}</div>' for p in points)
    return f'<div class="wdots2">{inner}</div>'


def web_stats(items, source):
    tiles = "".join(f'<div class="wstat"><div class="n">{n}</div><div class="l">{lab}</div></div>' for n, lab in items)
    return f'<div class="wstats">{tiles}</div><p class="wstat-src">{source}</p>'


def web_table(headers, rows, note=""):
    """headers: [dimension_label, our_option, ...others]. rows: [(dimension, [cells])].
    The first data cell (our option) is highlighted."""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = ""
    for dim, cells in rows:
        tds = "".join((f'<td class="hl">{c}</td>' if i == 0 else f'<td>{c}</td>') for i, c in enumerate(cells))
        body += f"<tr><th>{dim}</th>{tds}</tr>"
    note_h = f'<p class="wtable-note">{note}</p>' if note else ""
    return f'<div class="wtable-wrap"><table class="wtable"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>{note_h}'


def web_chips(items):
    """items: list of (label, logo_key_or_None). A None label renders an arrow."""
    parts = []
    for label, logo in items:
        if label == "&rarr;":
            parts.append('<span class="arrow">&rarr;</span>')
            continue
        img = f'<img src="data:image/png;base64,{LOGOS[logo]}" alt="">' if logo else ""
        parts.append(f'<span class="wchip">{img}{label}</span>')
    return f'<div class="wchips">{"".join(parts)}</div>'


def web_cta_band(p):
    deck = p.get("deck")
    btns = []
    if deck:
        btns.append(f'<a class="wbtn primary" href="{deck}">See the full deck &rarr;</a>')
    btns.append(f'<a class="wbtn primary" href="/{p["short"]}.pdf" download>Download as PDF</a>' if not deck
                else f'<a class="wbtn ghost" href="/{p["short"]}.pdf" download>Download as PDF</a>')
    btns.append('<a class="wbtn ghost" href="https://www.brisken.com">www.brisken.com</a>')
    return (f'<section class="wcta-band"><div class="inner"><h2>{p.get("cta_h", "Want the full picture?")}</h2>'
            f'<p>{p.get("cta_p", "The one-pager is the summary. The full deck and the team go deeper.")}</p>'
            f'<div class="wcta" style="justify-content:center;">{"".join(btns)}</div></div></section>')


def web_footer():
    return (f'<footer class="wfoot"><b>Brisken</b>, an SAP Co-Innovation Partner &middot; '
            f'<a href="https://www.brisken.com">www.brisken.com</a><br>Last updated: {LAST_UPDATED}</footer>')


# ---- per-product visuals (reuse the A4 brand widgets, laid out for a panel) --
def vis_mdh():
    return (f'<div class="wvlab">Every provider &middot; one feed</div>'
            f'<div class="logos">{lchip("bloomberg")}{lchip("lseg")}{lchip("ice")}{lchip("cme")}</div>'
            '<div class="funnel"><div class="stem"></div><div class="feed">one governed feed</div>'
            '<div class="stem"></div><div class="outs"><span class="out">SAP</span><span class="out">non-SAP</span></div></div>'
            '<div class="vcap">Both directions, no code. Central banks included.</div>')


def vis_smart_trading():
    return ('<div class="wvlab">Venue to SAP, straight through</div>'
            '<div class="steps" style="grid-template-columns:1fr;gap:16px;">'
            '<div class="step"><div class="sn">01</div><div class="st">Decide &amp; approve</div><div class="sd">Decision, approval and execution, with the controls applied up front.</div></div>'
            '<div class="step"><div class="sn">02</div><div class="st">Execution venues</div><div class="sd">Captured at the venue: Bloomberg FX GO, FXall, 360T, BidFX and more.</div></div>'
            '<div class="step"><div class="sn">03</div><div class="st">SAP TRM</div><div class="sd">The deal is created in SAP TRM straight through, validated on the way in.</div></div>'
            '</div>')


def vis_remittance():
    return ('<div class="wvlab">Unstructured in &middot; posted out</div>'
            '<div class="rflow">'
            '<div class="rrow"><span class="dpill">Email body</span><span class="dpill">PDF attachment</span><span class="dpill">Scanned advice</span></div>'
            '<div class="rside">Unstructured emails and attachments</div>'
            '<div class="stem"></div><div class="dai">AI reads &middot; structures &middot; matches</div><div class="stem"></div>'
            f'<div class="sapnode"><img src="data:image/png;base64,{LOGOS["sap"]}" alt="SAP"><b>SAP S/4HANA</b></div>'
            '<div class="vcap">Posted, matched, exceptions surfaced.</div></div>')


def vis_bank_fee():
    # Shorter bars, and a chart box tall enough to contain the bar PLUS its
    # caption (the .cbar is bar + caption; with align-items:flex-end a caption
    # that overflows the box pushes the bar top up into the label). Extra height
    # keeps clear air between the "Charged vs agreed" label and the bars.
    return ('<div class="wvlab">Charged vs agreed</div>'
            '<div class="chart" style="height:60mm;">'
            '<div class="cbar"><div class="col" style="height:40mm;background:linear-gradient(180deg,#cbd5e1,#94a3b8);"><div class="over"></div></div><div class="clab"><b>Charged</b>what the bank billed</div></div>'
            '<div class="cbar"><div class="col" style="height:24mm;background:var(--ac);"></div><div class="clab"><b>Agreed</b>what you negotiated</div></div>'
            '</div>'
            '<div class="ledger" style="margin-top:16px;"><div class="lhead">Line by line</div>'
            '<div class="lrow"><span>Wire transfer fee</span><span class="ltag ok">matches</span></div>'
            '<div class="lrow"><span>FX conversion margin</span><span class="ltag flag">flagged</span></div>'
            '<div class="lrow"><span>Custody fee</span><span class="ltag ok">matches</span></div>'
            '<div class="lrow"><span>Cash management</span><span class="ltag ok">matches</span></div>'
            '<div class="lrow"><span>Payment processing</span><span class="ltag flag">flagged</span></div></div>')


def vis_treasurycentral():
    import math
    nodes = ["Cash", "Investments", "Debt", "FX", "Market Data", "Governance"]
    cx, cy, rx, ry = 75.0, 37.0, 56.0, 28.0
    node_html, spokes = "", ""
    for i, name in enumerate(nodes):
        rad = math.radians(-90 + i * 60)
        x = cx + rx * math.cos(rad)
        y = cy + ry * math.sin(rad)
        spokes += f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="var(--ac)" stroke-width="0.5" stroke-opacity="0.35"/>'
        node_html += f'<div class="rad-node" style="left:{x / 150 * 100:.1f}%;top:{y / 74 * 100:.1f}%;">{name}</div>'
    svg = f'<svg viewBox="0 0 150 74" preserveAspectRatio="none" fill="none">{spokes}</svg>'
    return (f'<div class="wvlab">One cockpit &middot; six domains</div>'
            f'<div class="radial">{svg}<div class="rad-core"><div class="c1">Treasury<span class="ac">Central</span></div>'
            f'<div class="c2">the cockpit</div></div>{node_html}</div>')


def vis_onepilot():
    pillars = "".join(f'<div class="pil">{x}</div>' for x in
                      ["Market Data Hub", "Smart Trading", "Remittance Gate", "Bank Fee Portal"])
    return ('<div class="arch">'
            '<div class="arch-top">One<span class="ac">Pilot</span><span class="lab">the governed AI layer</span></div>'
            '<div class="arch-conn"></div>'
            f'<div class="arch-pillars">{pillars}</div>'
            '<div class="arch-base">out to <b>SAP</b> and non-SAP, bi-directional, across your landscape</div></div>')


# ---- per-product web page bodies ------------------------------------------- #
def web_body_market_data_hub(p):
    return (
        web_hero(
            p, "Market data", 'Market <span class="ac">Data Hub</span>',
            "Every rate, curve and price through one managed feed. No hand-keyed uploads.",
            ["Bloomberg, Refinitiv (LSEG), ICE, CME, 360T, OANDA and central banks through one governed feed.",
             "Ingested once, normalized, then distributed to SAP and non-SAP, both directions, no code.",
             "Adding or switching a provider is a configuration change, not a new interface to build.",
             "One point of control for entitlements, usage, and the audit trail behind every rate."],
            vis_mdh())
        + web_band("The problem",
                   '<p class="wlede">Getting market data into SAP usually means a Datafeed RFC connection or a custom per-vendor script: one for Bloomberg, another for Refinitiv, another for 360T. Both need ABAP to set up and maintain, and both break the moment a provider changes a field. Rates, curves and prices for SAP TRM and Market Rates Management end up hand-keyed, or held together by scripts nobody owns, and the day a feed breaks is the day the close waits on it.</p>'
                   '<p class="wlede" style="margin-bottom:0;">The Market Data Hub replaces that with one managed feed. It ingests every provider once, normalizes the data, and distributes the same governed number into SAP TRM and Market Rates Management, with a full audit trail and exception alerts, no code and no per-vendor interface to keep alive.</p>',
                   h2="Market data into SAP, without the scripts that break")
        + web_band("The market", web_stats([
            ("71%", "of US SAP-treasury roles describe building or hand-running integrations into SAP, or manual data work (29 of 41)."),
            ("34%", "are tied to an active S/4HANA migration or SAP implementation, the moment feeds get re-plumbed (14 of 41)."),
            ("22%", "name a specific market-data or trading vendor whose feed has to reach SAP, and that is a floor (9 of 41)."),
        ], "Source: Brisken Shadow Integration Report, N=41 US SAP-treasury job ads, read 2026-06-17. These are market-research figures, not a Market Data Hub performance metric."),
            h2="Loading market data by hand is the default, not the exception", alt=True)
        + web_band("How it works", web_steps([
            ("1", "Ingest", "Every provider's rates, curves and prices arrive in their own formats: Bloomberg, Refinitiv, ICE, CME, 360T, OANDA, central banks and government agencies."),
            ("2", "Govern", "One managed feed validates and normalizes each source, and controls entitlements and usage in a single place, with the audit trail attached."),
            ("3", "Distribute", "The same number flows to SAP TRM, Market Rates Management and non-SAP targets, both directions, straight through, no ABAP."),
        ]), h2="One managed feed, from source to system",
            lede="The hub sits between every provider and every system that needs a rate. Ingest once, govern in one place, distribute everywhere, so the same governed figure reaches each consumer instead of arriving three different ways.")
        + web_band("Governed by the feed",
                   '<p class="wlede" style="margin-bottom:0;">Governance lives in the feed, not in each interface. Every source is validated and normalized on the way in, entitlements and usage are controlled from one place, and manage-by-exception alerts surface anything that looks wrong before it reaches a decision. Segregation of duties and a full audit trail sit on the feed itself, so control does not depend on whoever wrote the last script.</p>',
                   h2="Control lives in the feed, not in each interface", alt=True)
        + web_band("How it compares", web_table(
            ["", "Market Data Hub", "SAP-native Datafeed", "Custom script"],
            [("Setup", ["No-code configuration", "ABAP function lists and translation tables", "Bespoke code per provider"]),
             ("Add or swap a provider", ["Configuration change", "New function list and mapping", "New script"]),
             ("Multiple providers", ["One normalized pipe, many sources", "Configured per provider", "One interface per provider"]),
             ("Governance", ["Audit trail, segregation of duties, exception alerts built in", "Manual or custom", "None unless coded"]),
             ("Maintenance owner", ["Vendor-managed (SaaS)", "In-house ABAP", "Whoever wrote it"]),
             ("When a provider changes a field", ["Absorbed in configuration", "ABAP edit needed", "The script breaks"]),
             ("SAP-listed", ["Yes, on the SAP Store", "Native to SAP", "Not applicable"])],
            note="Honest comparison. The SAP-native Datafeed is a real, supported path; the point of a hub is the no-code, multi-provider, governed layer over it, not a claim that SAP cannot do this."),
            h2="The hub versus the two usual paths")
        + web_band("What it retires", dark_band("What it <span>retires</span>", [
            "Per-provider upload scripts, maintained by hand and understood by one person",
            "Rates re-keyed into spreadsheets before they ever reach SAP",
            "Point-to-point integrations that break when a feed changes a field",
            "ABAP upkeep for every new or changed provider"]), alt=True)
        + web_band("Works with", web_chips([
            ("", "bloomberg"), ("", "lseg"), ("", "ice"), ("", "cme"),
            ("&rarr;", None), ("SAP TRM", None), ("Market Rates Management", None), ("SAP ECC / S/4HANA", None), ("non-SAP", None)]),
            h2="Every provider in, SAP and non-SAP out",
            lede="Beyond the four shown above, the hub also handles Refinitiv (LSEG), 360T, OANDA, central banks and government agencies. Switching or adding a provider is a configuration change, not a new interface, so there is no per-vendor rebuild to maintain.")
        + web_band("Common questions", web_faq([
            ("How do I get Bloomberg market data into SAP TRM automatically?",
             "The SAP-native path is a Datafeed RFC connection with per-provider function lists and translation tables, or a per-security custom interface, both of which need ABAP upkeep and break when Bloomberg changes a field. A governed market-data hub ingests Bloomberg once, normalizes it, and distributes into SAP TRM with an audit trail and exception alerts, no code."),
            ("How do I load Refinitiv (LSEG) rates and curves into SAP S/4HANA treasury?",
             "Refinitiv (LSEG) rates and curves reach SAP S/4HANA treasury through the same governed hub that handles any provider: ingest the feed once, normalize it, distribute into Market Rates Management. Switching or adding a provider is a configuration change, not a new interface, so there is no per-vendor rebuild to maintain."),
            ("Can I automate FX rates and yield curves into SAP Market Rates Management without ABAP?",
             "Yes. SAP's native route uses a Datafeed RFC with function lists and translation tables, which needs ABAP to set up and maintain. A no-code market-data hub maps and schedules FX rates and yield curves into SAP Market Rates Management through configuration, so the treasury team owns the feed without writing or changing ABAP."),
            ("What is the alternative to a custom Bloomberg-to-SAP script that keeps breaking?",
             "A custom script breaks whenever the provider changes a field or the person who wrote it leaves. A managed market-data hub replaces it with a configured, monitored interface: provider changes are absorbed in configuration, the feed is governed with an audit trail and exception alerts, and nobody is babysitting a brittle script."),
            ("How do I feed OANDA or central-bank rates into SAP cash management?",
             "OANDA and central-bank rates feed into SAP cash management through the same hub as every other source. Multiple providers land in one normalized pipeline rather than separate point interfaces, so the rates that drive cash and liquidity views come from one governed feed with a single point of control."),
            ("How do I govern multiple market-data providers into SAP from one place?",
             "A market-data hub is the single point of control for every provider feeding SAP: Bloomberg, Refinitiv, OANDA, 360T, central banks. It validates, normalizes and distributes each feed, with an audit trail, segregation of duties, and manage-by-exception alerts. Governance is built into the feed, not bolted on per interface afterwards."),
            ("What is the best way to handle market-data integration during an S/4HANA migration?",
             "A migration forces every treasury data feed to be re-plumbed, which is when hand-built market-data interfaces are most expensive to rebuild. Moving the feeds onto a governed hub during the migration re-platforms them once onto a managed interface instead of re-coding each script. In a read of US SAP-treasury job ads, 34% sat inside an active migration."),
            ("Is there a no-code alternative to SAP TRM datafeed configuration?",
             "The SAP TRM Datafeed needs ABAP-side setup of function lists and translation tables per provider. The alternative is a no-code hub that handles ingest, mapping and distribution through configuration, aimed at treasury teams that do not have the ABAP capacity to build and maintain the datafeed themselves."),
        ]), alt=True)
        + web_band("Proof",
                   '<p class="wlede" style="margin:0;">The Market Data Hub is the flagship product, with its own overview deck, and is listed on the SAP Store. Brisken is an SAP Co-Innovation Partner, certified to ISO 27001 and SOC 1 Type II, and delivers the hub as a managed product on your SAP landscape, with data partners including Bloomberg, Refinitiv, CME Group, 360T, Deutsche Boerse and OANDA.</p>')
    )


def web_body_smart_trading(p):
    return (
        web_hero(
            p, "Trade capture", 'Brisken <span class="ac">Smart Trading</span>',
            "The trade lifecycle from venue to booked deal, straight through. No re-keying.",
            ["Captured at the execution venue and created in SAP TRM straight through, validated on the way in.",
             "Venue and TMS agnostic, so a new venue is a configuration change, not a rebuild.",
             "Four-eye approval and segregation of duties, built in as standard.",
             "Brings exposure, market data and execution onto one surface, logged back into SAP."],
            vis_smart_trading(),
            rename="Formerly Trade Automation / TraderPlus. Now Brisken Smart Trading (BST).")
        + web_band("The problem",
                   '<p class="wlede">Treasury desks still re-key trades from the venue into SAP TRM by hand. Someone executes on the trading platform, switches tabs to check exposure, then types the deal back into SAP. It is slow, it is a control risk, and it breaks the moment a venue changes a field.</p>'
                   '<p class="wlede" style="margin-bottom:0;">Brisken Smart Trading captures the trade at the execution venue and creates the deal in SAP TRM straight through, validated on the way in. It brings exposure, market data and execution onto one surface and logs every action back into SAP under four-eye control. The manual middle is gone.</p>',
                   h2="From the trade decision to the booked deal, straight through")
        + web_band("The full trade lifecycle",
                   web_flow(["Decision", "Request", "Approval", "Execution", "Mapping", "Fulfillment", "Deal creation"])
                   + '<p class="wlede" style="margin-top:22px;margin-bottom:0;">Decision, request and approval happen with the controls applied up front. The trade is captured at the execution venue and mapped into SAP, then created in SAP TRM straight through, validated on the way in. One end-to-end lifecycle, trading-venue and TMS agnostic, so trades flow into SAP Treasury and Risk Management as governed deals, reconciled to source.</p>',
                   h2="Decision to booked deal, in one flow", alt=True)
        + web_band("Built in", dark_band("Built <span>in</span>", [
            "Four-eye approval and segregation of duties, as standard",
            "No ABAP and no per-venue interface to maintain",
            "Straight-through capture, so the manual re-key is gone"], mark="+"))
        + web_band("Works with", web_chips([
            ("FXall", None), ("Bloomberg FX GO", None), ("360T", None), ("BidFX", None), ("Citi Pulse", None),
            ("&rarr;", None), ("SAP TRM", None)]),
            h2="Any venue in, SAP TRM out",
            lede="Captured at Bloomberg FX GO, FXall, 360T, BidFX, Citi Pulse and more, then created in SAP TRM. It is trading-venue and TMS agnostic, so a new venue is a configuration change, and the deal flows into SAP Treasury and Risk Management reconciled to source.", alt=True)
        + web_band("Common questions", web_faq([
            ("What is Brisken Smart Trading (BST)?",
             "BST is the FX and trade-execution application in the family, and the live flagship. It brings exposure, market data and execution onto one surface and logs every action back into SAP under four-eye control."),
            ("How is a trade captured without re-keying it into SAP?",
             "The deal is captured at the execution venue and created in SAP TRM straight through, validated on the way in. Because it is venue and TMS agnostic, adding a new venue is a configuration change rather than a rebuild."),
        ]))
        + web_band("Proof", '<p class="wlede" style="margin:0;">Listed on the SAP Store as Trade Automation, and the live flagship on SAP. Brisken is an SAP Co-Innovation Partner, certified to ISO 27001 and SOC 1 Type II.</p>', alt=True)
    )


def web_body_remittance(p):
    return (
        web_hero(
            p, "Remittance processing", 'Remittance <span class="ac">Advice Gate</span>',
            "AI reads the remittance and posts it. No one retypes anything.",
            ["An LLM reads the unstructured email or attachment, structures it, and posts to SAP S/4HANA.",
             "Clean items post straight through; only genuine exceptions reach the team, with the source advice attached.",
             "In production: a live agricultural-sector customer runs it on S/4HANA Private Cloud."],
            vis_remittance())
        + web_band("The problem",
                   '<p class="wlede">Remittance advice still lands as email and PDF that someone keys into SAP cash application by hand. They open the remittance, find the invoices it pays, work out the deductions, and type the match into SAP, one document at a time. Volume is capped by headcount, and month-end is where the backlog shows.</p>'
                   '<p class="wlede" style="margin-bottom:0;">The Remittance Advice Gate reads the unstructured input directly. An LLM extracts the payer, invoices, amounts and deductions, and posts structured data into SAP S/4HANA. Clean items flow through untouched; only genuine exceptions reach a person, with the source advice attached. The job shifts from retype-everything to review-the-exceptions.</p>',
                   h2="Reading remittance advice into SAP, without the retype")
        + web_band("How it works",
                   '<p class="wlede" style="margin-bottom:0;">An LLM reads the unstructured email or attachment, whether that is an email body, a PDF, a scanned document or a spreadsheet export, and structures it into the fields SAP needs: payer, invoice references, amounts and deductions. It posts to SAP S/4HANA cash application, matching on the way in, so clean items post straight through. A monitor lets the team correct and retrain it as new layouts appear, so coverage improves over time rather than needing a new template each time a bank changes its format.</p>',
                   h2="From unstructured advice to a posted match", alt=True)
        + web_band("How it compares", web_table(
            ["", "Remittance Advice Gate", "Manual cash application", "Rules / template OCR"],
            [("Reads unstructured email and PDF", ["AI extraction, no fixed template", "A person reads and keys", "Works only on known layouts"]),
             ("A new remittance format", ["Handled, the monitor retrains it", "Staff adapt by hand", "A new template rule is needed"]),
             ("Output into SAP", ["Structured, posted to S/4HANA", "Hand-keyed", "Structured, if the template matched"]),
             ("Effort per remittance", ["Review exceptions only", "Full retype each time", "Fix the unmatched ones"]),
             ("Live proof", ["ChatGPT-powered agricultural customer", "Not applicable", "Not applicable"])],
            note="Honest comparison. Manual cash application and template-based capture are both real, working approaches; the gate's difference is reading unstructured input directly and learning from corrections, not a claim that the alternatives do nothing."),
            h2="The gate versus the two usual paths")
        + web_band("What it delivers", web_cols2(
            '<div><div class="band-lab">Straight through</div>' + dots([
                "Clean items post straight through, untouched by a person.",
                "The team reviews exceptions instead of retyping every remittance by hand."]) + '</div>',
            '<div><div class="band-lab">Any input</div>' + dots([
                "Reads email bodies, PDF attachments, scanned documents and spreadsheet exports.",
                "Extracts payer, invoice references, amounts and deductions, no fixed template."]) + '</div>'), alt=True)
        + web_band("Works with", web_chips([
            ("Email", None), ("PDF", None), ("Scanned advice", None), ("CSV", None),
            ("&rarr;", None), ("SAP S/4HANA", None), ("Serrala", None), ("BPI", None), ("HighRadius", None)]),
            h2="Any remittance format in, SAP cash application out")
        + web_band("Common questions", web_faq([
            ("How do I automate unstructured remittance advice emails into SAP cash application?",
             "Remittance advice arrives as unstructured email and PDF, which staff retype into SAP cash application. An AI-powered remittance gate reads the unstructured input, identifies and structures the data (payer, invoices, amounts, deductions), and delivers it into SAP S/4HANA, with a monitor that trains it over time. The manual retype step is removed."),
            ("Can AI read remittance PDFs and post them to SAP S/4HANA?",
             "Yes. A remittance gate uses an LLM to read remittance PDFs, email bodies and attachments, extract the structured fields, and post them into SAP S/4HANA cash application. A live agricultural-sector customer runs this on a ChatGPT-powered deployment on S/4HANA Private Cloud."),
            ("How do I reduce manual cash-application matching in SAP?",
             "A remittance gate does the reading and structuring automatically and hands SAP the data already formatted for matching, so the team reviews exceptions instead of retyping every remittance by hand."),
            ("What remittance inputs can an AI gate read?",
             "Email bodies, PDF attachments, scanned documents and spreadsheet exports. It reads the unstructured input directly rather than relying on a fixed template, and a monitor lets the team correct and retrain it as new layouts appear."),
            ("Does it work with Serrala, BPI or HighRadius?",
             "The gate delivers structured remittance data into SAP S/4HANA, and can also target cash-application platforms such as Serrala, BPI or HighRadius. It sits upstream as the step that turns unstructured remittances into clean, structured input."),
        ]), alt=True)
        + web_band("In production",
                   '<p class="wlede" style="margin:0;">Already in production: a live agricultural-sector customer runs this on a ChatGPT-powered deployment on S/4HANA Private Cloud, with the stated goal of removing the human from the retype entirely.</p>')
    )


def web_body_bank_fee(p):
    return (
        web_hero(
            p, "Bank fee control", 'Bank <span class="ac">Fee Portal</span>',
            "Check every bank charge against what you actually agreed, line by line.",
            ["Loads every bank fee statement in any format: CAMT.086, TWIST BSB and proprietary.",
             "Matches each charge against your negotiated agreement and flags every variance.",
             "A line-level audit trail behind every fee, in one place, not scattered across statements.",
             "Sits in front of SAP's own bank-fee analysis, so every bank reaches the review."],
            vis_bank_fee())
        + web_band("The problem",
                   '<p class="wlede">Bank fee statements arrive in three shapes: the older TWIST BSB format, the ISO 20022 CAMT.086 that is replacing it, and each bank\'s own proprietary layout. SAP added native bank-fee analysis in S/4HANA 1809, but it expects clean CAMT.086 in. The statements that arrive in any other format never reach the analyzer, so the fees on them never get reviewed.</p>'
                   '<p class="wlede" style="margin-bottom:0;">Fee leakage is rarely a single dramatic overcharge; it is the slow drift between a contracted rate and what the bank actually applies, on exactly those statements nobody reviews. The Bank Fee Portal sits in front and accepts every format, normalizes it, and feeds the analysis, so the fee review covers every bank, not just the ones that happen to send clean files.</p>',
                   h2="Getting every bank's statement into the fee review")
        + web_band("How it works", web_steps([
            ("1", "Load", "Every bank statement and fee line, from every account, in any format: CAMT.086, TWIST BSB or proprietary."),
            ("2", "Match", "Each charge is compared against the fee you negotiated in the agreement."),
            ("3", "Flag", "Every variance is surfaced, with a line-level trail behind it."),
        ]), h2="Every statement in, every variance flagged",
            lede="The portal ingests the statements, enriches each fee line for cost analytics, and feeds SAP's analysis, so the comparison of charged against agreed can run on every account.", alt=True)
        + web_band("How it compares", web_table(
            ["", "Bank Fee Portal in front of SAP", "SAP-native analysis alone", "Manual / spreadsheet"],
            [("Input formats accepted", ["TWIST BSB, CAMT.086, proprietary, normalized in", "Clean CAMT.086", "Whatever a person can open"]),
             ("Off-format statements", ["Parsed and delivered into the analysis", "Stall outside the app", "Re-keyed by hand, if at all"]),
             ("Overcharge detection", ["Every bank reaches the comparison", "Only banks already on CAMT.086", "Spot-checks, not line by line"]),
             ("Effort per cycle", ["Ingest is configured once, runs on its own", "Manual conversion for off-format banks", "Hours of clerical work each run"]),
             ("Audit trail", ["Logged ingest, exception alerts", "Within the app for loaded data", "None beyond the spreadsheet"])],
            note="The portal sits in front of SAP's own bank-fee analysis; it does not replace it. SAP's native analysis is capable once the data is in; the portal's job is getting every bank's statement, in any format, into it."),
            h2="The portal versus the two usual paths")
        + web_band("What it recovers", dark_band("What it <span>recovers</span>", [
            "Overcharges that would otherwise be paid without a second look",
            "The audit trail behind every fee, in one place, not scattered across statements"], mark="+"), alt=True)
        + web_band("What it delivers", web_dots2([
            "Every fee line enriched for cost analytics and surfaced on a dashboard.",
            "Each charge matched against the negotiated agreement, with a line-level trail.",
            "Every variance flagged, so overcharges are seen before they are paid.",
            "One place for every account's fees, in every format, not scattered across statements."]))
        + web_band("Why format matters",
                   web_callout("Format coverage is overcharge coverage.",
                               "You cannot audit a fee statement you never managed to load. The bank that sends a proprietary file is the bank whose fees go unchecked, so getting that statement into the analysis is what makes the discrepancy visible. The portal sits in front and accepts every format, so no bank is left out of the review."), alt=True)
        + web_band("Built on the standard",
                   '<p class="wlede" style="margin-bottom:0;">CAMT.086 is the ISO 20022 bank-fee-statement format that replaces the older TWIST BSB. SAP added native bank-fee analysis in S/4HANA release 1809, delivered as a Fiori app that compares charged fees against expected ones, but it reads clean CAMT.086 only. Banks have not standardized on it; many still send TWIST BSB or a proprietary layout, and those are exactly the statements the portal exists to normalize and bring in.</p>',
                   h2="Where SAP's native analysis stops")
        + web_band("Works with", web_chips([
            ("CAMT.086 (ISO 20022)", None), ("TWIST BSB", None), ("Proprietary formats", None),
            ("&rarr;", None), ("SAP bank-fee analysis", None), ("Any Bank Fee Analyzer", None)]),
            h2="Any statement format in, one analysis out", alt=True)
        + web_band("Common questions", web_faq([
            ("How do I automate CAMT.086 bank fee statement analysis in SAP?",
             "CAMT.086 is the ISO 20022 bank-fee-statement format that replaces TWIST BSB. SAP added native bank-fee analysis in S/4HANA 1809 via a Fiori app, but it expects clean CAMT.086 in; banks still send proprietary and TWIST formats. A bank-fee portal ingests any format, enriches for analytics, and distributes to the analyzer, so the fee review is not gated on format."),
            ("How do I detect bank overcharges or fee leakage with SAP treasury?",
             "Bank fee statements are rarely audited line by line, so contracted rates and applied charges drift apart unnoticed. Loading the statements as structured data lets the system compare charged against expected fees and flag discrepancies. The portal's job is getting every statement, in any format, into that analysis so the comparison can run at all."),
            ("How do I process TWIST BSB or proprietary bank fee statements into SAP?",
             "Banks issue fee statements in TWIST BSB, the older industry format, in CAMT.086, and in their own proprietary layouts. SAP's native analysis expects CAMT.086, so the off-format statements stall. A format-agnostic portal parses TWIST BSB and proprietary files, normalizes them to the structure SAP's analyzer reads, and delivers them in, so no bank is left out of the review."),
        ]))
    )


def web_body_treasurycentral(p):
    return (
        web_hero(
            p, "The treasury cockpit", 'Treasury<span class="ac">Central</span>',
            "Cash, investments, debt, FX and market data in one screen, on your SAP data.",
            ["One view of the money: cash, investments and debt across entities, reconciled to SAP.",
             "FX and market data validated before they reach a decision.",
             "Audit trail, manage-by-exception, four-eye and segregation of duties on every record."],
            vis_treasurycentral())
        + web_band("The problem",
                   '<p class="wlede">Most SAP finance teams run several brittle, hand-built feeds to move market data, trades, bank files and remittances in and out of SAP. They break when a field changes or the person who built them leaves: no audit trail, no owner, no monitoring. Between them, the treasurer\'s day goes to moving data between screens instead of using it.</p>'
                   '<p class="wlede" style="margin-bottom:0;">TreasuryCentral is OnePilot scoped to the treasurer: cash, investments, debt, FX, market data and governance on one screen, on your SAP data. The cockpit is what you see; OnePilot is the layer that moves the data in and out of SAP, governed end to end. It takes the brittle feeds off your team, and the treasurer stays in command.</p>',
                   h2="The treasurer's day on one surface")
        + web_band("What you get", web_cards([
            ("One view of the money", "Cash, investments and debt",
             "Cash positions roll up from every bank account and entity, reconciled to the statements already in SAP, so the group number is current instead of a Monday spreadsheet pull. Investments, debt and intercompany loans sit on the same screen with their maturities and interest, and every figure links back to the SAP record it came from."),
            ("FX and market data, governed", "Numbers you can trace",
             "Spot and forward rates, yield curves and prices arrive from Bloomberg, Refinitiv, 360T and central-bank feeds, normalized once and checked for gaps and outliers before anything posts. FX exposure by currency and entity updates as positions move, with the source and the validation recorded against each value, so a hedge decision rests on numbers you can trace."),
            ("Control built in", "Governed by design",
             "Every value carries where it came from, who approved it and when, so an audit follows the trail without a reconstruction project. Limits and tolerances are set once; only the records that breach them surface for a person, and a second approver signs off before a payment or a deal is released."),
        ]), alt=True)
        + web_band("What it takes off your team", web_dots2([
            "Market data: rates, curves and prices from every provider, governed into SAP.",
            "Trades: captured at the venue and booked in SAP TRM, straight through.",
            "Bank files: fee statements in any format, matched against the agreement.",
            "Remittances: unstructured advice read by AI and posted to S/4HANA."]),
            h2="The brittle feeds it replaces",
            lede="The apps that run underneath TreasuryCentral each take one hand-built feed off your team, governed end to end, so the cockpit shows a number you can act on rather than one you have to assemble.")
        + web_band("Common questions", web_faq([
            ("What is TreasuryCentral?",
             "TreasuryCentral is the treasury edition of OnePilot. It puts the treasurer's whole day on one surface: cash, FX, market data, trades, bank files and remittances, governed end to end, on your SAP data."),
            ("What runs underneath TreasuryCentral?",
             "The treasury apps run on OnePilot, the governed AI layer that moves data in and out of SAP. TreasuryCentral is OnePilot scoped to the treasurer, so market data, trades, bank files and remittances all flow through one governed layer, on your SAP data."),
            ("Does it need a separate data store?",
             "No. It works on the SAP data you already trust, so there is no separate store to reconcile. Every move is logged, and every action stays inside your controls."),
        ]), alt=True)
    )


def web_body_onepilot(p):
    return (
        web_hero(
            p, "The AI operating layer", 'One<span class="ac">Pilot</span>',
            "The governed AI layer that runs your treasury apps. In production now.",
            ["It asks, automates and acts across the applications, always inside your controls.",
             "Build your own apps and automations without writing a line of code.",
             "The book of record stays in SAP; OnePilot orchestrates on top, SAP and non-SAP, both ways.",
             "In production: a financial-services group governs several data domains from one deployment."],
            vis_onepilot(), bare=True)
        + web_band("The problem",
                   '<p class="wlede">A treasurer\'s day becomes tab management: the trading platform in one window, market data in another, bank portals and cash tools in others, and the numbers re-keyed between them. The day goes to moving data instead of using it. Around SAP, that shows up as shadow integrations, hand-keyed files and home-built scripts that move data in, fragile and unowned, plus a backlog of interfaces to build and maintain.</p>'
                   '<p class="wlede" style="margin-bottom:0;">OnePilot puts the data in one governed place, so the day shifts back to using it: deciding, not re-typing. It is a no-code layer over your SAP landscape where permissioned AI agents do the repetitive work, ingesting, validating, posting and reconciling, always inside your controls. The book of record stays in SAP; OnePilot orchestrates on top.</p>',
                   h2="Why a treasurer's day becomes tab management")
        + web_band("The market", web_stats([
            ("71%", "of US SAP-treasury roles describe building or hand-running integrations into SAP, or manual data work (29 of 41)."),
            ("34%", "are tied to an active S/4HANA migration or SAP implementation, the moment feeds get re-plumbed (14 of 41)."),
            ("22%", "name a specific market-data or trading vendor whose feed has to reach SAP, and that is a floor (9 of 41)."),
        ], "Source: Brisken Shadow Integration Report, N=41 US SAP-treasury job ads, read 2026-06-17. These are market-research figures, not an OnePilot performance metric."),
            h2="The shadow integration is the default state, not the exception", alt=True)
        + web_band("How it works", web_steps([
            ("1", "Ingest", "Any source and format: Bloomberg, Refinitiv, 360T, OANDA, central banks, banks, files, email."),
            ("2", "Validate", "Cleansing, mapping, calculations and anomaly detection, before anything reaches SAP."),
            ("3", "Govern", "Audit trail, manage-by-exception, segregation of duties and four-eye on every record."),
            ("4", "Distribute", "Straight into S/4HANA, TRM, Cash and Credit Management. No ABAP, no custom interface."),
        ], cols=4), h2="From any source to governed SAP records",
            lede="OnePilot Agents learn your systems and recommend each mapping; you approve it, and the feed runs governed end to end, SAP and non-SAP, both ways. Configured, not coded, so a new feed goes live in weeks rather than a multi-quarter build your team then owns.")
        + web_band("Governed by design", web_cards([
            ("Permission-bound agents", "Agents act within access",
             "An agent sees and acts only on what the user is allowed to. Access outside that boundary is not dimmed, it is absent, so an agent can never reach data or an action the person behind it could not."),
            ("Four-eye and segregation of duties", "The agent prepares, a person releases",
             "Approvals and separation of duties sit on the actions that need them. The agent prepares the work; a person releases it, so no payment or deal moves on the AI's say-so alone."),
            ("Full audit trail", "Manage by exception",
             "Every record is traceable, carrying where it came from, who approved it and when. You manage by exception, only the records that breach a rule surface for a person, and nothing moves outside the rules you set."),
        ]))
        + web_band("How it connects", web_chips([
            ("RFC & OData", None), ("SFTP", None), ("SOAP & REST", None), ("AMQP", None),
            ("Email", None), ("Excel add-in", None), ("XLSX / CSV / TXT", None), ("Web scraping", None), ("LLM & browser automation", None)])
            + '<p class="wlede" style="margin-top:22px;margin-bottom:0;">Push and pull, off-the-shelf, third-party-managed and low-maintenance. Sources on one side (Bloomberg, Refinitiv, 360T, OANDA, central banks, banks, files and email) and SAP on the other (S/4HANA, TRM, Cash and Credit Management), with non-SAP systems in the same governed perimeter. A new feed is set up on a managed product, so it goes live in weeks rather than a multi-quarter integration project your team has to build and then own.</p>',
            h2="Connects to what you already run", alt=True)
        + web_band("In production", web_cards([
            ("Financial services", "S/4HANA Public Cloud", "A financial-services group already governs several data domains from one OnePilot deployment."),
            ("Agricultural", "S/4HANA Private Cloud", "Posts remittances into S/4HANA on a governed AI gate, a ChatGPT-powered deployment with the retype removed."),
            ("Chemicals", "S/4HANA On-Prem", "An AI funding-request process, a complex multi-integration with SAP, fully automated."),
        ]))
        + web_band("Common questions", web_faq([
            ("Does OnePilot replace SAP?",
             "No. OnePilot orchestrates on top of SAP. The book of record stays in SAP, execution on the trading platform, and market data through the hub. It composes the apps and data your work needs on one surface, without moving the system of record."),
            ("Can we deploy AI agents in treasury without consuming our IT budget?",
             "Yes. OnePilot is configured, not coded, and runs as a managed product on top of your SAP landscape, so there is no ABAP build and nothing new for your IT team to own or maintain. A new feed or agent is set up on the product and goes live in weeks, which keeps the work off the IT backlog and the cost off the development budget."),
            ("Is AI automation in treasury safe?",
             "It is safe when the AI runs inside your controls rather than around them. Each OnePilot process works to rules you set and approve, with four-eye release, segregation of duties and a full audit trail on every record. You keep command of policy and exceptions; the AI handles the repetitive steps, and nothing moves outside the rules you define."),
            ("Can AI improve liquidity forecasting?",
             "Yes. A forecast is only as good as the data feeding it, and most of the delay is in collecting and cleaning cash, bank and exposure data by hand. OnePilot keeps that data current and governed in SAP, so the forecast runs on a clean, reconciled base. Treasury still owns the assumptions and the call; the AI removes the manual data work that slows the forecast down."),
            ("Can AI help the team focus the day on what matters?",
             "Yes. The repetitive work, ingesting feeds, validating, posting and reconciling, runs underneath by exception, so the team sees what needs a decision instead of working through every record. Their day shifts from re-keying and chasing data to judgment, review and the exceptions that actually need a person."),
        ]))
        + web_band("Proof",
                   '<p class="wlede" style="margin:0;">OnePilot is delivered by an SAP Co-Innovation Partner and PartnerEdge member, part of SAP Industry Cloud for Financial Services and Commodities, certified to ISO 27001 and SOC 1 Type II, with data partners including Bloomberg, Refinitiv, CME Group, 360T, Deutsche Boerse and OANDA. The Market Data Hub and Smart Trading are listed on the SAP Store.</p>', alt=True)
    )


WEB_BODIES = {
    "market-data-hub": web_body_market_data_hub,
    "smart-trading": web_body_smart_trading,
    "remittance-advice-gate": web_body_remittance,
    "bank-fee-portal": web_body_bank_fee,
    "treasurycentral": web_body_treasurycentral,
    "onepilot": web_body_onepilot,
}

# Per-product deck link (only where a full deck exists on the site) + closing copy.
WEB_META = {
    "market-data-hub": dict(deck="/market-data-hub-deck.html"),
    "smart-trading": dict(deck="/smart-trading-deck.html"),
    "remittance-advice-gate": dict(),
    "bank-fee-portal": dict(),
    "treasurycentral": dict(),
    "onepilot": dict(),
}


def _sheet(p):
    body = p["body"].replace("</main>", PROOF + "\n</main>")
    return f'''<div class="topline"></div><div class="sheet">
<header><img class="logo-img" src="data:image/png;base64,{LOGOS['brisken']}" alt="Brisken">
<div class="partner"><span class="sapbadge">SAP</span> Co-Innovation Partner</div></header>
{body}
<footer><b>Brisken</b> &middot; SAP Co-Innovation Partner &middot; www.brisken.com</footer>
</div>'''


def _head(p, extra_css=""):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Brisken &middot; {p.get('title', 'Resources')}</title>
<meta name="robots" content="noindex">
<link rel="icon" type="image/png" href="data:image/png;base64,{FAVICON}">
<link rel="apple-touch-icon" href="data:image/png;base64,{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>:root{{--ac:{p['accent']};--ac2:{p['accent2']};--glow:{p['glow']};}}{BASE_CSS}{extra_css}</style></head>'''


def page(p):  # print / PDF: bare A4 sheet
    return f'{_head(p)}\n<body>{_sheet(p)}</body></html>'


def page_web(p):  # native web page: full-bleed responsive product page
    short = p["short"]
    pw = {**p, **WEB_META.get(short, {})}
    body = WEB_BODIES[short](pw)
    return f'''{_head(pw, WEB_CSS)}
<body>
<div class="wnav">
  <a class="nl" href="/">
    <img class="nlogo" src="data:image/png;base64,{LOGOS['brisken']}" alt="Brisken">
    <span class="sep">&middot;</span><span class="plabel">{pw['title']}</span>
  </a>
  <div class="nr"><a class="nback" href="/">&larr; All resources</a>
  <a class="ndl" href="/{short}.pdf" download>Download PDF</a></div>
</div>
{body}
<section class="wproof"><div class="inner">{PROOF}</div></section>
{web_cta_band(pw)}
{web_footer()}
</body></html>'''


# The three multi-page product decks. Copy traces to the approved index-card
# lines and the shipped one-pager bodies; no new claims. These pages wrap the
# existing deck PDFs in the same nav/hero/band frame as the one-pagers.
DECKS = [
    dict(short="market-data-hub-deck", pdf="market-data-hub-deck", pages=12,
         title="Market Data Hub deck", h1="Market Data Hub",
         accent="#0891b2", accent2="#22b8cf", glow="rgba(8,145,178,.28)",
         promise="Every market-data feed in, one governed layer, six steps from source to system.",
         points=["Bloomberg, LSEG, ICE and CME feeds into one governed layer",
                 "Six steps from source to SAP, no code in the middle",
                 "One normalized feed your treasury apps read"],
         lede="Twelve pages: the providers, the governed layer in the middle, and the six steps "
              "that carry a rate from the source into SAP."),
    dict(short="smart-trading-deck", pdf="smart-trading-deck", pages=10,
         title="Brisken Smart Trading deck", h1="Brisken Smart Trading",
         accent="#2563eb", accent2="#60a5fa", glow="rgba(37,99,235,.26)",
         promise="From the trade decision to the booked deal in SAP, with the manual middle gone.",
         points=["Straight-through capture into SAP TRM, no re-key",
                 "The trade decision through to the booked deal in one flow",
                 "The manual middle step removed"],
         lede="Ten pages: how a trade moves from the decision to a booked deal in SAP TRM without "
              "the manual re-keying that usually sits in between."),
    dict(short="digital-co-worker", pdf="digital-co-worker", pages=11,
         title="Digital Co-Worker deck", h1="Digital Co-Worker",
         accent="#9333ea", accent2="#c084fc", glow="rgba(147,51,234,.30)",
         promise="An AI co-worker that takes the repetitive steps across your systems, governed and logged.",
         points=["Runs the repetitive steps across your SAP systems",
                 "Every action governed and logged",
                 "Works inside the controls you already run"],
         lede="Eleven pages: where an AI co-worker fits across your systems, the steps it takes, "
              "and the controls that keep every action governed and logged."),
]


def page_deck(d):
    pts = "".join(f"<li>{x}</li>" for x in d["points"])
    pdf = f'/{d["pdf"]}.pdf'
    return f'''{_head(d, WEB_CSS + DECK_CSS)}
<body>
<div class="wnav">
  <a class="nl" href="/">
    <img class="nlogo" src="data:image/png;base64,{LOGOS['brisken']}" alt="Brisken">
    <span class="sep">&middot;</span><span class="plabel">{d['title']}</span>
  </a>
  <div class="nr"><a class="nback" href="/">&larr; All resources</a>
  <a class="ndl" href="{pdf}" download>Download PDF</a></div>
</div>
<section class="whero"><div class="inner">
  <div class="hcopy">
    <div class="weyebrow">Full deck &middot; {d['pages']} pages</div>
    <h1>{d['h1']}</h1>
    <p class="wpromise">{d['promise']}</p>
    <ul class="wpoints">{pts}</ul>
    <div class="wcta">
      <a class="wbtn primary" href="{pdf}" download>Download the deck</a>
      <a class="wbtn ghost" href="/">All resources</a>
    </div>
  </div>
  <div class="wvisual deckcard">
    <div class="wvlab">{d['pages']}-page deck</div>
    <div class="deckstack">
      <span class="sl s3"></span><span class="sl s2"></span>
      <span class="sl s1"><span class="slrow"></span><span class="slrow w70"></span><span class="slrow w45"></span></span>
    </div>
  </div>
</div></section>
<section class="wband alt"><div class="inner">
  <div class="wlab">The deck</div>
  <h2 class="wh2">All {d['pages']} pages</h2>
  <p class="wlede">{d['lede']}</p>
  <div class="deckframe"><iframe class="deckview" src="{pdf}#toolbar=0&navpanes=0&view=FitH" title="{d['h1']} deck" loading="lazy"></iframe></div>
  <div class="deck-fallback">This deck opens best on a larger screen.<br><a href="{pdf}">Download the PDF</a> to view all {d['pages']} pages.</div>
</div></section>
{web_footer()}
</body></html>'''


def build_products():
    return [
        dict(slug="brisken-market-data-hub-onepager",        short="market-data-hub",        title="Market Data Hub",        accent="#0891b2", accent2="#22b8cf", glow="rgba(8,145,178,.28)",  body=body_market_data_hub()),
        dict(slug="brisken-smart-trading-onepager",          short="smart-trading",          title="Brisken Smart Trading",  accent="#2563eb", accent2="#60a5fa", glow="rgba(37,99,235,.26)",  body=body_smart_trading()),
        dict(slug="brisken-remittance-advice-gate-onepager", short="remittance-advice-gate", title="Remittance Advice Gate", accent="#059669", accent2="#34d399", glow="rgba(5,150,105,.26)",  body=body_remittance()),
        dict(slug="brisken-bank-fee-portal-onepager",        short="bank-fee-portal",        title="Bank Fee Portal",        accent="#ea580c", accent2="#fb923c", glow="rgba(234,88,12,.26)",  body=body_bank_fee_portal()),
        dict(slug="brisken-treasurycentral-onepager",        short="treasurycentral",        title="TreasuryCentral",        accent="#4f46e5", accent2="#818cf8", glow="rgba(79,70,229,.26)",  body=body_treasurycentral()),
        dict(slug="brisken-onepilot-onepager",               short="onepilot",               title="OnePilot",               accent="#9333ea", accent2="#c084fc", glow="rgba(147,51,234,.30)", body=body_onepilot()),
    ]


PRODUCTS = build_products()


def render(html_path: Path, pdf_path: Path):
    tmp_out = pdf_path.with_name(pdf_path.name + ".tmp")
    tmp_out.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="sap-onepager-") as prof:
        cmd = [str(CHROME), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
               "--no-first-run", "--no-default-browser-check",
               f"--user-data-dir={prof}", f"--print-to-pdf={tmp_out}", html_path.as_uri()]
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
    ap = argparse.ArgumentParser(description="Render the 6 Brisken SAP one-pagers (PDF + web pages) and gate them.")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT, help=f"PDF output dir (default: {OUT_DEFAULT})")
    ap.add_argument("--web-out", type=Path, default=WEB_OUT_DEFAULT, help=f"web-page HTML output dir (default: {WEB_OUT_DEFAULT})")
    ap.add_argument("--web-only", action="store_true",
                    help="write only the web-page HTML; skip the Chrome PDF render and the gate")
    args = ap.parse_args()

    # The downloadable PDF is a render of the SAME web page (via its @media print
    # stylesheet), so the download and the site have identical content.
    web = args.web_out.resolve()
    web.mkdir(parents=True, exist_ok=True)
    for p in PRODUCTS:
        (web / f'{p["short"]}.html').write_text(page_web(p), encoding="utf-8")
    print(f"web pages: {len(PRODUCTS)} written -> {web}")

    # The 3 full-deck pages: same nav/hero/band frame as the one-pagers, wrapping
    # the existing deck PDFs (no re-render; the deck PDFs are already built).
    for d in DECKS:
        (web / f'{d["short"]}.html').write_text(page_deck(d), encoding="utf-8")
    print(f"deck pages: {len(DECKS)} written -> {web}")

    if args.web_only:
        print("web-only: skipped PDF render")
        return 0

    if not CHROME.is_file():
        sys.exit(f"Chrome not found at {CHROME}; it is the only render engine that works while Edge is open")

    print("PRODUCT | PDF pages | size KB")
    pdfs: list[Path] = []
    for p in PRODUCTS:
        hp = web / f'{p["short"]}.html'          # render the served page itself
        pdf = web / f'{p["short"]}.pdf'
        render(hp, pdf)
        pdfs.append(pdf)
        pages = len(PdfReader(str(pdf)).pages)
        kb = round(pdf.stat().st_size / 1024)
        print(f'{p["short"]:24s} | {pages} | {kb}')

    if not run_gate(pdfs):
        print("BANNED-CONTENT GATE FAILED on the rendered PDFs; do not ship them")
        return 1
    print("banned-content gate: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
