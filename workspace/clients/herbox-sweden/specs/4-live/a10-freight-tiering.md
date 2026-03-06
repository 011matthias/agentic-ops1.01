---
id: a10
type: automation
name: Freight Tiering System
stage: spec
needs_fixes: false
version: 1.0.0
created: 2026-02-17
updated: 2026-02-17
orchestrator: n8n
trigger:
  type: n/a
  webhook_event: n/a
systems:
  - fortnox
owner: nils@herbox.se
last_changes: []
next_steps:
  - Clarify with Nils whether this replaces contract freight or only applies to new orders
  - Determine how to identify Sweden vs Europa customers
  - Implement tier lookup
stage_history:
  - stage: spec
    date: 2026-02-17
---

# A10: Freight Tiering System (Fraktstege)

## Goal

**Problem:** Freight on orders is currently copied as a flat value from the Fortnox contract (`contract.Freight`). In reality, Herbox uses a tiered freight system ("Fraktstege") where the freight cost depends on the total order value and the customer's region.

**Solution:** Implement a freight tier lookup that automatically calculates the correct freight based on order value and region (Sweden or Europa).

**Business Value:** Correct freight on every order — no manual adjustment needed, consistent pricing across all orders.

## Freight Tier Tables

Source: `Fraktstege.pdf` (sent by Nils, 2026-02-11)

### Sweden (SEK)

| Order Value (SEK) | Freight (SEK) | Notes |
|---|---|---|
| 0–500 | 129 | |
| 500–1,500 | 199 | |
| 1,500–3,000 | 299 | |
| 3,000–7,000 | 599 | |
| 7,000–15,000 | 899 | |
| 15,000–20,000 | 1,399 | |
| 20,000–30,000 | 1,799 | |
| 30,000–45,000 | 1,999 | |
| 45,000–70,000 | 2,499 | |
| 70,000+ | *On request* | Leave freight empty |

**Special case:** "Föreningar" (associations) — no invoice fee ("EJ Fakturaavgift"), 99 SEK for refills ("påfyllningar").

### Europa (EUR)

| Order Value (EUR) | Freight (EUR) |
|---|---|
| 0–50 | 19.9 |
| 50–150 | 24.9 |
| 150–300 | 39.9 |
| 300–700 | 59.9 |
| 700–1,500 | 89.9 |
| 1,500–2,000 | 139.9 |
| 2,000–3,000 | 179.9 |
| 3,000–4,500 | 199.9 |
| 4,500–7,000 | 249.9 |
| 7,000+ | *On request* | Leave freight empty |

## Where This Applies

### A9 New Orders Only

Freight tiering applies **only to new orders** (A9). Recurring orders (A1) continue to use the flat freight value from the Fortnox contract.

When creating a new order in the dashboard:
1. User adds line items → subtotal is calculated
2. System looks up freight from tier table based on subtotal + currency
3. Freight is pre-filled but editable (Rebecca can override)

### Dashboard Edit

When Rebecca edits new order line items in the dashboard, freight should recalculate (but remain editable for manual override). This does **not** apply to recurring orders — their freight stays as-is from the contract.

## Implementation Options

## Implementation

Since freight tiering only applies to new orders (dashboard), it lives entirely in the FastAPI app.

**Location:** `app/utils/freight.py`

```python
FREIGHT_TIERS = {
    "SEK": [
        (500, 129), (1500, 199), (3000, 299), (7000, 599),
        (15000, 899), (20000, 1399), (30000, 1799),
        (45000, 1999), (70000, 2499),
    ],
    "EUR": [
        (50, 19.9), (150, 24.9), (300, 39.9), (700, 59.9),
        (1500, 89.9), (2000, 139.9), (3000, 179.9),
        (4500, 199.9), (7000, 249.9),
    ],
}

def calculate_freight(subtotal: float, currency: str = "SEK") -> float | None:
    """Look up freight from tier table. Returns None if over max (on request)."""
    tiers = FREIGHT_TIERS.get(currency, FREIGHT_TIERS["SEK"])
    for max_val, freight in tiers:
        if subtotal <= max_val:
            return freight
    return None  # Over max = on request
```

### Region Detection

Region is determined by **currency**:
- `SEK` → Sweden tier table
- `EUR` → Europa tier table
- Any other currency → defaults to Sweden (SEK) table

## Resolved Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | Should tier freight replace contract freight? | **No** — tiers only apply to new orders (A9). Recurring orders (A1) keep contract freight. |
| 2 | How to identify Sweden vs Europa customers? | **By currency** — SEK = Sweden, EUR = Europa. |

## Open Questions

| # | Question | Impact |
|---|----------|--------|
| 1 | What about the "Föreningar" (associations) special case? How are they identified in Fortnox? | May need a customer type check |
| 2 | The "99 kr vid påfyllningar" (refills) — what qualifies as a refill? | Special freight logic |
| 3 | When the order is over the max tier (70k+ SEK / 7k+ EUR), should the freight field be empty or 0? | UI and Fortnox behavior |

## Testing

1. Create test orders at various value points and verify freight matches the tier table
2. Test boundary values (e.g., exactly 500 SEK, 501 SEK)
3. Test with EUR currency customer
4. Test "over max" scenario — verify freight is left empty
5. Test manual override — Rebecca edits freight in dashboard, it persists

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| A2 Upsales Order Enrichment Pipeline | Spec | Primary consumer of freight tiers — calculates freight for Upsales-triggered orders |
| Order Approval Dashboard | Done | Freight displayed in New Orders tab; editable before approval |

> **Note:** A9 (New Order Integration) was removed from scope 2026-02-18. A2 is now the primary consumer of freight tiering.
