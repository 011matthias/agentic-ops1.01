# Kunde Inc. — Campaign Dashboard

> A working proof-of-concept: a live dashboard for monitoring cold email campaign performance, backed by Google Sheets, automated data pipelines, and three API endpoints running in the cloud.
>
> **Current status:** Fully operational. Google Sheets connected, daily sync running, weekly snapshots accumulating. Only missing: real Smartlead API key.

---

## What's Live Now

Four things working together:

### The Dashboard (APP1)

A web page that visualises campaign performance. You open it in a browser, enter a password, and see:

- **Summary cards** across the top — total leads, emails sent, average open rate, meetings booked
- **Campaign table** — one row per campaign, sortable by any column, filterable by status or search
- **Sequence drill-down** — click the arrow on any campaign to see how each email step performed (open rate, reply rate per step)
- **Trend charts** — switch to the Trends tab to see open rate, reply rate, email volume, and meetings booked over time as line and bar charts
- **Analytics** — conversion funnel, ROI metrics, lead status breakdown, campaign comparison radar chart
- **Auto-refresh** — data updates silently every 5 minutes

No installation needed. It's a single HTML file — works in any browser.

### The API Backend (A3)

Three cloud endpoints running on n8n. The dashboard calls these to get its data:

| Endpoint | What it returns |
|----------|----------------|
| `/dashboard-campaigns` | All 18 campaigns with metrics (leads, sent, open %, reply %, meetings booked) |
| `/dashboard-sequences` | Per-step breakdown for each campaign's email sequence (50+ steps) |
| `/dashboard-weekly` | 24 weeks of historical trend data per campaign |

Each endpoint reads from Google Sheets and checks the password before returning data.

### The Daily Sync (A1)

Every morning at 8:00 AM, an n8n workflow updates campaign data in Google Sheets. Currently running with simulated data progression — when a Smartlead API key is provided, it will pull real data instead.

### The Weekly Snapshot (A2)

Every Monday at 6:00 AM, an n8n workflow reads the current state of each campaign and appends a timestamped snapshot row to Google Sheets. This is what powers the trend charts.

---

## How Data Flows

### Today (operational pipeline)

```
A1: Daily Sync (08:00 daily)
  |
  |  updates campaign + sequence metrics in Google Sheets
  v
Google Sheets (campaigns, sequences, weekly snapshots)
  |                          |
  |  every Monday at 06:00   |  on every dashboard visit
  v                          v
A2: Weekly Snapshot         A3: API Endpoints
  |  appends trend data        |  reads from Sheets
  |  to Sheets                 |
  v                          v
                            Dashboard (renders tables, charts, cards)
```

### Future (real campaign data)

```
Smartlead (campaign platform)
  |
  |  replaces the simulation in A1
  v
A1: Daily Sync (08:00 daily)
  |
  v
[everything else stays the same]
```

The key takeaway: **the entire pipeline is operational.** The only placeholder is the data source for A1 (simulation instead of Smartlead API). Everything else is real and running.

---

## What the Dashboard Shows

| What you see | What it means |
|---|---|
| **Total Leads** (top card) | Total number of prospects contacted across all campaigns |
| **Emails Sent** (top card) | Total emails delivered across all campaigns and sequence steps |
| **Avg Open Rate** (top card) | Average percentage of emails that were opened |
| **Meetings Booked** (top card) | Total meetings booked from all campaigns |
| **Campaign table** | One row per campaign — sort by clicking any column header, filter by status or name |
| **Arrow icon on a row** | Click to expand and see how each email step performed (Step 1, Step 2, etc.) |
| **Trends tab: Rate chart** | Open rate and reply rate plotted week by week — shows whether performance is improving |
| **Trends tab: Volume chart** | How many emails were sent each week |
| **Trends tab: Bookings chart** | How many meetings were booked each week |
| **Campaign selector** | On the Trends tab, filter charts to one campaign or view all together |
| **Analytics tab** | Conversion funnel, ROI metrics, campaign comparison |

---

## What's Needed for Real Data

1. **Smartlead API key** — plug into A1 workflow, replace the simulation Code node
2. That's it — everything else is already built and running

---

## Path to Production

### Phase 1 — Dashboard & Demo Data (DONE)
- [x] Build dashboard (APP1) with 5 tabs, charts, filters, dark mode
- [x] Build 3 API endpoints (A3) serving demo data
- [x] Expand to 18 campaigns, 50 sequences, 24 weeks of trends
- [x] Fix UI bugs (chart overflow, fullscreen, scrolling)

### Phase 2 — Google Sheets Integration (DONE)
- [x] Create Google Spreadsheet with 3 tabs (automated via n8n workflow)
- [x] Update 3 API workflows to read from Sheets
- [x] Test dashboard end-to-end with Sheets data
- [x] Build A1: Daily Campaign Sync (simulated Smartlead data)
- [x] Build A2: Weekly Snapshot

### Phase 3 — Deploy & Share
- [ ] Deploy dashboard to GitHub Pages
- [ ] Share the dashboard URL
- [ ] Set production password

### Phase 4 — Real Data (needs Smartlead API key)
- [ ] Replace simulation in A1 with real Smartlead API calls
- [ ] Monitor first week of real syncs

---

## Technical Reference

### Infrastructure

| Component | Details |
|---|---|
| Automation platform | n8n, running at `unpauseai.app.n8n.cloud` |
| Data storage | Google Sheets (`1axfHoNjE8LaJY-tKwbbAElfwVXN--cU09aeHaT6ZRoU`) |
| Dashboard file | `automations/dashboard/index.html` (single HTML file) |
| Demo password | `kunde-demo-2026` |
| Frontend tech | HTML, CSS, JavaScript, Chart.js (no framework) |

### Live Workflows

| Workflow | n8n ID | Schedule | Status |
|---|---|---|---|
| A3a: Dashboard API - Campaigns | `QoEf8USAiguQR6T2` | On request | Active |
| A3b: Dashboard API - Sequences | `kwl5FhcCHOdUF6ps` | On request | Active |
| A3c: Dashboard API - Weekly | `LNLQ5YqXvTneEBtO` | On request | Active |
| A1: Daily Campaign Sync | `kSdp7t5gHcTBk5iq` | 08:00 daily | Active |
| A2: Weekly Snapshot | `0869MI6O30YT5juH` | Monday 06:00 | Active |

### Systems

| System | Role | Status |
|---|---|---|
| n8n | Runs API endpoints, daily sync, weekly snapshots | Live |
| Google Sheets | Data storage (campaigns, sequences, weekly trends) | Live |
| Smartlead | Campaign platform — source of real data | Not yet connected (needs API key) |

---

*Last updated: March 3, 2026 — Phase 2 complete, all workflows operational*
