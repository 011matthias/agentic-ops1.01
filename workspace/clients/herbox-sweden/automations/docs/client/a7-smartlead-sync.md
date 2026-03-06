# Smartlead Campaign Sync

Your campaign performance data from Smartlead automatically syncs to Airtable every day, giving you real-time visibility into outreach effectiveness without any manual work.

## What This Does

**The Problem:** Campaign performance metrics in Smartlead were disconnected from your Sales CRM in Airtable. You had to manually copy data to track which campaigns were working.

**The Solution:** Every morning at 10:00 AM, this automation fetches all campaign analytics from Smartlead and updates your Campaigns table in Airtable. New campaigns are automatically added, existing ones are updated with the latest metrics.

**Runs:** Every day at 10:00 AM Stockholm time

## How It Works

1. **Fetch All Campaigns** - Connects to Smartlead and retrieves your complete list of campaigns (including drafts)

2. **Get Detailed Analytics** - For each campaign, fetches performance metrics like emails sent, opened, replied, and lead status breakdowns

3. **Update Airtable** - Upserts the data to your Campaigns table, creating new records for new campaigns or updating existing ones based on Campaign ID

4. **Smart Processing** - Handles each campaign individually with rate limiting, so if one campaign has an issue, the others still sync successfully

## What You'll See

When this automation runs successfully, you'll see:

- **In Airtable:** All campaign data updated in the Campaigns table with the latest metrics
- **In the Dashboard:** Success status with a summary showing how many campaigns were synced
- **In Logs:** Detailed execution log showing each campaign processed

### Fields Updated in Airtable

Every sync updates these fields in your Campaigns table:

| Field | What It Shows |
|-------|---------------|
| **Campaign ID** | Unique identifier from Smartlead (used to match records) |
| **Campaign Name** | Name of your campaign |
| **Status** | Active, Completed, Ramp Up, etc. (automatically formatted) |
| **Total Leads** | Total number of leads in the campaign |
| **Leads In Progress** | Leads currently being contacted |
| **Leads Completed** | Leads that have finished the sequence |
| **Leads Not Started** | Leads waiting to start |
| **Email Replied (Positive)** | Leads who replied with interest |
| **Prospects Contacted** | Unique prospects who received emails |
| **Email Sent** | Total emails sent |
| **Email Opened** | Total email opens |
| **Email Replied** | Total replies received |
| **Email Bounced** | Total bounced emails |
| **Number Of Sequences** | Number of email sequences in campaign |

## Example

### Before (Manual Process)
1. Log into Smartlead
2. Open each campaign
3. Copy analytics data
4. Paste into Airtable
5. Repeat daily to keep data fresh
6. Risk of missing campaigns or outdated data

### After (Automated)
1. Wake up at 10:00 AM
2. Check Airtable - all campaign data is already updated
3. Make decisions based on fresh data
4. No manual work required

## Status Meanings

When you check the dashboard, you may see these statuses:

| Status | What It Means |
|--------|---------------|
| Success | All campaigns synced successfully |
| Partial Success | Some campaigns synced, others had errors (but sync completed) |
| Failed | Entire sync failed - the team has been notified |
| Auto-resolved | Had an issue but fixed itself automatically |

## Troubleshooting

### "No campaigns showing in Airtable"

**What to check:**
1. Do you have campaigns in Smartlead? (Including draft campaigns)
2. Is the automation running? Check the dashboard logs
3. Look for error messages in the latest log entry

**Common causes:**
- New Smartlead account with no campaigns yet
- API key needs to be refreshed
- Network connectivity issue

### "Some campaigns aren't updating"

**What to check:**
1. Check the campaign name in the latest log - was it processed?
2. Look for the Campaign ID in Airtable's "Campaign ID" field
3. Review the log for any error messages about specific campaigns

**Common causes:**
- Campaign was deleted in Smartlead but still exists in Airtable (won't be updated)
- Individual campaign has an API issue (others will still sync)
- Field type mismatch in Airtable

### "Data looks wrong or incomplete"

**What to check:**
1. Compare a specific campaign's data in Smartlead vs Airtable
2. Check if the sync ran today (look at the log timestamp)
3. Verify all field names match the list above

**Common causes:**
- Viewing old data (wait for next sync at 10:00 AM)
- Field names changed in Airtable (needs configuration update)
- Smartlead API returning incomplete data (check their status)

### "How do I run it manually?"

If you need fresh data before 10:00 AM:

1. Go to the automation dashboard
2. Find "Smartlead Campaign Sync" card
3. Click "Run Now" button
4. Wait ~2 minutes (depends on number of campaigns)
5. Refresh Airtable to see updated data

**Note:** Manual runs work exactly like scheduled runs - safe to trigger anytime.

## What Gets Synced

**Always included:**
- All active campaigns
- All draft campaigns
- All completed campaigns
- All archived campaigns

**Match behavior:**
- If Campaign ID exists in Airtable → Updates the existing record
- If Campaign ID is new → Creates a new record
- If campaign is deleted from Smartlead → Remains in Airtable (not deleted)

**Rate limiting:**
- Processes campaigns one at a time
- 2-second pause between campaigns (Smartlead API requirement)
- Safe for up to 100+ campaigns

## Questions?

If you have questions about this automation:

**For data issues:**
- Check the automation logs in the dashboard
- Compare specific campaign in Smartlead vs Airtable
- Note the Campaign ID when reporting issues

**For technical issues:**
- Contact the development team
- Include the log timestamp and error message
- Mention which campaigns are affected

**For feature requests:**
- Want to sync additional fields? Let us know
- Need different sync timing? We can adjust the schedule
- Want to exclude certain campaigns? We can add filtering

---
*Last updated: 2026-01-15*
*Automation ID: `a7_smartlead_campaign_sync`*
*Version: 1.0.0*
