# Open Questions — Upsales Enrichment Pipeline

Questions that must be answered before or during implementation.

---

## 🔴 Blockers (must answer before building)

### Upsales Webhook / Trigger

| # | Question | Who | Context |
|---|----------|-----|---------|
| 1 | What is the exact Upsales webhook event name when a deal moves to the "Fortnox" stage? (e.g. `opportunity.stage_changed`?) | Nils | Needed to configure n8n webhook trigger |
| 2 | What is the exact name of the deal stage in Upsales that triggers Fortnox order creation? ("Fortnox", "Order", something else?) | Nils | Needed to filter webhook events |
| 3 | Does the Upsales webhook payload include the company/customer number directly, or do we need to make a follow-up API call? | Test Workflow | Run Test Workflow to confirm |

### Fortnox Order Lookup

| # | Question | Who | Context |
|---|----------|-----|---------|
| 4 | Does the native Upsales→Fortnox integration put any Upsales reference (deal ID, opportunity ID) on the Fortnox order — e.g. in `YourOrderNumber`, `ExternalReference`, or `OurReference`? | Test Workflow | If yes, use that for reliable lookup. If no, fall back to customer number + latest order. |
| 5 | After the native integration creates a Fortnox order, how do we reliably find it? By customer number (latest order)? By a reference field? | Test Workflow | |

---

## 🟡 Important (answer before first production run)

### Freight & Pricing

| # | Question | Who | Context |
|---|----------|-----|---------|
| 6 | Should FreightVAT for Upsales orders be **25%** (standard Swedish VAT) or **30%** (as in old A3 spec)? | Nils | Old A3 had 30%, but 25% is the standard rate |
| 7 | Is the A10 freight tier table (Fraktstege.pdf) correct and final? Should it apply to ALL Upsales-triggered orders, or only specific customer types? | Nils | A10 previously only applied to A9 (manual orders) — now we want it for A2 as well |
| 8 | For customers over the max freight tier (70k+ SEK / 7k+ EUR) — should freight be left empty (null) or set to 0? | Nils | Affects Fortnox order behavior |
| 9 | What is the default **PriceList** code to set on enriched orders? (e.g. "A", "B", or customer-specific?) | Nils | Currently TBD in A3 spec |

### Order Text

| # | Question | Who | Context |
|---|----------|-----|---------|
| 10 | What should the default `Remarks` text be on enriched Upsales orders? (Old A3 spec had "Order synkad från Upsales") | Rebecca/Nils | Swedish text preferred |

### Warehouse

| # | Question | Who | Context |
|---|----------|-----|---------|
| 11 | Should `StockPointCode` (warehouse) be set on enriched orders? If yes, what value? ("1"?) | Nils | Was commented out in A3 spec — needs confirmation |

---

## 🟢 Nice to Know (can proceed without, but good to clarify)

| # | Question | Who | Context |
|---|----------|-----|---------|
| 12 | How long does the native Upsales→Fortnox integration take to create the Fortnox order after the deal stage change? 5 minutes wait in n8n — is that enough? | Nils | Current plan: 5 min wait. May need tuning. |
| 13 | Are there any deal stages in Upsales that should NOT trigger enrichment (e.g. test deals, internal deals)? | Nils | May need a filter step |
| 14 | Should the "Föreningar" (associations) special case from A10 (99 SEK refill freight) apply to Upsales enrichment too? How are associations identified? | Nils | A10 mentions this as an open question |
| 15 | When the mode switch is set to `"direct"` and Fortnox is updated immediately — should we still log anything to the FastAPI database? | Internal decision | For audit trail purposes |

---

## Answers Log

| # | Answer | Date | Source |
|---|--------|------|--------|
| 2 | Stage name is **"Fortnox"**, stage ID = **12** | 2026-02-18 | A2-Test workflow |
| 3 | Webhook payload: N/A — we're polling, not using webhooks | 2026-02-18 | Design decision |
| 4 | **No** — all Fortnox reference fields (YourOrderNumber, OurReference, YourReference, ExternalReference) are EMPTY. The link is the inverse: Upsales deal `description` field stores the Fortnox `DocumentNumber` (e.g. "8012"). The deal `regBy` is "Fortnox app" — the native integration creates the Upsales deal and puts the Fortnox order number in `description`. | 2026-02-18 | A2-Test workflow execution #35 |
| 5 | Use `deal.description` directly as the Fortnox DocumentNumber — `GET /3/orders/{deal.description}`. No customer search needed. | 2026-02-18 | A2-Test workflow execution #35 |
| 1 (A2 spec) | Upsales date filter param is **`modDate`** (not `modifiedSince`). Field on the deal object is also `modDate`. | 2026-02-18 | Confirmed by Nils + deal payload |
| 1 (A2 spec) | Upsales deals endpoint is `/api/v2/orders` (not `/api/v2/opportunities`) | 2026-02-18 | A2-Test workflow |
| — (A2 spec) | Customer matching: Upsales `company.orgNo` → Fortnox customer search by org number → `CustomerNumber` confirmed working (e.g. orgNo 556760-5471 → CustomerNumber 2100) | 2026-02-18 | A2-Test workflow execution #35 |
| 6 | Remarks: use `custom[fieldId=7]` (REMARKS field) value if present, else omit entirely | 2026-02-18 | Confirmed by Riccardo |
| 11 | StockPointCode = **"2"** | 2026-02-18 | Confirmed by Riccardo |
| 6 (FreightVAT) | **25%** — provisional. Explicitly set as starting point, may change later. | 2026-02-18 | Provisional decision by Riccardo |

---

## 🟠 Provisional Decisions (confirmed for now, may change)

| Decision | Value | Who | Notes |
|----------|-------|-----|-------|
| FreightVAT | **25%** | Riccardo | Explicitly provisional — "start with 25%, change later" |
| StockPointCode | **"2"** | Riccardo | Confirmed |
| Remarks source | `custom[fieldId=7]` if present, else omit | Riccardo | Confirmed |
| YourOrderNumber source | `custom[fieldId=1]` (REFERENCE / Kundens referensnummer) | Inferred | **Not explicitly confirmed** — needs verification before build |
| Stage filter | Client-side only (`stage.id === 12`) | A2-Test | API `stage` param doesn't work reliably |
| Fortnox order lookup | `custom[fieldId=4]` (FORTNOX_ORDER_ID) | A2-Test | Confirmed via custom field schema |
| `modDate` filter format | ISO 8601 timestamp | Assumed | **Format not tested** — verify at start of build session |
