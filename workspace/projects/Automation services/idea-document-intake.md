# Document intake to structured data

Status: idea
Added: 2026-07-28
Demand verified: no

## One-liner

AI reads a recurring document stream (invoices, receipts, delivery notes,
contracts) and pushes clean structured rows into the accounting system, ERP,
or CRM. Sold to firms paying humans to key data by hand: bookkeepers,
logistics, property managers.

## Demand (why they must buy)

Back-office labor shortage (same driver as the Steuerkanzlei idea on this
board); the volume recurs monthly so the pain never expires. E-Rechnung
adjacency keeps document pipelines topical through 2027/28: firms touching
their invoice flow for the mandate are open to automating the rest of it.

## Supply / competition (honest)

Template-OCR products exist (DATEV Unternehmen online, GetMyInvoices, Candis
class). They handle clean standard layouts and miss the long tail: layout
variance, attachments, handwritten notes, and the matching/validation logic
around extraction. Freelance integrators serve that tail at day rates.

## Automation edge

The service closest to work already delivered once (document-to-ledger
pipelines with review queues); near-zero R&D. LLM extraction absorbs layout
variance that template OCR cannot, and the margin is in the matching logic,
not the OCR.

## Offer shape

Front door: 20 of their real documents returned as a clean table same day
(fixed small price or free). Then install 3-10k EUR (ASSUMPTION), then a
per-volume retainer. Stickiest retainer on this board once installed.

## Channel (UWG-clean)

Steuerkanzlei hub (shared distribution with `idea-steuerkanzlei-automation.md`),
referral, LinkedIn, postal. The 20-doc demo is the whole pitch.

## First euro

One bookkeeper or logistics firm from the existing network, 20-doc demo run
same day, converted to a paid pilot. Realistic: 2-4 weeks.

## Risks / open questions

- Accuracy liability on financial data: a human review queue for
  low-confidence fields is part of scope, not optional.
- Integration surface (DATEV export formats, ERP/CRM APIs) must be
  enumerated per client before promising (B7).
- GDPR: processing agreement (AVV) required; document data is sensitive.
