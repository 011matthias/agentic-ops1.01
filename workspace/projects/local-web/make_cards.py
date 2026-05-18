# /// script
# requires-python = ">=3.11"
# dependencies = ["segno"]
# ///
"""Generate printable A6 leave-behind cards (QR + short URL) per prospect.

One card = one business. Walk in, hand it over: "Ich habe Ihnen schon eine
neue Website gebaut. Scannen Sie das, dann sehen Sie sie."
Identity/contact line is a placeholder on purpose: it must not be fabricated.
"""
import io, pathlib, segno

BASE = "https://webvorschau-ka.vercel.app"
OUT = pathlib.Path(__file__).parent / "cards"
OUT.mkdir(exist_ok=True)

PROSPECTS = [
    ("praxis-uslu",  "Praxis Dr. med. Sema Uslu", "Ihre neue Praxis-Website"),
    ("coffee-boxx",  "Coffee Boxx",               "Die neue Website für Ihr Café"),
    ("pronto-pronto","Pronto-Pronto",             "Die neue Website für Ihren Lieferservice"),
]

# Identity line: filled from identity.txt if present, else visible placeholder.
idf = pathlib.Path(__file__).parent / "identity.txt"
if idf.exists():
    lines = [l.strip() for l in idf.read_text(encoding="utf-8").splitlines() if l.strip()]
    NAME = lines[0] if lines else "[IHR NAME]"
    CONTACT = lines[1] if len(lines) > 1 else "[IHRE TELEFONNUMMER / E-MAIL]"
else:
    NAME, CONTACT = "[IHR NAME]", "[IHRE TELEFONNUMMER / E-MAIL]"

def qr_svg(url: str) -> str:
    return segno.make(url, error="m").svg_inline(scale=6, border=0, dark="#1c2530")

cards_html = []
for slug, biz, headline in PROSPECTS:
    url = f"{BASE}/{slug}"
    cards_html.append(f"""
  <article class="card">
    <div class="top">
      <div class="kicker">Persönlich für Sie vorbereitet</div>
      <h1>{biz}</h1>
      <p class="head">{headline}</p>
    </div>
    <div class="qr">{qr_svg(url)}</div>
    <p class="scan">Kamera öffnen, QR scannen</p>
    <p class="url">{url.replace("https://","")}</p>
    <div class="foot">
      <span>{NAME}</span>
      <span>{CONTACT}</span>
    </div>
  </article>""")

html = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<title>Leave-behind Karten</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
    background:#eef1f4;color:#1c2530;padding:18px}}
  .sheet{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;max-width:1000px;margin:0 auto}}
  .card{{background:#fff;border:1px solid #d7dde3;border-radius:18px;padding:30px 28px;
    aspect-ratio:1.55/1;display:flex;flex-direction:column;align-items:center;
    text-align:center;box-shadow:0 10px 26px rgba(20,40,60,.08)}}
  .kicker{{text-transform:uppercase;letter-spacing:.16em;font-size:.66rem;font-weight:800;
    color:#2f7d92;margin-bottom:8px}}
  h1{{font-size:1.35rem;font-weight:800;letter-spacing:-.01em}}
  .head{{color:#5d7280;font-size:.92rem;margin-top:4px}}
  .qr{{margin:16px 0 8px}}
  .qr svg{{width:128px;height:128px;display:block}}
  .scan{{font-size:.78rem;color:#5d7280}}
  .url{{font-weight:700;font-size:.9rem;margin-top:4px;color:#1c2530}}
  .foot{{margin-top:auto;padding-top:14px;border-top:1px solid #e6eaee;width:100%;
    display:flex;justify-content:space-between;font-size:.8rem;color:#5d7280;gap:10px}}
  .foot span:first-child{{font-weight:700;color:#1c2530}}
  @media print{{
    body{{background:#fff;padding:0}}
    .sheet{{gap:0}}
    .card{{border:1px dashed #b9c2ca;border-radius:0;box-shadow:none;
      page-break-inside:avoid}}
  }}
</style></head>
<body><div class="sheet">{''.join(cards_html)}</div></body></html>"""

(OUT / "leave-behind-cards.html").write_text(html, encoding="utf-8")
print(f"Wrote {OUT/'leave-behind-cards.html'}")
print(f"Identity: name={NAME!r} contact={CONTACT!r} "
      f"({'from identity.txt' if idf.exists() else 'PLACEHOLDER - create identity.txt'})")
