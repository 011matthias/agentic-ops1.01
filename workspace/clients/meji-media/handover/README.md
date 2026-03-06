# Automated Follow-Up System — Setup Guide

## What's Included

| File | Purpose |
|------|---------|
| `setup-form.html` | Interactive setup wizard (open in your browser) |
| `s0-environment-setup.json` | One-time setup scenario blueprint |
| `a1-template.json` | A1 — Enquiry Follow-Up (auto-deployed by S0) |
| `a2-template.json` | A2 — Reply Detection (auto-deployed by S0) |
| `a3-template.json` | A3 — Scheduled Follow-Ups (auto-deployed by S0) |
| `ab-testing-guide.md` | A/B testing setup and usage guide |

## Prerequisites

Before you start, make sure you have:

- **Make.com account** — [sign up here](https://www.make.com/en/register) (free plan works to start)
- **Google account** with Gmail and Google Sheets (preferably a shared/team inbox)
- **OpenAI API key** — [create one here](https://platform.openai.com/api-keys) (~$0.01 per enquiry)
- **Downloaded files** from the link we sent you (4 blueprint files + the setup wizard page)

## Quick Start

1. Download all files from the link we sent you and save them in one folder
2. Open **setup-form.html** in your browser
3. Follow the 3-step wizard — it walks you through everything

The wizard handles:
- Importing the setup scenario (S0) into Make.com and connecting your Google account
- Creating your data stores, email templates, and tracking spreadsheet
- Deploying all 3 production automations (A1, A2, A3) with your connections pre-configured
- Returning your A1 webhook URL so you can connect your website form

**Estimated time: 5 minutes.**

## What Gets Created

The setup process automatically creates:

| Resource | Description |
|----------|-------------|
| **Pipeline Config** data store | 35 fields: scoring weights, follow-up timing, AI settings, brand config, A/B testing toggle |
| **Email Templates** data store | 8 A/B variant email templates (4 pairs: initial standard, initial high-priority, step 2, step 3) |
| **Google Sheet** | "Company Name — Enquiry Tracker" with 17-column Leads worksheet + AB_Analytics tab |
| **A1 scenario** | Enquiry Follow-Up — webhook-triggered, receives form submissions |
| **A2 scenario** | Reply Detection — runs every 5 minutes, checks Gmail for replies |
| **A3 scenario** | Scheduled Follow-Ups — runs every 15 minutes, sends step 2 and step 3 emails |

## How the System Works

```
Website form submission
        |
        v
   A1: Enquiry Follow-Up
   - Logs to Google Sheet
   - Scores the lead (hot/warm/standard)
   - Sends personalised initial email
   - Schedules follow-ups
        |
        +------> A2: Reply Detection (every 5 min)
        |        - Checks Gmail for replies
        |        - Marks lead as "stopped" if they replied
        |
        +------> A3: Scheduled Follow-Ups (every 15 min)
                 - Sends step 2 and step 3 emails on schedule
                 - Skips leads that already replied
```

## After Setup

- **Delete the S0 scenario** — it's a one-time tool
- **Keep A1, A2, A3 active** — they run your follow-up pipeline
- **Monitor your Google Sheet** — all enquiries are logged there
- Open the tracking spreadsheet to see lead scores, statuses, and email history

## Troubleshooting

**"Scenario failed to initialize"**
- Make sure you clicked "Run once" in the S0 scenario before submitting the form
- Check that your Make.com API token is correct (Profile > API Tokens)

**Data store IDs are empty in the response**
- Your Make.com API token may be invalid or expired — create a new one
- Check that your Team ID is correct (it's in your Make.com URL after `/team/`)

**"Connection not found" or scenario deployment failed**
- S0 auto-detects your Google Sheets and Gmail connections. Make sure you authorised both connections when you imported S0 (Step 2 of the wizard).
- If you have multiple Google accounts connected, the system picks the first one for each type. Verify the right account was selected in S0.

**No email received after test enquiry**
- Check the A1 scenario execution history in Make.com for errors
- Verify your Gmail connection is authorised
- Check spam/junk folder

**Google Sheet not updating**
- The spreadsheet is linked automatically during setup — no manual selection needed
- Verify the Google Sheets connection is authorised in Make.com

## Support

If you run into issues, check the scenario execution history in Make.com (Scenarios > click scenario > History tab). Each execution shows which modules succeeded or failed with detailed error messages.
