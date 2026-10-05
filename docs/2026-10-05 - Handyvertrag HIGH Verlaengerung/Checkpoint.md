# Checkpoint: Handyvertrag HIGH Verlaengerung

**Date:** 2026-10-05
**Status:** Analysis done, contract filed in iCloud; extend-or-switch decision is the owner's

---

## Summary
Personal session: reviewed the owner's HIGH 75 5G mobile contract (mobilezone, Telekom network, 12,49 €/month) against the October 2026 market, SIM-only and with-iPhone, before the owner answers HIGH's 24-month extension offer. Contract PDFs and a fact sheet now live in iCloud.

---

## What Was Done This Session
### Market research
1. SIM-only 70-100 GB, monthly cancellable: Lebara 100 GB o2 11,99 €, SIMon 80 GB Vodafone 11,99 €, klarmobil 75 GB Vodafone 9,99 € (+19,99 € connection). Telekom-network equivalents are pricier (fraenk 30 GB 10 €; the summer D1 deals at 80 GB/11,99-12,49 € expired in August).
2. Network tests 2026: Telekom wins connect (975 vs 937/937) and is CHIP's only "exzellent".
3. iPhone bundles, 24-month totals vs "extend HIGH + buy phone": iPhone 17 + Telekom 30 GB = 1.293,75 € vs 1.177,65 € (bundle 116 € worse); iPhone 17 Pro + Vodafone unlimited (44,99 €) ≈ 1.209 € vs 1.397,76 € (bundle ≈189 € better, only if the 39,99 € connection refund and 120 € credit are both claimed).
### Contract read (owner-supplied PDFs)
1. 12,49 € = 24,99 € list minus 12,50 € discount; HIGH's site confirms the discount ends at month 25, so doing nothing costs 24,99 €.
2. Cost traps extracted: non-EU roaming 0,59 € per 50 KB (Schweiz, USA, Türkei), ship/plane networks, calls abroad not in the flat, 32 kbit/s after 75 GB, Anschlusspreis 29,90 € refunded only "nach Erstattung".
### Filing
1. Copied both PDFs to iCloud `Personal\Rechnungen\HIGH-Mobilfunk\vertrag\` (SHA-256 matched against the originals) and wrote `_UEBERSICHT.md` in the Advanzia/Stadtmobil style.

---

## Key Decisions Made
### Recommendation given
- **Choice:** Extend HIGH (299,76 € over 24 months) unless the owner wants an iPhone 17 Pro, where the Vodafone bundle wins by ≈189 € at the cost of leaving the Telekom network.
- **Rationale:** No cheaper comparable D1 offer exists today; leaving D1 for o2/Vodafone saves at most ≈32 € over two years.
### Filing home
- **Choice:** `Personal\Rechnungen\HIGH-Mobilfunk\` with `vertrag\` subfolder, originals left in `Desktop\Downloads`.
- **Rationale:** Matches the existing per-provider convention; nothing deleted without an ask.

---

## What Did NOT Work (and why)
- **Answering before seeing the contract:** the first answer led with "ohne Verlängerung läuft der Vertrag zum selben Preis weiter (§ 56 TKG)". True of the law, wrong for HIGH, whose discount is time-limited; corrected once the PDFs arrived.
- **Quoting deal prices from WebSearch/WebFetch summaries:** the Vodafone iPhone 17 Pro deal was quoted at 34,99 €/month; the deal page shows 34,99 € needs two existing Vodafone products, the normal price is 44,99 €. The summarizer dropped the condition. Corrected in the iPhone answer.
- **simdealz.de fetch:** HTTP 403.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| iCloudDrive `Personal\Rechnungen\HIGH-Mobilfunk\_UEBERSICHT.md` | Created | Tariff, price jump, cancellation rules, cost traps, open points |
| iCloudDrive `...\HIGH-Mobilfunk\vertrag\Vertragszusammenfassung_HIGH-75-5G_2026-09-21.pdf` | Copied | Contract summary + product info sheet |
| iCloudDrive `...\HIGH-Mobilfunk\vertrag\AGB-Widerruf-Servicepreisliste_09-2025.pdf` | Copied | AGB, privacy, withdrawal, service price list |

---

## Current Status
The owner has not answered HIGH yet. No client work touched; no ops status applies.

---

## Next Steps
1. Owner: look up the current contract's end date in the HIGH portal and enter it in `_UEBERSICHT.md`.
2. Owner: ask HIGH how the 29,90 € connection refund works before accepting.
3. Owner: decide extend vs. iPhone 17 Pro bundle; re-check deal prices on the day (they move weekly).

---

## Context for Next Session
### Files to Read First
- iCloudDrive `Personal\Rechnungen\HIGH-Mobilfunk\_UEBERSICHT.md`

### Open Questions
- What "Start Rabatt 1,00 €, Laufzeitmonat" in the contract summary means.
- Whether HIGH 75 can buy extra data (the price list names only older HIGH tariffs).

### Working Notes
Baseline for any bundle comparison: bundle 24-month total vs 299,76 € + the phone's cash price (iPhone 17 256 GB 877,89 € on 04.10.; iPhone 17 Pro ≈1.098 € on 03.10.).

### Reference Materials
- https://www.high-mobile.de/tarife/ , https://www.high-mobile.de/vertragsverlaengerung
- https://www.dealdoktor.de/apple-iphone-17-pro-vodafone-smart-m/

---

## How to Continue
Read `_UEBERSICHT.md`; if the owner picks a bundle, fetch that deal page itself (not a summary) and rerun the baseline arithmetic.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the owner's own contract flipped the recommendation basis (discount expiry, Telekom network) that generic market research had wrong.

### Suggestions
- For consumer price comparisons, fetch the deal page itself before quoting a monthly price; search-result summaries drop conditions like "mit Kombivorteil".

### System Health
- Autonomy: 0 human interventions (fully autonomous session); both errors self-detected and corrected in later answers.
