# Local Web — preemptive demo sites for local businesses

Revenue line: build a high-fidelity demo site for a local business *before*
contacting them, then walk in and introduce myself with the demo already
made. The artifact in hand is the pitch.

## Model

- Build a tasteful, fast, mobile-first **one-site demo** using the
  business's real public data (name, services, hours, address, contact).
- Demo is self-contained HTML — works offline on a laptop, loads instantly,
  no broken external calls during a face-to-face pitch.
- Walk in, show it on a phone/laptop, leave a card with a QR to the live
  preview URL so the owner can show a partner before deciding.
- Close on a low one-time build fee + monthly hosting/edits retainer
  (recurring revenue is the product; the build removes the yes/no friction).

## Status

Validation batch 1 (manual builds, Karlsruhe):

| Prospect | Type | Slug | Demo | Pitched | Outcome |
|----------|------|------|------|---------|---------|
| Dr. med. Sema Uslu | Hausarztpraxis | `praxis-uslu` | built | no | — |
| Pronto-Pronto | Pizza Heimservice | `pronto-pronto` | built | no | — |
| Michael Meinzer Malerfachbetrieb | Handwerk / Maler | `meinzer-maler` | built | no | — |
| Helmle & Helmle | Physiotherapie / Massage | `helmle-physio` | built | no | — |
| Beauty Lounge Karlsruhe | Kosmetik / Nageldesign | `beauty-lounge` | built | no | — |

## Data accuracy (B4)

Every demo uses only data traced to a public source. Per-prospect sources
are listed in each `prospects/{slug}/data.md`. Anything not found is marked
`[BITTE PRÜFEN]` in the demo so the owner fills it, never fabricated.

## Next

1. User review of the 3 demos.
2. Decide hosting (unlisted Vercel path under platform, `noindex`).
3. Generate QR leave-behind cards.
4. Pitch in person; log outcomes in the table above.
5. If conversion validates, automate: scout → scrape → generate → deploy.
