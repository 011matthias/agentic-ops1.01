---
id: app1
name: Campaign Dashboard Frontend
type: app
stage: live
needs_fixes: false
version: 2.0.0
created: 2026-02-26
updated: 2026-03-03
orchestrator: none
trigger:
  type: manual
systems:
  - google-sheets
owner: kunde-inc
last_changes:
  - "2026-03-03: Stage corrected to live (dashboard built, not yet deployed)"
  - Built 2,798-line single-file dashboard (automations/dashboard/index.html)
  - Dark mode, Chart.js charts, Overview + Trends + Analytics tabs
next_steps:
  - Deploy to GitHub Pages
  - Set production auth token
  - Spec body updated to reflect Google Sheets (done 2026-03-06)
stage_history:
  - stage: spec
    date: 2026-02-26
  - stage: live
    date: 2026-03-03
---

# APP1: Campaign Dashboard Frontend

## Goal

**Problem:** Campaign data lives in Google Sheets but isn't easy to visualize — no trend charts, no at-a-glance summary cards, no sequence-level drill-down.

**Solution:** Static HTML/CSS/JS dashboard hosted on Vercel/Netlify/GitHub Pages that fetches data from n8n webhook API endpoints.

**Business Value:** Clean visual interface for the client to monitor campaign performance, identify underperforming campaigns, and track week-over-week trends without opening Google Sheets.

## Tech Stack

- **HTML/CSS/JS** — no framework, single-page app
- **Chart.js** via CDN — line and bar charts for trends
- **System font stack** — `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- **CSS variables** for theming
- **Hosting:** Vercel, Netlify, or GitHub Pages (static files)

## Layout

### Overview Tab (default)

```
┌──────────────────────────────────────────────────────────────┐
│ HEADER: "Kunde Inc."                    Last synced: 5m ago  │
│ Tabs: [Overview] | Trends                          [Logout]  │
├──────────────────────────────────────────────────────────────┤
│ STATS BAR (4 summary cards — aggregated totals)              │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│ │Total Leads│ │Emails Sent│ │Avg Open% │ │ Booked   │        │
│ │   1,430   │ │   6,200   │ │   42.3%  │ │    13    │        │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
├──────────────────────────────────────────────────────────────┤
│ [Status: All ▾]  [Search: ____________]                      │
│ ┌────────────┬────────┬───────┬──────┬───────┬───────┬─────┐│
│ │ Name     ↕ │Status ↕│Leads ↕│Sent ↕│Open% ↕│Reply%↕│Bkd ↕││
│ ├────────────┼────────┼───────┼──────┼───────┼───────┼─────┤│
│ │ Campaign A │ Active │   250 │ 1200 │  45%  │   8%  │   5 ││
│ │  ▶ steps   │        │       │      │       │       │     ││
│ │ Campaign B │ Done   │   180 │  900 │  38%  │  12%  │   8 ││
│ │  ▶ steps   │        │       │      │       │       │     ││
│ └────────────┴────────┴───────┴──────┴───────┴───────┴─────┘│
│                                                              │
│ EXPANDED (click ▶):                                          │
│ │ Step 1 │ Sent: 250 │ Open: 52% │ Reply: 3% │              │
│ │ Step 2 │ Sent: 210 │ Open: 41% │ Reply: 5% │              │
│ │ Step 3 │ Sent: 180 │ Open: 38% │ Reply: 8% │              │
└──────────────────────────────────────────────────────────────┘
```

### Trends Tab

```
┌──────────────────────────────────────────────────────────────┐
│ [Campaign selector: All ▾]  [Period: 12 weeks ▾]            │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ LINE CHART: Open Rate & Reply Rate over weeks            │ │
│ │ (Chart.js, dual Y-axis, one line per metric)             │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ BAR CHART: Emails Sent per week                          │ │
│ │ (Chart.js, stacked by campaign if "All" selected)        │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ LINE CHART: Meetings Booked over weeks                   │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

```
1. User opens dashboard URL
2. Check localStorage for auth token
   → No token: show login screen (password field + submit)
   → Has token: proceed to step 3
3. Fetch all 3 endpoints in parallel:
   GET {N8N_BASE}/webhook/dashboard-campaigns?token=XXX
   GET {N8N_BASE}/webhook/dashboard-sequences?token=XXX
   GET {N8N_BASE}/webhook/dashboard-weekly?token=XXX
4. On success: render overview tab
   On 401: clear token, show login
   On error: show error banner with retry button
5. Auto-refresh every 5 minutes
```

## Design System

Following existing patterns from Herbox Sweden dashboard:

| Element | Value |
|---------|-------|
| Background | `#f5f5f5` |
| Cards | white, `border-radius: 8px`, `box-shadow: 0 1px 3px rgba(0,0,0,0.1)` |
| Active status | `#e6f4ea` bg, `#1e7e34` text |
| Completed status | `#e8eaed` bg, `#5f6368` text |
| Paused status | `#fef7e0` bg, `#b06000` text |
| Font sizes | Header: 1.25rem, Body: 0.875rem, Meta: 0.75rem |
| Table rows | Alternating `#fff` / `#fafafa` |
| Sort indicators | `↕` default, `▲` asc, `▼` desc |

## JavaScript Architecture

```
state = {
  token: localStorage 'dashboard_token',
  campaigns: [],
  sequences: [],
  weeklyTrends: {},
  loading: true,
  error: null,
  activeTab: 'overview',
  sortColumn: 'name',
  sortDirection: 'asc',
  statusFilter: 'all',
  searchQuery: '',
  expandedCampaigns: new Set()
}

Functions:
- fetchDashboardData() — parallel fetch from 3 endpoints
- renderAll() — dispatch to current tab renderer
- renderOverview() — stats bar + sortable table
- renderTrends() — Chart.js charts
- renderLogin() — password form
- sortCampaigns(column) — toggle sort
- filterCampaigns() — by status + search
- toggleSequences(campaignId) — expand/collapse
- computeAggregates() — sum totals for stats bar
```

## File Structure

```
automations/dashboard/
  index.html     # Single file with embedded CSS and JS
                 # (or split into index.html + style.css + app.js)
```

## Acceptance Criteria

- [ ] Login screen accepts token, stores in localStorage
- [ ] Invalid token shows error, clears stored token
- [ ] Stats bar shows correct aggregated totals
- [ ] Campaign table sorts by any column (click header)
- [ ] Campaign table filters by status dropdown
- [ ] Campaign table search filters by name
- [ ] Sequence rows expand/collapse per campaign
- [ ] Trends tab shows line chart for rates and bar chart for volume
- [ ] Campaign selector on Trends tab filters charts
- [ ] Auto-refresh every 5 minutes
- [ ] Loading spinner during data fetch
- [ ] Error banner with retry on API failure
- [ ] Responsive layout (works on tablet+)
- [ ] Works with mock data (for development before API is live)

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-26 | Initial specification |
