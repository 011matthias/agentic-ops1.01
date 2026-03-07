# Kunde Inc. — Automation Specs

## Client Overview
Cold email agency using Smartlead for campaigns. Module #1: Dashboard Automation with Google Sheets as data layer and n8n webhook APIs.

## Orchestrator: n8n

## Automations

| ID | Name | Stage | Trigger | Systems |
|----|------|-------|---------|---------|
| a1 | Daily Campaign Sync | live | cron (daily 08:00) | google-sheets |
| a2 | Weekly Snapshot | live | cron (Monday 06:00) | google-sheets |
| a3 | Dashboard API Endpoints | live | webhook (3 endpoints) | google-sheets |
| app1 | Campaign Dashboard Frontend | live | manual | google-sheets (via n8n API) |

## Dependency Order
1. Google Sheets spreadsheet (created via UTIL setup workflow)
2. A1: Daily Campaign Sync (populates Campaigns + Sequences tabs)
3. A2: Weekly Snapshot (reads Campaigns, appends to Weekly Snapshots tab)
4. A3: Dashboard API (3 webhook workflows reading from Sheets, returning JSON)
5. APP1: Dashboard Frontend (calls A3 endpoints)

## Remaining Work
- [ ] Smartlead API key (to replace simulated data in A1)
- [ ] Deploy dashboard to GitHub Pages
- [ ] Set production auth token (replace kunde-demo-2026)
- [x] Update spec bodies to reflect Google Sheets (done 2026-03-06)
