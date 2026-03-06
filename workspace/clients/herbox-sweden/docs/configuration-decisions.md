# Herbox Configuration Decisions

This document tracks configuration decisions and their reasoning for the Herbox automations.

---

## A6.3 Contact Enrichment

### MAX_CONTACTS

| Setting | Value | Environment |
|---------|-------|-------------|
| Testing | 20 | Development |
| Production | TBD | Railway |

**Location:** `app/automations/contact_enrichment.py:21`

**Purpose:** Limits how many contacts are processed per enrichment run.

**Considerations:**
- **API Rate Limits:** Leadmagic, Trykitt have rate limits. Processing too many contacts too fast triggers 429 errors.
- **Railway Timeout:** Railway functions timeout after ~5 minutes. Large batches may not complete.
- **Cost Control:** Each contact = 1-3 API calls. Unbounded runs could drain credits.
- **CRON Frequency:** If running every 6 hours, smaller batches processed more frequently may be better than one large batch.

**Options:**
1. **Keep limit (recommended):** 100-500 per run with 6-hour CRON
2. **Remove limit:** Process all pending contacts (risky - could timeout or drain credits)
3. **Dynamic:** Base on time budget or available API credits

**Decision:** [Pending - update after production testing]

---

### CONCURRENT_LIMIT

| Setting | Value |
|---------|-------|
| Current | 10 |

**Location:** `app/automations/contact_enrichment.py:22`

**Purpose:** How many contacts to process simultaneously (parallel API calls).

**Reasoning:** Balance between speed and API rate limits. 10 concurrent allows fast processing without overwhelming APIs.

---

### RATE_LIMIT_DELAY

| Setting | Value |
|---------|-------|
| Current | 0.5 seconds |

**Location:** `app/automations/contact_enrichment.py:23`

**Purpose:** Delay between verification API calls to avoid rate limiting.

**Reasoning:** Leadmagic email validation has rate limits. 0.5s delay adds ~50 seconds per 100 contacts but prevents 429 errors.

---

## A6.4 Data Cleaning

### MAX_RECORDS

| Setting | Value | Environment |
|---------|-------|-------------|
| Testing | 20 | Development |
| Production | TBD | Railway |

**Location:** `app/automations/data_cleaning.py`

**Purpose:** Limits records processed per cleaning run.

**Considerations:** Same as MAX_CONTACTS - API rate limits (OpenRouter), timeouts, costs.

---

## Email Verification Status Mapping

All verification vendors map to these Airtable options:

| Vendor Status | Airtable Status |
|---------------|-----------------|
| ok, valid, safe, deliverable | **Valid** |
| risky, catch-all, accept-all | **Catch-All** |
| invalid, undeliverable, bounce, spam-trap, disposable | **Invalid** |
| (anything else) | **Unknown** |

**Location:** `app/automations/contact_enrichment.py:standardize_status()`

---

## Enrichment Vendor Tracking

| Vendor | Field Value |
|--------|-------------|
| Leadmagic Email Finder | Leadmagic |
| Leadmagic LinkedIn Profile | Leadmagic-LinkedIn |
| Trykitt | Trykitt |
| Pre-existing email | Existing |

**Verification Vendor:** Always "Leadmagic" (using Leadmagic email validation API)

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| AIRTABLE_TOKEN | Yes | Airtable API token |
| LEADMAGIC_API_KEY | Yes | Leadmagic API key (enrichment + verification) |
| TRYKITT_API_KEY | No | Trykitt API key (fallback enrichment) |
| OPENROUTER_API | Yes | OpenRouter API for A6.4 data cleaning |

---

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-01-22 | Switched verification from Usebouncer to Leadmagic | Cost savings, already have Leadmagic API key |
| 2026-01-22 | Added RATE_LIMIT_DELAY (0.5s) | Prevent API rate limiting |
| 2026-01-22 | Standardized status mapping to 4 options | Match Airtable field options |
