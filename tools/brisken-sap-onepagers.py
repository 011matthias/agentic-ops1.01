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


# Web-page chrome (appended after BASE_CSS so it overrides the print sizing):
# each one-pager is also served as a native page on resources.brisken.com, the
# A4 sheet centred on a neutral stage with a back link + Download PDF button.
WEB_CSS = r"""
html,body{width:auto;height:100%;}
body{margin:0;height:100vh;display:flex;flex-direction:column;background:#e2e8f0;overflow:hidden;}
.topbar{flex:0 0 auto;display:flex;justify-content:space-between;align-items:center;
  padding:12px 22px;background:#fff;border-bottom:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(15,23,42,.06);}
.topbar a{font-family:'IBM Plex Sans',sans-serif;text-decoration:none;font-size:14px;font-weight:600;}
.tb-back{color:#475569;}
.tb-dl{background:var(--ac);color:#fff;padding:8px 18px;border-radius:99px;}
.stage{flex:1 1 auto;display:flex;align-items:center;justify-content:center;overflow:auto;padding:14px;}
.sheet-wrap{flex:0 0 auto;position:relative;width:210mm;background:#fff;overflow:hidden;
  box-shadow:0 10px 34px rgba(15,23,42,.18);}
.sheet-wrap .sheet{height:auto;min-height:297mm;}
"""

# fit-to-viewport: scale the A4 sheet to fill the stage (presentation full-screen)
FIT_JS = ("<script>(function(){var w=document.querySelector('.sheet-wrap'),"
          "s=document.querySelector('.stage'),W=210*96/25.4,H=297*96/25.4;"
          "function f(){var z=Math.min((s.clientWidth-28)/W,(s.clientHeight-28)/H);"
          "if(z>0)w.style.zoom=z;}addEventListener('resize',f);addEventListener('load',f);f();})();</script>")


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
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>:root{{--ac:{p['accent']};--ac2:{p['accent2']};--glow:{p['glow']};}}{BASE_CSS}{extra_css}</style></head>'''


def page(p):  # print / PDF: bare A4 sheet
    return f'{_head(p)}\n<body>{_sheet(p)}</body></html>'


def page_web(p):  # native web page: chrome + sheet scaled to fill the screen
    return f'''{_head(p, WEB_CSS)}
<body>
<div class="topbar"><a class="tb-back" href="/">&larr; Brisken Resources</a>
<a class="tb-dl" href="/{p['short']}.pdf">Download PDF</a></div>
<div class="stage"><div class="sheet-wrap">{_sheet(p)}</div></div>
{FIT_JS}
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
    ap.add_argument("--no-web", action="store_true", help="skip writing the native web-page HTML")
    args = ap.parse_args()

    if not CHROME.is_file():
        sys.exit(f"Chrome not found at {CHROME}; it is the only render engine that works while Edge is open")

    out = args.out.resolve()  # Chrome --print-to-pdf needs an absolute target
    out.mkdir(parents=True, exist_ok=True)
    print("PRODUCT | pages | size KB")
    all_ok = True
    pdfs: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="sap-onepager-html-") as html_dir:
        for p in PRODUCTS:
            html = page(p)
            hp = Path(html_dir) / f'{p["slug"]}.html'
            hp.write_text(html, encoding="utf-8")
            pdf = out / f'{p["slug"]}.pdf'
            render(hp, pdf)
            pdfs.append(pdf)
            pages = len(PdfReader(str(pdf)).pages)
            kb = round(pdf.stat().st_size / 1024)
            flag = "" if pages == 1 else "  <-- NOT 1 PAGE"
            if pages != 1:
                all_ok = False
            print(f'{p["slug"]:42s} | {pages} | {kb}{flag}')
    print("ALL SINGLE-PAGE" if all_ok else "PAGE-COUNT FAILURE")

    if not run_gate(pdfs):
        print("BANNED-CONTENT GATE FAILED on the rendered PDFs; do not ship them")
        return 1
    print("banned-content gate: PASS")

    if not args.no_web:
        web = args.web_out.resolve()
        web.mkdir(parents=True, exist_ok=True)
        for p in PRODUCTS:
            (web / f'{p["short"]}.html').write_text(page_web(p), encoding="utf-8")
        print(f"web pages: {len(PRODUCTS)} written -> {web}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
