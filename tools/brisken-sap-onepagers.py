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


# The brisken mark is a 92 KB base64 blob and appears in two places on a web
# page (nav + print letterhead). Inlining it twice put ~92 KB of duplicate text
# in every page; defining it once in CSS and pointing both at it does not.
# Native size 718x157, so width:height is 4.573:1; both users set an explicit
# box because a background image has no intrinsic size to lay out from.
LOGO_CSS = (
    f'.blogo{{background-image:url("data:image/png;base64,{LOGOS["brisken"]}");'
    'background-repeat:no-repeat;background-position:left center;'
    'background-size:contain;display:block;flex:0 0 auto;}'
)


def blogo(cls: str) -> str:
    return f'<span class="blogo {cls}" role="img" aria-label="Brisken"></span>'


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


# The shared credential strip. No blanket "live" claim: it shows on every page,
# including Bank Fee (POC), so a live claim here would be false on that page.
PROOF = ('<div class="proof">'
         '<span class="pchip"><span class="sapbadge">SAP</span> Co-Innovation Partner</span>'
         '<span class="pchip">SAP Store</span>'
         '<span class="pchip">ISO 27001</span>'
         '<span class="pchip">SOC 1 Type II</span>'
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
      <div class="eyebrow">Bank fee statements</div>
      <h1>Bank Fee<br>Portal</h1>
      <p class="promise">Every bank's fee statement, whatever format it arrives in, turned into data your fee analyzer can actually read.</p>
      <p class="rename">The statements that arrive off-format never reach the analyzer, so their fees never get reviewed.</p>
    </div>
    <div class="panel">
      <div class="vlab">Any format in &middot; one structure out</div>
      <div class="rflow">
        <div class="rrow"><span class="dpill">CAMT.086</span><span class="dpill">XML</span><span class="dpill">TWIST BSB</span><span class="dpill">Bank proprietary</span></div>
        <div class="rside">One fee statement per bank, every bank a different shape</div>
        <div class="stem"></div>
        <div class="dai">reads &middot; validates &middot; enriches</div>
        <div class="stem"></div>
        <div class="outs"><span class="out">Bank Fee Analyzer</span><span class="out">TMS</span><span class="out">Analytics</span></div>
        <div class="vcap">The portal prepares the data. The analyzer runs the comparison.</div>
      </div>
    </div>
  </div>
  <div>
    <div class="band-lab">How it works</div>
    <div class="steps">
      <div class="step"><div class="sn">1</div><div class="st">Read</div><div class="sd">Every fee statement, from every account, in any format.</div></div>
      <div class="step"><div class="sn">2</div><div class="st">Validate and enrich</div><div class="sd">Checked, and the derived fees calculated rather than left buried.</div></div>
      <div class="step"><div class="sn">3</div><div class="st">Deliver</div><div class="sd">Into your Bank Fee Analyzer, TMS or analytics, plus a dashboard.</div></div>
    </div>
  </div>
  {dark_band("What it <span>puts in reach</span>", [
      "The banks whose statement format never reached the fee review before",
      "Derived fees calculated during enrichment, instead of left buried in the file"], mark="+")}
</main>'''


def body_treasurycentral():
    pillars = "".join(f'<div class="pil">{x}</div>'
                      for x in ["Market data governance", "Autonomous trading"])
    return f'''<main>
  <div class="hero stack">
    <div class="eyebrow">The treasury workspace</div>
    <h1>Treasury<span class="ac">Central</span></h1>
    <p class="promise">Where your people and AI agents run treasury together, on top of your SAP systems.</p>
  </div>
  <div class="arch">
    <div class="arch-top">Treasury<span class="ac">Central</span><span class="lab">the treasury workspace</span></div>
    <div class="arch-conn"></div>
    <div class="arch-pillars">{pillars}</div>
    <div class="arch-base">on <b>OnePilot</b>, on your SAP data</div>
  </div>
  <div class="cols2">
    <div>
      <div class="band-lab">One workspace</div>
      <p class="p">The treasurer's day on one surface, with people and AI agents working together and the process orchestrated end to end. Governance is built in, not bolted on afterwards.</p>
    </div>
    <div>
      <div class="band-lab">Two applications underneath</div>
      {dots(["Market data governance and autonomous trading, run on OnePilot.",
             "No separate data store; it works on the SAP data you already trust, every action inside your controls."])}
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
.wnav .nl .nlogo{height:22px;width:101px;display:block;}
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

/* print-only letterhead: the nav (the only Brisken mark on screen) is hidden in
   print, so the downloaded PDF would otherwise open with nothing identifying
   Brisken on it. This block is invisible on screen and heads page 1 in print. */
.wprint-head{display:none;}

/* ---- TreasuryCentral: OnePilot is the field, not a box -------------------
   Dirk's V3 model (TreasuryCentral-Architecture-Handoff.md, SharePoint
   MARKETING / WIP PPTX 2026, 2026-07-21), sections 2.2 and 3: OnePilot is
   not a box among boxes, it is the whole environment, and everything floats
   inside it. There is no "outside".
   His own verdict on the V3 render was "still very boring, boxes everywhere"
   (35 bordered tiles in two grids), so the rosters here are flowing text on
   the field and the workspace card is the only bordered element. */
.tcf{position:relative;overflow:hidden;border-radius:16px;padding:24px;
  background:radial-gradient(130% 100% at 50% -22%,#232466,#111634 52%,#080b1d);
  box-shadow:inset 0 0 0 1px rgba(129,140,248,.3);}
.tcf .fl{font-family:'Space Grotesk';font-size:10.5px;font-weight:600;letter-spacing:.2em;
  text-transform:uppercase;color:#767f9f;margin-bottom:15px;text-align:center;}
.tcf .fl b{color:#a5b0ff;font-weight:600;}
.tcf .sep{color:#525b8a;margin:0 3px;font-weight:400;}
.tcf .it{white-space:nowrap;}

/* the workspace: the one card in the diagram */
.tcws{position:relative;border:1px solid rgba(129,140,248,.55);border-radius:12px;padding:19px 21px;
  background:linear-gradient(180deg,rgba(99,102,241,.19),rgba(99,102,241,.05));
  box-shadow:0 0 46px -8px rgba(99,102,241,.45);}
.tcws .nm{font-family:'Space Grotesk';font-size:24px;font-weight:700;color:#fff;letter-spacing:-.5px;line-height:1;}
.tcws .nm .ac{color:#a5b0ff;}
.tcws .sub{font-family:'Space Grotesk';font-size:10.5px;font-weight:600;letter-spacing:.19em;
  text-transform:uppercase;color:#8990b4;margin-top:8px;}
.tcws .ln{font-size:14.5px;line-height:1.55;color:#c9cee6;margin-top:13px;}
.tcws .cap{font-size:13px;font-weight:600;color:#a5b0ff;margin-top:13px;}
.tcws .cap .sep{color:#6a72a8;margin:0 7px;}
/* the real product shot, in place of V3's striped image placeholder */
.tcshot{margin:16px 0 0;padding:0;}
.tcshot img{display:block;width:100%;height:auto;border-radius:8px;
  border:1px solid rgba(148,163,184,.22);}
.tcshot figcaption{font-size:11.5px;color:#7e86a8;margin-top:8px;}
.tcapps{margin-top:16px;padding-top:15px;border-top:1px solid rgba(148,163,184,.2);
  font-size:14px;font-weight:600;line-height:2;color:#e7eaf6;}
.tcapps .own{color:#a5b0ff;}
.tcdesk{margin-top:14px;padding-top:13px;border-top:1px solid rgba(148,163,184,.14);
  font-size:13px;color:#99a1c0;line-height:1.75;}
.tcdesk .dk{font-family:'Space Grotesk';font-size:9.5px;font-weight:600;letter-spacing:.17em;
  text-transform:uppercase;color:#6f7793;margin-right:11px;}

/* OnePilot woven through the stack: a thread, never a layer box */
.tcw{display:flex;align-items:center;flex-wrap:wrap;gap:8px 14px;margin:21px 0 17px;}
.tcw .wn{font-family:'Space Grotesk';font-size:14.5px;font-weight:700;color:#a5b0ff;white-space:nowrap;}
.tcw .wr{flex:1 1 60px;height:1px;background:linear-gradient(90deg,rgba(129,140,248,.65),rgba(129,140,248,.06));}
.tcw .wt{font-size:12.5px;line-height:1.5;color:#8b93b8;max-width:56ch;}

/* the two rosters: label plus flowing text, no tiles */
.tcb+.tcb{margin-top:17px;}
.tcb .bl{font-family:'Space Grotesk';font-size:9.5px;font-weight:600;letter-spacing:.19em;
  text-transform:uppercase;color:#6f7793;margin-bottom:9px;}
.tcb .bi{font-size:14px;line-height:1.95;color:#c4cade;}
.tcb .bi b{color:#fff;font-weight:700;}
.tcb .bi .q{color:#7e86a8;font-size:12.5px;}

/* hero panel runs the same field at reduced density */
.tcf.compact{padding:19px;}
.tcf.compact .tcws{padding:16px 17px;}
.tcf.compact .tcws .nm{font-size:21px;}
.tcf.compact .tcws .ln{font-size:13.5px;margin-top:11px;}
.tcf.compact .tcw{margin:16px 0 13px;}
.tcf.compact .tcb .bi{font-size:13px;line-height:1.85;}
@media(max-width:900px){.tcw .wt{max-width:none;}}

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
  /* Brisken letterhead on page 1 of every downloaded PDF */
  .wprint-head{display:flex !important;align-items:center;justify-content:space-between;gap:12mm;
    padding:0 0 4mm;margin-bottom:6mm;border-bottom:1px solid #e6ebf2;border-top:1.3mm solid var(--ac);
    padding-top:4mm;break-after:avoid;}
  .wprint-head .plogo{height:9mm;width:41mm;display:block;}
  .wprint-head .pright{display:flex;align-items:center;gap:3mm;font-size:10pt;color:#475569;font-weight:500;white-space:nowrap;}
  .wprint-head .psap{background:#0a6ed1;color:#fff;font-weight:700;font-size:8.5pt;padding:1mm 2mm;border-radius:1.2mm;letter-spacing:.5px;}
  .wprint-head .pdoc{font-family:'Space Grotesk';font-weight:600;color:#0f172a;}
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
  /* the open-state toggle is a rotated "+", which prints as a red x next to
     every question and reads as an error mark on paper. Screen-only affordance. */
  .wfaq summary::after{display:none !important;}
  .wcard .cd{font-size:12px !important;}
  .wproof{padding:6mm 0 !important;}
  .wfoot{background:#fff !important;padding:6mm 0 0 !important;}
  a{color:inherit !important;}
  /* the OnePilot field keeps its dark ground in the PDF (colour-adjust is
     forced above); only the density comes down to A4.
     The shared .wband break-inside:avoid would move this whole band, product
     shot and all, to the next page and strand an 80%-empty page behind it, so
     this one band may break; the field itself still may not. */
  .wband:has(.tcf){break-inside:auto !important;}
  .tcshot img{max-height:62mm;object-fit:contain;object-position:left top;}
  .tcf{break-inside:avoid;padding:5mm !important;}
  .tcws{padding:4mm !important;}
  .tcws .nm{font-size:17px !important;}
  .tcws .ln{font-size:11.5px !important;margin-top:2.5mm !important;}
  .tcws .cap{font-size:11px !important;margin-top:2.5mm !important;}
  .tcapps{font-size:11.5px !important;line-height:1.75 !important;margin-top:3mm !important;padding-top:3mm !important;}
  .tcdesk{font-size:10.5px !important;line-height:1.6 !important;}
  .tcw{margin:4mm 0 3.5mm !important;}
  .tcb .bi{font-size:11.5px !important;line-height:1.75 !important;}
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
LAST_UPDATED = "2026-07-29"

# Brisken's own primary call to action, verified live 2026-07-22:
# www.brisken.com's single nav CTA is "Book a demo" -> /demo, a working form
# ("See TreasuryCentral running on SAP"). The product pages reuse it rather than
# inventing a contact route.
DEMO_URL = "https://www.brisken.com/demo"


def dl_name(p) -> str:
    """Filename the browser saves the PDF under. The served path stays
    /{short}.pdf (index.html and the deck pages link to it), but a file landing
    in someone's Downloads folder has to say Brisken on it."""
    return "Brisken-" + p["title"].replace(" ", "-").replace("&", "and") + ".pdf"


def _cta_buttons(p, hero=True):
    """Primary action is always the demo: a reader who wants the product needs a
    way to ask for it, and a download link is not one."""
    pdf = f'/{p["short"]}.pdf'
    out = [f'<a class="wbtn primary" href="{DEMO_URL}">{p.get("cta_btn", "Book a demo")} &rarr;</a>']
    if p.get("deck"):
        out.append(f'<a class="wbtn ghost" href="{p["deck"]}">See the full deck</a>')
    out.append(f'<a class="wbtn ghost" href="{pdf}" download="{dl_name(p)}">Download as PDF</a>')
    return "".join(out)


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
    # Default closing copy per product shape. The old default promised "the full
    # deck" on the four products that have no deck; only the two that do get it.
    if deck:
        h2 = p.get("cta_h", "Want the full picture?")
        para = p.get("cta_p", "The deck goes deeper. A demo shows it running on SAP.")
    else:
        h2 = p.get("cta_h", "See it running on SAP")
        para = p.get("cta_p", "Bring your own systems and formats to the call; we will walk through what the fit looks like.")
    btns = [f'<a class="wbtn primary" href="{DEMO_URL}">{p.get("cta_btn", "Book a demo")} &rarr;</a>']
    if deck:
        btns.append(f'<a class="wbtn ghost" href="{deck}">See the full deck</a>')
    btns.append(f'<a class="wbtn ghost" href="/{p["short"]}.pdf" download="{dl_name(p)}">Download as PDF</a>')
    btns.append('<a class="wbtn ghost" href="https://www.brisken.com">www.brisken.com</a>')
    return (f'<section class="wcta-band"><div class="inner"><h2>{h2}</h2>'
            f'<p>{para}</p>'
            f'<div class="wcta" style="justify-content:center;">{"".join(btns)}</div></div></section>')


def web_footer(p=None):
    # Per-product stamp: a page that was not touched must not claim today's date.
    updated = (p or {}).get("updated", LAST_UPDATED)
    return (f'<footer class="wfoot"><b>Brisken</b>, an SAP Co-Innovation Partner &middot; '
            f'<a href="https://www.brisken.com">www.brisken.com</a><br>Last updated: {updated}</footer>')


# ---- per-product visuals (reuse the A4 brand widgets, laid out for a panel) --
def vis_mdh():
    return (f'<div class="wvlab">Every provider &middot; one feed</div>'
            f'<div class="logos">{lchip("bloomberg")}{lchip("lseg")}{lchip("ice")}{lchip("cme")}</div>'
            '<div class="funnel"><div class="stem"></div><div class="feed">one governed feed</div>'
            '<div class="stem"></div><div class="outs"><span class="out">SAP</span><span class="out">non-SAP</span></div></div>'
            '<div class="vcap">Both directions, no code. Central banks included.</div>')


def vis_smart_trading():
    return ('<div class="wvlab">The central status monitor</div>'
            '<div class="steps" style="grid-template-columns:1fr;gap:16px;">'
            '<div class="step"><div class="sn">01</div><div class="st">Request</div><div class="sd">Exposure in SAP becomes a request, with the controls and four-eyes applied up front.</div></div>'
            '<div class="step"><div class="sn">02</div><div class="st">Execute</div><div class="sd">At the best bid, competitive bids recorded: 360T, FXall, Bloomberg FXGO, banks and brokers.</div></div>'
            '<div class="step"><div class="sn">03</div><div class="st">Match &amp; book</div><div class="sd">Confirmations matched, the deal booked in SAP TRM straight through, no re-keying.</div></div>'
            '<div class="step"><div class="sn">04</div><div class="st">Monitor</div><div class="sd">Every step in one place, with the integration log and anomaly alerts.</div></div>'
            '</div>')


def vis_remittance():
    return ('<div class="wvlab">Unstructured in &middot; ready to clear out</div>'
            '<div class="rflow">'
            '<div class="rrow"><span class="dpill">Email body</span><span class="dpill">PDF attachment</span><span class="dpill">Scanned advice</span></div>'
            '<div class="rside">Unstructured emails and attachments</div>'
            '<div class="stem"></div><div class="dai">reads &middot; structures &middot; enriches</div><div class="stem"></div>'
            f'<div class="sapnode"><img src="data:image/png;base64,{LOGOS["sap"]}" alt="SAP"><b>Your clearing engine</b></div>'
            '<div class="vcap">Enriched and checked. The Gate never matches and never clears.</div></div>')


def vis_bank_fee():
    # 2026-07-21 Dirk review: the previous visual was a charged-vs-agreed bar
    # chart over a "matches / flagged" ledger, i.e. a picture of the comparison
    # the portal does NOT run. Replaced with the mechanism it does run: every
    # statement format in, validated and enriched, delivered to the analyzer.
    fmts = ["CAMT.086", "XML", "TWIST BSB", "Bank proprietary"]
    pills = "".join(f'<span class="dpill">{f}</span>' for f in fmts)
    outs = "".join(f'<span class="out">{o}</span>'
                   for o in ["Bank Fee Analyzer", "TMS", "Analytics"])
    return ('<div class="wvlab">Any format in &middot; one structure out</div>'
            '<div class="rflow">'
            f'<div class="rrow">{pills}</div>'
            '<div class="rside">One fee statement per bank, every bank a different shape</div>'
            '<div class="stem"></div>'
            '<div class="dai">reads &middot; validates &middot; enriches</div>'
            '<div class="stem"></div>'
            f'<div class="outs">{outs}</div>'
            '<div class="vcap">The portal prepares the data. The analyzer runs the comparison.</div>'
            '</div>')


# Dirk's V3 architecture model, taken from TreasuryCentral-Architecture-Handoff.md
# (SharePoint MARKETING / WIP PPTX 2026, written 2026-07-21, sent 21:30 the same
# evening). Rosters are his, verbatim except "&" spelled out: apps from 2.3,
# desktop from 2.4, counterparties from 2.5, enterprise systems from 2.6.
# The canon menu (tc-story-canon.md S17/S18): two APPLICATIONS + seven USE CASES,
# each with its type (APP/UC) and status (LIVE/POC). "Bank Messaging Gate" has no
# deck basis and is removed. Rendered as the workspace roster on the TC page.
TC_APPS = [
    ("Market Data Hub", "APP", "LIVE"),
    ("Brisken Smart Trading", "APP", "LIVE"),
    ("Intercompany Funding Request", "UC", "LIVE"),
    ("Remittance Advice Gate", "UC", "LIVE"),
    ("Cash Flow &amp; Exposure Hub", "UC", "LIVE"),
    ("Bank Fee Portal", "UC", "POC"),
    ("Bank Statement Generator", "UC", "LIVE"),
    ("Credit Data Hub", "UC", "LIVE"),
    ("ESG Data Hub", "UC", "POC"),
]
TC_DESK = ["Mail", "Teams", "Calendar", "Documents and office"]
TC_EXTERNAL = ["Data providers", "Trading venues", "Banks", "Central banks",
               "Government offices", "Credit and rating agencies", "Exchanges",
               "Custodians", "Clearing houses", "Payment networks", "Authorities",
               "Tariffs and customs"]
TC_ENTERPRISE = ["Other ERPs", "Databases", "Data lakes", "BI and analytics",
                 "Trading and OMS", "Risk systems", "Import and export",
                 "Document management", "APIs and connectors", "Best-of-breed apps"]
# 6.1 and 6.2 of the handoff, the two woven OnePilot lines.
TC_WOVEN1 = "one governed layer that brings every source into the workspace, visible, accessible, actionable"
TC_WOVEN2 = "and every enterprise system too, one governed layer for data, process and control"


def _tcflow(items):
    """A roster as flowing text. Dirk's V3 drew each of these as a bordered
    tile, which is what made him call his own diagram boxes everywhere.
    Each term is nowrap so a two-word product name breaks between terms and
    never through one ("Bank Messaging / Gate"). The literal spaces around the
    separator are load-bearing: they are the only break opportunities left once
    the terms themselves cannot break, and without them the row overflows the
    field instead of wrapping."""
    return ' <span class="sep">&middot;</span> '.join(f'<span class="it">{i}</span>' for i in items)


def _tcapp(name, typ, status):
    """One roster item on the workspace card: name + a small APP/UC + LIVE/POC
    chip. Inline-styled to sit on the dark OnePilot field without adding CSS."""
    live = status == "LIVE"
    col = "#a5b0ff" if live else "#fbbf24"
    bg = "rgba(129,140,248,.16)" if live else "rgba(251,191,36,.14)"
    chip = ("<span style=\"font-family:'Space Grotesk';font-size:9px;font-weight:600;"
            "letter-spacing:.06em;padding:1px 6px;border-radius:99px;margin-left:6px;"
            f"background:{bg};color:{col};\">{typ} &middot; {status}</span>")
    return f'<span class="it"><b>{name}</b>{chip}</span>'


def _tcapps_roster(apps):
    return ' <span class="sep">&middot;</span> '.join(_tcapp(*a) for a in apps)


def _tcwoven(text=""):
    t = f'<span class="wt">{text}</span>' if text else ""
    return f'<div class="tcw"><span class="wn">Brisken OnePilot</span><span class="wr"></span>{t}</div>'


def vis_treasurycentral():
    """Hero panel: the one idea, at panel scale. The full roster is the
    architecture band further down the page, so this states the relationship
    (the workspace sits inside the field) without repeating the detail."""
    return ('<div class="wvlab">It&rsquo;s all OnePilot &middot; TreasuryCentral is the workspace inside it</div>'
            '<div class="tcf compact">'
            '<div class="tcws">'
            '<div class="nm">Treasury<span class="ac">Central</span></div>'
            '<div class="sub">The treasury workspace</div>'
            '<div class="ln">The workspace where your team and its Digital Co-Workers '
            'run treasury together, the whole treasury day on one surface.</div>'
            f'<div class="cap">{_tcflow(["Connect", "Orchestrate", "Govern"])}</div>'
            '</div>'
            + _tcwoven()
            + '<div class="tcb"><div class="bl">Everything treasury deals with</div>'
            f'<div class="bi">{_tcflow(["Banks", "Trading venues", "Data providers", "Central banks", "Authorities"])}</div></div>'
            '<div class="tcb"><div class="bl">Everything the business runs on</div>'
            f'<div class="bi">{_tcflow(["<b>SAP</b>", "Other ERPs", "Data lakes", "Trading and OMS", "Best-of-breed apps"])}</div></div>'
            '</div>')


def tc_architecture():
    """The full V3 model at band width. One field, one card, two woven threads,
    two rosters as text.

    The workspace card carries a real product shot where Dirk's V3 had a
    striped "[IMAGE] humans + agents collaborating in TC" placeholder (handoff
    5). Source: SharePoint MARKETING, "260621_ONEPILOT for Financial Planning
    - screenshots only (TreasuryCentral Design).pptx", the investment-dashboard
    frame, cropped to the content area. The crop drops the left nav on purpose:
    it carried dirk.neumann@brisken.com, which does not belong on a published
    page. Dataset in the shot is demo data."""
    shot = _b64("treasurycentral-workspace")
    apps = (_tcapps_roster(TC_APPS) + ' <span class="sep">&middot;</span> '
            '<span class="own">+ the use cases your own team builds</span>')
    return ('<div class="tcf">'
            '<div class="fl">It&rsquo;s all OnePilot &middot; <b>TreasuryCentral</b> is the treasury workspace inside it</div>'
            '<div class="tcws">'
            '<div class="nm">Treasury<span class="ac">Central</span></div>'
            '<div class="sub">The treasury workspace</div>'
            '<div class="ln">Where your team and its Digital Co-Workers run treasury together, the whole treasury day on one surface.</div>'
            f'<div class="cap">{_tcflow(["Connect", "Orchestrate", "Govern"])}</div>'
            f'<figure class="tcshot"><img src="data:image/png;base64,{shot}" alt="The TreasuryCentral workspace: an investment dashboard in OnePilot, showing request status, volume by transaction type and top products by volume." loading="lazy">'
            '<figcaption>The workspace today: the investment dashboard, running in OnePilot.</figcaption></figure>'
            f'<div class="tcapps">{apps}</div>'
            f'<div class="tcdesk"><span class="dk">Your workstation, now in the workspace</span>{_tcflow(TC_DESK)}</div>'
            '</div>'
            + _tcwoven(TC_WOVEN1)
            + '<div class="tcb"><div class="bl">External services and counterparties</div>'
            f'<div class="bi">{_tcflow(TC_EXTERNAL)}</div></div>'
            + _tcwoven(TC_WOVEN2)
            + '<div class="tcb"><div class="bl">Enterprise systems and data</div>'
            f'<div class="bi"><span class="it"><b>SAP</b></span> <span class="it q">on-prem, private cloud, public cloud</span>'
            f'<span class="sep">&middot;</span>{_tcflow(TC_ENTERPRISE)}</div></div>'
            '</div>')


def vis_onepilot():
    pillars = "".join(f'<div class="pil">{x}</div>' for x in ["Connect", "Orchestrate", "Govern"])
    return ('<div class="arch">'
            '<div class="arch-top">One<span class="ac">Pilot</span><span class="lab">the platform</span></div>'
            '<div class="arch-conn"></div>'
            f'<div class="arch-pillars" style="grid-template-columns:repeat(3,1fr);">{pillars}</div>'
            '<div class="arch-base"><b>TreasuryCentral</b>, powered by OnePilot &middot; grounded in SAP, your book of records</div></div>')


# ---- per-product web page bodies ------------------------------------------- #
def web_body_market_data_hub(p):
    return (
        web_hero(
            p, "Market data", 'Market <span class="ac">Data Hub</span>',
            "One source for every rate you rely on.",
            ["Market data means the FX and interest rates, commodity prices and credit ratings a treasury runs on. Today they arrive from a dozen places.",
             "Any source in, any consumer out: Bloomberg, LSEG, 360T, OANDA, CME, central banks, government, websites and internal feeds.",
             "Validated, cleansed and calculated on arrival, then distributed to SAP and non-SAP, both directions, 100% no-code.",
             "An application on OnePilot; inside TreasuryCentral it runs as your team's market-data source."],
            vis_mdh())
        + web_band("Pain and answer", web_cards([
            ("Siloed data", "One source of truth",
             "Rates and prices arrive from a dozen places and nobody owns the number. The hub centralizes them into consistent numbers, at lower data cost."),
            ("Poor data quality", "Governed end to end",
             "Every source is validated, cleansed and calculated on arrival, transparent from source to delivery, on a 360° audit trail."),
            ("Inflexible tooling", "Configurable and agnostic",
             "Any source, any target, any data class, changed any time, 100% no-code."),
        ]), h2="Rates and prices, from a dozen places to one owned number")
        + web_band("The market", web_stats([
            ("71%", "of US SAP-treasury roles describe building or hand-running integrations into SAP, or manual data work (29 of 41)."),
            ("34%", "are tied to an active S/4HANA migration or SAP implementation, the moment feeds get re-plumbed (14 of 41)."),
            ("22%", "name a specific market-data or trading vendor whose feed has to reach SAP, and that is a floor (9 of 41)."),
        ], "Source: Brisken Shadow Integration Report, N=41 US SAP-treasury job ads, read 2026-06-17. These are market-research figures, not a Market Data Hub performance metric."),
            h2="Loading market data by hand is the default, not the exception", alt=True)
        + web_band("How it works", web_steps([
            ("1", "Integrate", "Push and pull, any protocol, any format, no coding."),
            ("2", "Govern", "Validation, anomaly checks, quality and cleansing, with schedulers and the audit trail attached."),
            ("3", "Transform", "Cleanse, normalize, map and date-shift each source into one shape."),
            ("4", "Calculate", "Invert, triangulate and interpolate, plus your own formulas and libraries."),
            ("5", "Store", "The curated market-data store, high performance and available. Any source in, any consumer out."),
        ], cols=5), h2="Any source in, any consumer out",
            lede="The hub sits between every provider and every system that needs a rate. Integrate once, govern and transform in one place, calculate what you need, and store the curated number every consumer reads.")
        + web_band("The market-data space", web_callout(
            "Your team and its Digital Co-Workers run the hub together.",
            "The market-data space is where people and the Digital Co-Worker run the hub side by side. The Co-Worker configures, monitors and operates the feeds; people stay in charge. The Digital Co-Worker is a feature of OnePilot, not a separate product."),
            h2="One new advantage: the market-data space", alt=True)
        + web_band("Why it wins", web_cards([
            ("Source and provider agnostic", "Any provider",
             "Bloomberg, LSEG, 360T, OANDA, CME, central banks, government, websites and internal feeds, all through one governed feed."),
            ("Governance without limits", "Validated and calculated",
             "Validation, anomaly detection, quality and cleansing, schedulers, plus calculations: inversion, triangulation, interpolation, date shifts, averages and your own formula libraries."),
            ("Open data models", "Any data class",
             "Credit risk, security master, ESG, climate and social; any data class the treasury needs, beyond rates alone."),
            ("Target system agnostic", "SAP and non-SAP",
             "Push or pull over API, OData, SFTP, files or e-mail; out of the box for SAP ECC and S/4HANA, no coding."),
        ]))
        + web_band("How it compares", web_table(
            ["", "Market Data Hub", "SAP-native Datafeed", "Custom script"],
            [("Setup", ["No-code configuration", "ABAP function lists and translation tables", "Bespoke code per provider"]),
             ("Add or swap a source", ["Configuration change", "New function list and mapping", "New script"]),
             ("Multiple sources", ["One normalized pipe, many sources", "Configured per provider", "One interface per provider"]),
             ("Governance", ["Audit trail, segregation of duties, exception alerts built in", "Manual or custom", "None unless coded"]),
             ("Who maintains it", ["Managed product on your SAP landscape", "In-house ABAP", "Whoever wrote it"]),
             ("When a source changes a field", ["Absorbed in configuration", "ABAP edit needed", "The script breaks"]),
             ("SAP-listed", ["Yes, on the SAP Store", "Native to SAP", "Not applicable"])],
            note="Honest comparison. The SAP-native Datafeed is a real, supported path; the point of a hub is the no-code, multi-source, governed layer over it, not a claim that SAP cannot do this."),
            h2="The hub versus the two usual paths")
        + web_band("What it retires", dark_band("What it <span>retires</span>", [
            "Per-provider upload scripts, maintained by hand and understood by one person",
            "Rates re-keyed into spreadsheets before they ever reach SAP",
            "Point-to-point integrations that break when a feed changes a field",
            "ABAP upkeep for every new or changed source"]), alt=True)
        + web_band("Works with", web_chips([
            ("", "bloomberg"), ("", "lseg"), ("", "ice"), ("", "cme"),
            ("&rarr;", None), ("SAP TRM", None), ("Market Rates Management", None), ("SAP ECC / S/4HANA", None), ("non-SAP", None)]),
            h2="Every source in, SAP and non-SAP out",
            lede="Beyond the logos above, the hub also handles 360T, OANDA, central banks, government agencies, public websites and internal feeds. Switching or adding a source is a configuration change, not a new interface, so there is no per-source rebuild to maintain.")
        + web_band("Common questions", web_faq([
            ("How do I get Bloomberg market data into SAP TRM automatically?",
             "The SAP-native path is a Datafeed RFC connection with per-provider function lists and translation tables, or a per-security custom interface, both of which need ABAP upkeep and break when Bloomberg changes a field. A governed market-data hub ingests Bloomberg once, normalizes it, and distributes into SAP TRM with an audit trail and exception alerts, no code."),
            ("How do I load LSEG rates and curves into SAP S/4HANA treasury?",
             "LSEG rates and curves reach SAP S/4HANA treasury through the same governed hub that handles any source: integrate the feed once, transform it, distribute into Market Rates Management. Switching or adding a source is a configuration change, not a new interface, so there is no per-source rebuild to maintain."),
            ("Can I automate FX rates and yield curves into SAP Market Rates Management without ABAP?",
             "Yes. SAP's native route uses a Datafeed RFC with function lists and translation tables, which needs ABAP to set up and maintain. A no-code market-data hub maps and schedules FX rates and yield curves into SAP Market Rates Management through configuration, so the treasury team owns the feed without writing or changing ABAP."),
            ("What is the alternative to a custom Bloomberg-to-SAP script that keeps breaking?",
             "A custom script breaks whenever the source changes a field or the person who wrote it leaves. A managed market-data hub replaces it with a configured, monitored interface: source changes are absorbed in configuration, the feed is governed with an audit trail and exception alerts, and nobody is babysitting a brittle script."),
            ("How do I feed OANDA or central-bank rates into SAP cash management?",
             "OANDA and central-bank rates feed into SAP cash management through the same hub as every other source. Multiple sources land in one normalized pipeline rather than separate point interfaces, so the rates that drive cash and liquidity views come from one governed feed with a single point of control."),
            ("How do I govern multiple market-data sources into SAP from one place?",
             "A market-data hub is the single point of control for every source feeding SAP: Bloomberg, LSEG, OANDA, 360T, central banks. It validates, normalizes and distributes each feed, with an audit trail, segregation of duties, and manage-by-exception alerts. Governance is built into the feed, not bolted on per interface afterwards."),
            ("What is the best way to handle market-data integration during an S/4HANA migration?",
             "A migration forces every treasury data feed to be re-plumbed, which is when hand-built market-data interfaces are most expensive to rebuild. Moving the feeds onto a governed hub during the migration re-platforms them once onto a managed interface instead of re-coding each script. In a read of US SAP-treasury job ads, 34% sat inside an active migration."),
            ("Is there a no-code alternative to SAP TRM datafeed configuration?",
             "The SAP TRM Datafeed needs ABAP-side setup of function lists and translation tables per provider. The alternative is a no-code hub that handles integrate, transform and distribute through configuration, aimed at treasury teams that do not have the ABAP capacity to build and maintain the datafeed themselves."),
        ]), alt=True)
        + web_band("Where the truth lives",
                   '<p class="wlede" style="margin:0;">Market Data Hub is a live application on the OnePilot platform, listed on the SAP Store. Brisken is an SAP Co-Innovation Partner, certified to ISO 27001 and SOC 1 Type II. OnePilot runs on SAP\'s own cloud, inside your landscape; your book of records stays in SAP. The market-data truth lives in the hub; SAP, your book of records, is one of its many consumers.</p>')
    )


def web_body_smart_trading(p):
    return (
        web_hero(
            p, "Autonomous trading", 'Brisken <span class="ac">Smart Trading</span>',
            "Autonomous trading, from the venue to booked in SAP.",
            ["Autonomous trading means the trade carries itself from the decision to the booked deal, with no manual re-keying.",
             "Provable by design: rule-based execution at the best bid, competitive bids recorded, every step on a 360° audit trail.",
             "Any instrument, any venue, any system: FX spot and forward, swaps, NDFs, derivatives, money market and securities.",
             "The trading space: your team and its Digital Co-Workers run it together; people stay in charge."],
            vis_smart_trading(),
            rename="Formerly Trade Automation / TraderPlus. Now Brisken Smart Trading (BST).")
        + web_band("Pain and answer", web_cards([
            ("The manual middle", "Straight-through, no-touch",
             "A trade is re-keyed between venue and SAP; a manual FX run takes 10 to 15 minutes a trade. BST carries exposure in SAP to a booked deal in TRM with zero re-keying, approvals under your rules, four-eyes on execution."),
            ("Unprovable execution", "Provable by design",
             "Policy and the FX Global Code expect evidenced best execution. BST executes rule-based at the best bid, records competitive bids, matches confirmations, and logs every step on a 360° audit trail."),
            ("Fragmented landscape", "Any instrument, any venue, any system",
             "FX spot and forward, swaps, NDFs, derivatives and options, money market, investments and securities; 360T, FXall, Bloomberg FXGO, Citi Pulse, BidFX, banks, brokers and exchanges; any OMS or TMS; out of the box for SAP, no coding."),
        ]), h2="Best execution, provable, from the venue to booked in SAP")
        + web_band("The central status monitor",
                   web_flow(["Request", "Execute", "Match", "Book", "Monitor"])
                   + '<p class="wlede" style="margin-top:22px;margin-bottom:0;">Every step in one place: request, order, merge, split, fill, match, booking and confirmation, with the integration log and anomaly alerts alongside. Exposure in SAP becomes a request, execution happens at the best bid, confirmations are matched, and the deal is booked in SAP TRM straight through. You see the trade mid-flight, not after it breaks.</p>',
                   h2="You see the trade mid-flight, not after it breaks", alt=True)
        + web_band("The trading space", web_callout(
            "Your team and its Digital Co-Workers run BST together.",
            "The trading space is where people and the Digital Co-Worker run BST side by side. The Co-Worker suggests trades, watches every run, alerts, fixes and configures; people stay in charge. The Digital Co-Worker is a feature of OnePilot, not a separate product."))
        + web_band("Built in", dark_band("Built <span>in</span>", [
            "Four-eye approval and segregation of duties, as standard",
            "No ABAP and no per-venue interface to maintain",
            "Straight-through booking, so the manual re-key is gone"], mark="+"))
        + web_band("Works with", web_chips([
            ("FXall", None), ("Bloomberg FXGO", None), ("360T", None), ("BidFX", None), ("Citi Pulse", None),
            ("&rarr;", None), ("SAP TRM", None)]),
            h2="Any venue in, SAP TRM out",
            lede="Executed at 360T, FXall, Bloomberg FXGO, Citi Pulse, BidFX, banks, brokers and exchanges, then booked in SAP TRM. It is instrument, venue and TMS agnostic, so a new venue is a configuration change, and the deal flows into SAP Treasury and Risk Management reconciled to source.", alt=True)
        + web_band("Common questions", web_faq([
            ("What is Brisken Smart Trading (BST)?",
             "BST is an application on the OnePilot platform: autonomous best-bid execution across any instrument, from the venue to booked in SAP. It carries exposure in SAP to a booked deal in TRM with no re-keying, records competitive bids, and logs every action under four-eye control."),
            ("How is a trade booked without re-keying it into SAP?",
             "The trade is executed at the venue and booked in SAP TRM straight through, validated on the way in. Because it is instrument, venue and TMS agnostic, adding a new venue is a configuration change rather than a rebuild."),
            ("Is the execution auditable for the FX Global Code?",
             "Yes. Execution is rule-based at the best bid, competitive bids are recorded, confirmations are matched, and every step sits on a 360° audit trail, so best execution is evidenced rather than asserted."),
        ]))
        + web_band("Proof", '<p class="wlede" style="margin:0;">Listed on the SAP Store as Trade Automation. Brisken is an SAP Co-Innovation Partner, certified to ISO 27001 and SOC 1 Type II. Decided once, dealt at the best bid, booked without a touch.</p>', alt=True)
    )


def web_body_remittance(p):
    return (
        web_hero(
            p, "Remittance processing", 'Remittance <span class="ac">Advice Gate</span>',
            "A gate in front of your clearing engine. It makes sure what reaches the engine is worth clearing.",
            ["A remittance advice is the note a payer sends listing which invoices a payment covers. The Gate turns it into data your clearing system can actually use.",
             "It sits in front of your clearing engine, not instead of it. We do not match and we do not clear.",
             "Deterministic where the format is known; the Digital Co-Worker reads what no rule anticipated and shows the evidence.",
             "A correction made once becomes memory and context; the provider's model is never trained on your data."],
            vis_remittance())
        + web_band("The boundary", web_callout(
            "It enriches the advice; it never matches an item and never clears one.",
            "The Gate sits in front of your clearing engine, not instead of it. We make sure what reaches the engine is worth clearing, then hand over to SAP S/4HANA or your cash-application processor, whether that is Serrala, HighRadius or another. Cash application by eye is the problem; the Gate removes the retype in front of it, not the engine behind it."),
            h2="We do not match and we do not clear")
        + web_band("How it works", web_steps([
            ("1", "Parse", "Deterministic where the format is known: EDI 820, IDoc, camt.054, XML, CSV, fixed-width."),
            ("2", "Normalise", "Every layout mapped into one shape, whatever shape it arrived in."),
            ("3", "Clean and check", "Amounts footed, references resolved, short-pays and deductions read out."),
            ("4", "Hand over", "The result goes to your clearing engine, worth clearing, with the evidence attached."),
        ], cols=4), h2="Determinism where it works, intelligence where it doesn't",
            lede="Rules handle the formats a rule can anticipate. For everything else, the Digital Co-Worker reads what no rule anticipated, any layout, scans, screenshots, infers the reference, shows the evidence, explains short-pays and learns the payer.")
        + web_band("Three doors out", web_cards([
            ("Door 1", "Ready to process",
             "Clean and complete, straight to your clearing engine, no one touches it."),
            ("Door 2", "Enriched, with a confidence label",
             "The Co-Worker filled the gaps, and hands over the evidence and a confidence label alongside the data."),
            ("Door 3", "On a person's list",
             "Below the confidence threshold or above your value limit, with the proposed answer and the reasoning, for a person to decide."),
        ]), h2="Every advice leaves by one of three doors", alt=True)
        + web_band("Why a person still does it by hand", web_dots2([
            "No reference", "Wrong reference", "Buried in narrative", "Locale and language",
            "Unreadable by design", "Split across pages", "Duplicates", "Multi-invoice",
            "One advice, many payments", "Out of sequence", "Partial payment", "Deductions and short-pay",
            "Credit notes and rebates", "Amounts that don't foot", "Currency missing", "Group and third-party payers"]),
            h2="Sixteen ways an advice arrives unusable, and every one is a person filling in the blanks by hand")
        + web_band("The remittance space", web_callout(
            "Your team and its Digital Co-Workers run the Gate together.",
            "The remittance space is where people and the Digital Co-Worker work the advices side by side: the Co-Worker reads, infers and explains; a person decides the ones that carry judgment. The Digital Co-Worker is a feature of OnePilot, not a separate product."), alt=True)
        + web_band("How it compares", web_table(
            ["", "Remittance Advice Gate", "Manual cash application", "Rules / template OCR"],
            [("Reads unstructured email and PDF", ["The Co-Worker reads it, no fixed template", "A person reads and keys", "Works only on known layouts"]),
             ("A new remittance format", ["Handled, the Co-Worker reads it and learns the payer", "Staff adapt by hand", "A new template rule is needed"]),
             ("Output", ["Enriched and handed to your clearing engine", "Hand-keyed", "Structured, if the template matched"]),
             ("Matching and clearing", ["Left to your engine, never done here", "A person does it by eye", "A person does it by eye"]),
             ("Effort per advice", ["Review the exceptions only", "Full retype each time", "Fix the unmatched ones"])],
            note="Honest comparison. Manual cash application and template-based capture are both real, working approaches; the Gate's difference is reading unstructured input directly and learning the payer, not a claim that the alternatives do nothing."),
            h2="The gate versus the two usual paths")
        + web_band("Works with", web_chips([
            ("Email", None), ("PDF", None), ("Scanned advice", None), ("EDI 820", None), ("camt.054", None),
            ("&rarr;", None), ("SAP S/4HANA", None), ("Serrala", None), ("HighRadius", None)]),
            h2="Any remittance format in, your clearing engine out", alt=True)
        + web_band("Learning",
                   '<p class="wlede" style="margin:0;">A correction made once becomes memory and context, so the next advice of the same shape arrives worked out rather than re-solved. The provider\'s model is never trained on your data. Coverage improves through experience, not by retraining a model on what you sent.</p>',
                   h2="A correction becomes memory, not training data")
        + web_band("Common questions", web_faq([
            ("How do I turn unstructured remittance advice emails into data my clearing engine can use?",
             "Remittance advice arrives as unstructured email and PDF, which staff retype before anything can clear. The Gate reads the unstructured input, structures it (payer, invoices, amounts, deductions), enriches it and hands it to your clearing engine worth clearing. It sits in front of the engine; it does not match and does not clear."),
            ("Does the Gate post into SAP and clear the items itself?",
             "No. The Gate enriches the advice and hands over to SAP S/4HANA or your cash-application processor. Matching and clearing stay in your engine. The Gate makes sure what reaches the engine is worth clearing; it never matches an item and never clears one."),
            ("Can it read remittance PDFs and scans, or only structured files?",
             "Yes. Where the format is known it parses deterministically (EDI 820, IDoc, camt.054, XML, CSV, fixed-width). For everything else the Digital Co-Worker reads any layout, including scans and screenshots, infers the reference and shows the evidence."),
            ("What happens when a new remittance format shows up?",
             "The Digital Co-Worker reads it and learns the payer, so the next one arrives worked out. A correction made once becomes memory and context; the provider's model is never trained on your data, and no new template rule is needed."),
            ("Does it work with Serrala or HighRadius?",
             "Yes. The Gate hands the enriched, checked advice to SAP S/4HANA or to a cash-application processor such as Serrala or HighRadius. It sits upstream as the step that turns unstructured remittances into input worth clearing."),
        ]), alt=True)
        + web_band("In production",
                   '<p class="wlede" style="margin:0;">Already in production: a live agricultural-sector customer runs the Gate on S/4HANA Private Cloud. The Gate enriches the advice and hands it over; a person still owns the exceptions.</p>')
    )


def web_body_bank_fee(p):
    # 2026-07-21 Dirk review, verbatim: "we do not do the analysis itself, we
    # could, but we do not"; a comparative-analysis claim would need us to read
    # the bank statements too and pair the portal with the SAP Bank Fee Analyzer.
    # Every claim below is one of REF s23's four Application Features (reads any
    # format / validates and enriches to calculate derived fees / sends to a Bank
    # Fee Analyzer, TMS or analytics / one dashboard for on-demand analysis),
    # sourced via deliverables/tc-overview-redesign/CHANGELOG-substance-pass.md
    # S29. The charged-vs-agreed comparison is attributed to the analyzer
    # throughout, never to the portal.
    return (
        web_hero(
            p, "Bank fee statements &middot; UC-04 &middot; Use case &middot; POC", 'Bank <span class="ac">Fee Portal</span>',
            "Every bank's fee statement, whatever format it arrives in, turned into data your fee analyzer can actually read.",
            ["Reads every bank fee statement format: CAMT.086, XML, TWIST BSB and each bank's own layout.",
             "Validates each statement and enriches it, calculating the derived fees that are hard to catch by hand.",
             "Delivers the structured result to your Bank Fee Analyzer, your TMS or your analytics.",
             "A use case on OnePilot; inside TreasuryCentral your team and its Digital Co-Workers run it.",
             "One dashboard for on-demand analysis across every account and every bank. At proof-of-concept stage today."],
            vis_bank_fee())
        + web_band("The problem",
                   '<p class="wlede">Bank fee statements arrive in four shapes: the older TWIST BSB format, the ISO 20022 CAMT.086 that is replacing it, plain XML, and each bank\'s own proprietary layout. SAP added native bank-fee analysis in S/4HANA 1809, but it expects clean CAMT.086 in. The statements that arrive in any other format never reach the analyzer, so the fees on them never get reviewed.</p>'
                   '<p class="wlede" style="margin-bottom:0;">Derived fees make it harder still: the charge that has to be calculated out of the file rather than read off it is the one a person checking by hand misses. The Bank Fee Portal sits in front, accepts every format, validates and enriches each statement, and delivers the result into the analyzer, so the fee review covers every bank rather than only the ones that happen to send clean files.</p>',
                   h2="Getting every bank's statement into the fee review")
        + web_band("Where we stop",
                   '<p class="wlede" style="margin-bottom:0;">Brisken reads the fee statements, validates them, calculates the derived fees and hands over the structured result. Comparing what a bank charged against what you negotiated runs in SAP\'s Bank Fee Analyzer, or in whichever TMS or analytics tool you already own; that comparison also needs your bank statements alongside the fee statements. The portal is what gets every bank into it, including the ones whose format never made it in before.</p>',
                   h2="The portal prepares the data; the analyzer runs the comparison", alt=True)
        + web_band("How it works", web_steps([
            ("1", "Read", "Every fee statement, from every account, in CAMT.086, XML, TWIST BSB or the bank's own layout."),
            ("2", "Validate and enrich", "Each statement is checked and enriched, with the derived fees calculated rather than left buried in the file."),
            ("3", "Deliver", "The structured result goes to your Bank Fee Analyzer, TMS or analytics, plus a dashboard for on-demand analysis."),
        ]), h2="Every statement in, one structure out",
            lede="Configured once per bank, the ingest then runs on its own.")
        + web_band("How it compares", web_table(
            ["", "Bank Fee Portal in front of the analyzer", "The analyzer alone", "Manual / spreadsheet"],
            [("Input formats accepted", ["CAMT.086, XML, TWIST BSB, proprietary, normalized in", "Clean CAMT.086", "Whatever a person can open"]),
             ("Off-format statements", ["Parsed and delivered into the analysis", "Stall outside the app", "Re-keyed by hand, if at all"]),
             ("Derived fees", ["Calculated during enrichment", "Only what the file already states", "Easy to miss by hand"]),
             ("Who runs the comparison", ["Your Bank Fee Analyzer, TMS or analytics", "The same analyzer, on fewer banks", "A person, on spot-checks"]),
             ("Banks reaching the review", ["Every bank that sends a statement", "Only banks already on CAMT.086", "Whatever got opened in time"]),
             ("Effort per cycle", ["Ingest is configured once, runs on its own", "Manual conversion for off-format banks", "Hours of clerical work each run"])],
            note="The portal sits in front of the fee analysis; it does not replace it and does not perform it. The analyzer is capable once the data is in. The portal's job is getting every bank's statement, in any format, into it."),
            h2="The portal versus the two usual paths", alt=True)
        + web_band("What it puts in reach", dark_band("What it <span>puts in reach</span>", [
            "The banks whose statement format never reached the fee review before",
            "Derived fees calculated during enrichment, instead of left buried in the file",
            "One dashboard across every account, instead of fee data scattered across statements"], mark="+"))
        + web_band("Why format matters",
                   web_callout("A statement you cannot load is a bank you cannot review.",
                               "The bank that sends a proprietary file is the bank whose fees go unchecked, however good the analyzer is. Getting that statement in, structured and enriched, is what puts it in front of the analysis at all. The portal accepts every format, so no bank is left out on a technicality."), alt=True)
        + web_band("Built on the standard",
                   '<p class="wlede" style="margin-bottom:0;">CAMT.086 is the ISO 20022 bank-fee-statement format that replaces the older TWIST BSB. SAP added native bank-fee analysis in S/4HANA release 1809, delivered as a Fiori app that compares charged fees against expected ones, but it reads clean CAMT.086 only. Banks have not standardized on it; many still send TWIST BSB, plain XML or a proprietary layout, and those are exactly the statements the portal exists to normalize and bring in.</p>',
                   h2="Where SAP's native analysis stops")
        + web_band("Works with", web_chips([
            ("CAMT.086 (ISO 20022)", None), ("XML", None), ("TWIST BSB", None), ("Proprietary formats", None),
            ("&rarr;", None), ("SAP Bank Fee Analyzer", None), ("Any TMS", None), ("Analytics", None)]),
            h2="Any statement format in, one structure out", alt=True)
        + web_band("Common questions", web_faq([
            ("Does the Bank Fee Portal compare charged fees against my agreement?",
             "No. That comparison runs in SAP's Bank Fee Analyzer, or in the TMS or analytics tool you already use, and it needs your bank statements alongside the fee statements. The portal reads every bank's fee statement in any format, validates it, calculates the derived fees and delivers the structured result into that tool. Paired with an analyzer, it is what lets the comparison cover every bank instead of only the ones sending clean CAMT.086."),
            ("How do I automate CAMT.086 bank fee statement analysis in SAP?",
             "CAMT.086 is the ISO 20022 bank-fee-statement format that replaces TWIST BSB. SAP added native bank-fee analysis in S/4HANA 1809 via a Fiori app, but it expects clean CAMT.086 in; banks still send XML, TWIST and proprietary formats. A bank-fee portal reads any format, validates and enriches it, and distributes it to the analyzer, so the fee review is not gated on format."),
            ("How do I process TWIST BSB or proprietary bank fee statements into SAP?",
             "Banks issue fee statements in TWIST BSB, the older industry format, in CAMT.086, in plain XML, and in their own proprietary layouts. SAP's native analysis expects CAMT.086, so the off-format statements stall. A format-agnostic portal parses them, normalizes them to the structure the analyzer reads, and delivers them in, so no bank is left out of the review."),
            ("What are derived fees, and why do they get missed?",
             "A derived fee is one you have to calculate out of the statement rather than read off it, for example a margin or a volume-tiered charge implied by the underlying figures. A person checking a statement by hand sees the stated lines and misses the implied ones. The portal calculates them during enrichment, so they arrive at the analyzer as data rather than staying buried in the file."),
        ]))
    )


def web_body_treasurycentral(p):
    return (
        web_hero(
            p, "The treasury workspace", 'Treasury<span class="ac">Central</span>',
            "The workspace where your team and its Digital Co-Workers run treasury, grounded in SAP.",
            ["The workspace where your team and its Digital Co-Workers run treasury, on the OnePilot platform, grounded in SAP.",
             "What it replaces: a dozen point tools, and the hand-keying between your systems and SAP.",
             "Who it is for: treasury and finance teams on SAP.",
             "Brisken's main product, and a single treasury use case of OnePilot. Both are true."],
            vis_treasurycentral(), bare=True)
        + web_band("The problem",
                   '<p class="wlede">A treasurer\'s day goes into the gaps between systems: grey-scale processing through endless SAP GUIs, and data parsed by hand out of one system and into the next process step. Around those gaps sit brittle, hand-built feeds that break when a field changes or the person who built them leaves, with no audit trail, no owner and no monitoring.</p>'
                   '<p class="wlede" style="margin-bottom:0;">TreasuryCentral closes the gaps. It is the workspace where your team and its Digital Co-Workers run treasury together, and its value is bringing the business context for treasury into one place. Underneath it, OnePilot connects every source, counterparty and enterprise system, so the context a decision needs is already in the room instead of three screens away.</p>',
                   h2="The treasurer's day on one surface")
        + web_band("The Digital Co-Worker", web_cards([
            ("A feature of OnePilot", "The agent inside a space",
             "The Digital Co-Worker is the agent that works with your team inside a dedicated space: it drives the solution, watches every run, fixes what breaks, and brings you the decisions. It is a feature of OnePilot, never a product of its own."),
            ("Division of labor", "The work splits three ways",
             "The solution executes the deterministic steps, the same result every time. The Co-Worker drives every step across your systems. You keep the judgment."),
            ("An agentic team", "Roles, not one bot",
             "Specialised agents with roles: Domain Specialists, Analysts, Clerks and Personal Assistants, each briefed for its part of the work."),
        ]), h2="Your team, and its Digital Co-Workers", alt=True)
        + web_band("The Spaces", web_callout(
            "A colleague, not a black box.",
            "Every app and use case has a space; your team and its Digital Co-Workers run it together: chat, alerts, fixes, orchestration. The Co-Worker monitors every run where a human would, raises and records alerts, fixes data issues, and hands you the exceptions. Nothing fails in silence, and people stay in charge."))
        + web_band("The architecture", tc_architecture(),
                   h2="There is no outside",
                   lede="Describing OnePilot as connecting to outside systems is a technical view, and the wrong one for how treasury actually works. Every source, counterparty and enterprise system sits inside the governed platform, and the workspace is where you meet them. What goes away: grey-scale processing through endless SAP GUIs, and manual data parsing between systems and process steps.")
        + web_band("Governance", web_cards([
            ("", "Bounded autonomy", "Acts only within the permissions and limits you set."),
            ("", "Human authority", "A person owns the moves that matter, and can review, override or stop."),
            ("", "Four-eyes, segregation of duties", "Whatever initiates a step never approves it."),
            ("", "Robust and fail-safe", "Tested before it runs, behaves predictably, safe-stops or rolls back on error."),
            ("", "Traceable and explainable", "Every action and data change logged: who, what, when, why, and explainable."),
            ("", "Monitored, managed by exception", "Outputs watched in real time; anomalies go to a person, the rest just runs."),
        ]), h2="Six controls across the workspace and every app",
            lede="Governed to EU AI Act principles, on a 360° audit trail, certified to ISO 27001 and SOC 1 Type II. It runs on the SAP data you already trust, with no separate store to reconcile, and a person approves the moves that matter.", alt=True)
        + web_band("Common questions", web_faq([
            ("What is TreasuryCentral?",
             "TreasuryCentral is the workspace where your team and its Digital Co-Workers run treasury. It brings the business context for treasury into one place, the whole day on one surface, on the OnePilot platform and grounded in SAP. It is Brisken's main product."),
            ("How does TreasuryCentral relate to OnePilot?",
             "Technically all of it is OnePilot. TreasuryCentral is a treasury-centric use case of the platform, and the apps inside it are OnePilot applications wrapped into a treasury value proposition. OnePilot is not a layer the workspace sits on top of and calls out from; it is the environment everything runs inside, which is why a counterparty and an enterprise system are reached the same governed way."),
            ("Which applications and use cases run inside it?",
             "Two applications, Market Data Hub and Brisken Smart Trading, plus the use cases: Intercompany Funding Request, Remittance Advice Gate, Cash Flow and Exposure Hub, Bank Fee Portal, Bank Statement Generator, Credit Data Hub and ESG Data Hub, and the use cases your own team builds as apps on OnePilot."),
            ("Can our own team build use cases in it?",
             "Yes, and it is the point. Customers build their own use cases into solid apps in the workspace, on OnePilot, using the same connectivity, governance and audit trail as the applications we deliver."),
            ("Does it need a separate data store?",
             "No. It works on the SAP data you already trust, so there is no separate store to reconcile. Every move is logged, and every action stays inside your controls."),
        ]))
    )


def web_body_onepilot(p):
    return (
        web_hero(
            p, "The platform", 'One<span class="ac">Pilot</span>',
            "The platform underneath everything: Connect, Orchestrate, Govern.",
            ["One platform for everything between your systems and SAP. Not limited to treasury.",
             "TreasuryCentral, powered by OnePilot, is its one shipped edition and Brisken's main product.",
             "The Digital Co-Worker, a feature of OnePilot, runs each task with full context; people stay in charge.",
             "The book of record stays in SAP; OnePilot orchestrates on top, SAP and non-SAP, both ways."],
            vis_onepilot(), bare=True)
        + web_band("The problem",
                   '<p class="wlede">A treasurer\'s day becomes tab management: the trading platform in one window, market data in another, bank portals and cash tools in others, and the numbers re-keyed between them. The day goes to moving data instead of using it. Around SAP, that shows up as shadow integrations, hand-keyed files and home-built scripts that move data in, fragile and unowned, plus a backlog of interfaces to build and maintain.</p>'
                   '<p class="wlede" style="margin-bottom:0;">OnePilot puts the data in one governed place, so the day shifts back to using it: deciding, not re-typing. It is a no-code platform over your SAP landscape where your team and its Digital Co-Workers do the repetitive work, ingesting, validating, posting and reconciling, always inside your controls. The book of record stays in SAP; OnePilot orchestrates on top.</p>',
                   h2="Why a treasurer's day becomes tab management")
        + web_band("The market", web_stats([
            ("71%", "of US SAP-treasury roles describe building or hand-running integrations into SAP, or manual data work (29 of 41)."),
            ("34%", "are tied to an active S/4HANA migration or SAP implementation, the moment feeds get re-plumbed (14 of 41)."),
            ("22%", "name a specific market-data or trading vendor whose feed has to reach SAP, and that is a floor (9 of 41)."),
        ], "Source: Brisken Shadow Integration Report, N=41 US SAP-treasury job ads, read 2026-06-17. These are market-research figures, not an OnePilot performance metric."),
            h2="The shadow integration is the default state, not the exception", alt=True)
        + web_band("The platform", web_steps([
            ("1", "Connect", "Every system, in and out: banks, market data, ERP, portals."),
            ("2", "Orchestrate", "The Digital Co-Worker runs each task with full context, at scale."),
            ("3", "Govern", "Audit, segregation of duties, anomaly alerts, person-in-the-loop."),
        ], cols=3), h2="Connect, Orchestrate, Govern",
            lede="The Digital Co-Worker learns your systems and recommends each mapping; you approve it, and the task runs governed end to end, SAP and non-SAP, both ways. Configured, not coded, so a new feed goes live in weeks rather than a multi-quarter build your team then owns.")
        + web_band("The Digital Co-Worker", web_cards([
            ("A feature of OnePilot", "The agent inside a space",
             "The Digital Co-Worker drives the solution, watches every run, fixes what breaks, and brings you the decisions. It is a feature of OnePilot, never a product of its own, and never sold standalone."),
            ("An agentic team", "Roles, not one bot",
             "Specialised agents with roles: Domain Specialists, Analysts, Clerks and Personal Assistants, each briefed for its part of the work."),
            ("The Spaces", "Run it together",
             "Every app and use case has a space where your team and its Digital Co-Workers run it together: chat, alerts, fixes, orchestration. A colleague, not a black box."),
        ]))
        + web_band("Governance", web_cards([
            ("", "Bounded autonomy", "Acts only within the permissions and limits you set."),
            ("", "Human authority", "A person owns the moves that matter, and can review, override or stop."),
            ("", "Four-eyes, segregation of duties", "Whatever initiates a step never approves it."),
            ("", "Robust and fail-safe", "Tested before it runs, behaves predictably, safe-stops or rolls back on error."),
            ("", "Traceable and explainable", "Every action and data change logged: who, what, when, why, and explainable."),
            ("", "Monitored, managed by exception", "Outputs watched in real time; anomalies go to a person, the rest just runs."),
        ]), h2="Six controls on every record",
            lede="Governed to EU AI Act principles, on a 360° audit trail, certified to ISO 27001 and SOC 1 Type II. A person approves the moves that matter.", alt=True)
        + web_band("How it connects", web_chips([
            ("RFC & OData", None), ("SFTP", None), ("SOAP & REST", None), ("AMQP", None),
            ("Email", None), ("Excel add-in", None), ("XLSX / CSV / TXT", None), ("Web scraping", None), ("LLM & browser automation", None)])
            + '<p class="wlede" style="margin-top:22px;margin-bottom:0;">Push and pull, off-the-shelf, third-party-managed and low-maintenance. Sources on one side (Bloomberg, LSEG, 360T, OANDA, central banks, banks, files and email) and SAP on the other (S/4HANA, TRM, Cash and Credit Management), with non-SAP systems in the same governed perimeter. A new feed is set up on a managed product, so it goes live in weeks rather than a multi-quarter integration project your team has to build and then own.</p>',
            h2="Connects to what you already run")
        + web_band("The modules", web_table(
            ["Module", "Type", "Status", "Problem it removes"],
            [("Market Data Hub", ["APP", "LIVE", "Rates and prices arrive from a dozen places; nobody owns the number."]),
             ("Brisken Smart Trading", ["APP", "LIVE", "A trade is re-keyed between venue and SAP; best execution unprovable."]),
             ("Intercompany Funding Request", ["UC", "LIVE", "Funding between entities runs on emails and hand-keyed bookings."]),
             ("Remittance Advice Gate", ["UC", "LIVE", "Payments land, but which invoices do they clear? Cash application by eye."]),
             ("Cash Flow &amp; Exposure Hub", ["UC", "LIVE", "Exposure data sits scattered across entities; the hedge is always late."]),
             ("Bank Fee Portal", ["UC", "POC", "Bank charges get paid unchecked against what was actually agreed."]),
             ("Bank Statement Generator", ["UC", "LIVE", "Statements are hand-built to each bank's format, every single day."]),
             ("Credit Data Hub", ["UC", "LIVE", "Counterparty risk is spread across agencies and never quite current."]),
             ("ESG Data Hub", ["UC", "POC", "ESG metrics are fragmented across providers when reporting falls due."])],
            note="Two applications, built once and maintained by Brisken; the rest are use cases, assembled from the same kit and owned by you. Your problem isn't on the list? That's the next one."),
            h2="Two applications, seven use cases, and the ones you build", alt=True)
        + web_band("In production", web_cards([
            ("Financial services", "S/4HANA Public Cloud", "A financial-services group already governs several data domains from one OnePilot deployment."),
            ("Agricultural", "S/4HANA Private Cloud", "Runs the Remittance Advice Gate: the enriched advice is handed to the clearing engine, and a person owns the exceptions."),
            ("Chemicals", "S/4HANA On-Prem", "An intercompany funding-request process across a complex SAP integration, governed; a person approves the moves that matter."),
        ]))
        + web_band("Common questions", web_faq([
            ("Does OnePilot replace SAP?",
             "No. OnePilot orchestrates on top of SAP. The book of record stays in SAP, execution on the trading platform, and market data through the hub. It composes the apps and data your work needs on one surface, without moving the system of record."),
            ("Can we deploy a Digital Co-Worker in treasury without consuming our IT budget?",
             "Yes. OnePilot is configured, not coded, and runs as a managed product on top of your SAP landscape, so there is no ABAP build and nothing new for your IT team to own or maintain. A new feed or Digital Co-Worker is set up on the product and goes live in weeks, which keeps the work off the IT backlog and the cost off the development budget."),
            ("Is AI automation in treasury safe?",
             "It is safe when the AI runs inside your controls rather than around them. Each OnePilot process works to rules you set and approve, with four-eye release, segregation of duties and a full audit trail on every record. You keep command of policy and exceptions; the Digital Co-Worker handles the repetitive steps, and nothing moves outside the rules you define."),
            ("Can AI improve liquidity forecasting?",
             "Yes. A forecast is only as good as the data feeding it, and most of the delay is in collecting and cleaning cash, bank and exposure data by hand. OnePilot keeps that data current and governed in SAP, so the forecast runs on a clean, reconciled base. Treasury still owns the assumptions and the call; the Digital Co-Worker removes the manual data work that slows the forecast down."),
            ("Can AI help the team focus the day on what matters?",
             "Yes. The repetitive work, ingesting feeds, validating, posting and reconciling, runs underneath by exception, so the team sees what needs a decision instead of working through every record. Their day shifts from re-keying and chasing data to judgment, review and the exceptions that actually need a person."),
        ]))
        + web_band("Proof",
                   '<p class="wlede" style="margin:0;">OnePilot is delivered by an SAP Co-Innovation Partner and PartnerEdge member, part of SAP Industry Cloud for Financial Services and Commodities, certified to ISO 27001 and SOC 1 Type II. It runs on SAP\'s own cloud, inside your landscape; your book of records stays in SAP. TreasuryCentral, powered by OnePilot, is its one shipped edition. The Market Data Hub and Brisken Smart Trading are listed on the SAP Store.</p>', alt=True)
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
    # The smart-trading deck is retired: its PDF carried a banned claim
    # ("Evonik and RWZ already build on the platform"). It regenerates later from
    # the deck engine; until then the page links no deck.
    "smart-trading": dict(),
    "remittance-advice-gate": dict(),
    # 2026-07-21 Dirk review: the page claimed the charged-vs-agreed analysis
    # ("we do not do the analysis itself"), carried no call to action, and its
    # PDF said nothing about Brisken. Copy now claims only REF s23's four
    # application features; CTA + letterhead come from the shared layer.
    "bank-fee-portal": dict(
        updated="2026-07-29",
        cta_h="See it running on your fee statements",
        cta_p="Bring the formats your banks actually send; we will show what the portal reads and what it hands to your analyzer."),
    # 2026-07-21 21:30 Dirk review: "the site is a little messy", the diagram
    # needed replacing, and his own V3 render was "still very boring, boxes
    # everywhere". Page now runs his V3 model (workspace inside the OnePilot
    # field, the full app roster, the workstation) with the rosters as text.
    "treasurycentral": dict(
        updated="2026-07-29",
        cta_h="See the workspace running on your SAP",
        cta_p="Bring the systems and counterparties your treasury actually deals with; we will show what moves into the workspace and what stays where it is."),
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


def _print_head(p):
    """Brisken letterhead for the downloaded PDF. Hidden on screen (the sticky
    nav already carries the mark there); heads page 1 of the print render, which
    otherwise opened with no Brisken identity on it at all."""
    return (f'<div class="wprint-head">'
            f'{blogo("plogo")}'
            f'<div class="pright"><span class="pdoc">{p["title"]}</span>'
            f'<span class="psap">SAP</span> Co-Innovation Partner</div></div>')


def page(p):  # print / PDF: bare A4 sheet
    return f'{_head(p)}\n<body>{_sheet(p)}</body></html>'


def page_web(p):  # native web page: full-bleed responsive product page
    short = p["short"]
    pw = {**p, **WEB_META.get(short, {})}
    body = WEB_BODIES[short](pw)
    return f'''{_head(pw, WEB_CSS + LOGO_CSS)}
<body>
<div class="wnav">
  <a class="nl" href="/">
    {blogo("nlogo")}
    <span class="sep">&middot;</span><span class="plabel">{pw['title']}</span>
  </a>
  <div class="nr"><a class="nback" href="/">&larr; All resources</a>
  <a class="ndl" href="/{short}.pdf" download="{dl_name(pw)}">Download PDF</a></div>
</div>
{_print_head(pw)}
{body}
<section class="wproof"><div class="inner">{PROOF}</div></section>
{web_cta_band(pw)}
{web_footer(pw)}
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
    # The Brisken Smart Trading deck is retired here: its served PDF carried a
    # banned claim ("Evonik and RWZ already build on the platform"). It
    # regenerates later from the deck engine; the smart-trading page links no
    # deck in the meantime.
    dict(short="digital-co-worker", pdf="digital-co-worker", pages=11,
         title="Digital Co-Worker deck", h1="Digital Co-Worker",
         accent="#9333ea", accent2="#c084fc", glow="rgba(147,51,234,.30)",
         promise="A feature of OnePilot: your team and its Digital Co-Workers run each app together, inside a dedicated space.",
         points=["The solution executes the deterministic steps; the Co-Worker drives every step across your systems; you keep the judgment",
                 "An agentic team: Domain Specialists, Analysts, Clerks and Personal Assistants, each briefed for its part",
                 "A colleague who watches every run, raises alerts, fixes data issues, and hands you the exceptions"],
         lede="Eleven pages: the Digital Co-Worker as a feature of OnePilot, the agentic team behind "
              "it, the Spaces where your people and their Co-Workers work together, and the governance "
              "that keeps a person on the moves that matter."),
]


def page_deck(d):
    pts = "".join(f"<li>{x}</li>" for x in d["points"])
    pdf = f'/{d["pdf"]}.pdf'
    return f'''{_head(d, WEB_CSS + DECK_CSS + LOGO_CSS)}
<body>
<div class="wnav">
  <a class="nl" href="/">
    {blogo("nlogo")}
    <span class="sep">&middot;</span><span class="plabel">{d['title']}</span>
  </a>
  <div class="nr"><a class="nback" href="/">&larr; All resources</a>
  <a class="ndl" href="{pdf}" download="{dl_name(d)}">Download PDF</a></div>
</div>
{_print_head(d)}
<section class="whero"><div class="inner">
  <div class="hcopy">
    <div class="weyebrow">Full deck &middot; {d['pages']} pages</div>
    <h1>{d['h1']}</h1>
    <p class="wpromise">{d['promise']}</p>
    <ul class="wpoints">{pts}</ul>
    <div class="wcta">
      <a class="wbtn primary" href="{DEMO_URL}">Book a demo &rarr;</a>
      <a class="wbtn ghost" href="{pdf}" download="{dl_name(d)}">Download the deck</a>
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
{web_footer(d)}
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
        # --virtual-time-budget: without it Chrome prints before the Google-Fonts
        # webfonts arrive, so every PDF shipped in Times New Roman + Arial while
        # the site itself rendered in Space Grotesk + IBM Plex Sans. Part of
        # Dirk's 2026-07-21 "nothing says anything about brisken" on the PDF:
        # the download did not even carry the brand typography.
        cmd = [str(CHROME), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
               "--no-first-run", "--no-default-browser-check", "--virtual-time-budget=8000",
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
    ap.add_argument("--only", action="append", metavar="SHORT",
                    help="regenerate only these products/decks by short name (repeatable), "
                         "e.g. --only bank-fee-portal. Leaves every other artefact untouched, "
                         "so a single reviewed page can ship without re-rendering the set.")
    args = ap.parse_args()

    products, decks = PRODUCTS, DECKS
    if args.only:
        wanted = set(args.only)
        known = {p["short"] for p in PRODUCTS} | {d["short"] for d in DECKS}
        unknown = wanted - known
        if unknown:
            sys.exit(f"--only: unknown name(s) {sorted(unknown)}; known: {sorted(known)}")
        products = [p for p in PRODUCTS if p["short"] in wanted]
        decks = [d for d in DECKS if d["short"] in wanted]
        print(f"--only: {sorted(wanted)}")

    # The downloadable PDF is a render of the SAME web page (via its @media print
    # stylesheet), so the download and the site have identical content.
    web = args.web_out.resolve()
    web.mkdir(parents=True, exist_ok=True)
    for p in products:
        (web / f'{p["short"]}.html').write_text(page_web(p), encoding="utf-8")
    print(f"web pages: {len(products)} written -> {web}")

    # The 3 full-deck pages: same nav/hero/band frame as the one-pagers, wrapping
    # the existing deck PDFs (no re-render; the deck PDFs are already built).
    for d in decks:
        (web / f'{d["short"]}.html').write_text(page_deck(d), encoding="utf-8")
    print(f"deck pages: {len(decks)} written -> {web}")

    if args.web_only:
        print("web-only: skipped PDF render")
        return 0

    if not CHROME.is_file():
        sys.exit(f"Chrome not found at {CHROME}; it is the only render engine that works while Edge is open")

    print("PRODUCT | PDF pages | size KB")
    pdfs: list[Path] = []
    for p in products:
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
