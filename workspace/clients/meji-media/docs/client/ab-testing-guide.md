# A/B Testing Guide

Your follow-up email system can send two different versions of each email to see which gets more replies. This guide explains how to use the feature.

## How It Works

1. A new enquiry arrives via your website form
2. The system randomly assigns the enquiry to **Group A** or **Group B** (50/50 split)
3. Group A receives email Version A; Group B receives Version B
4. When someone replies, the system records which group they were in
5. The **AB_Analytics** tab in your spreadsheet shows which version is performing better

The assignment happens once when the enquiry first arrives and stays the same throughout the entire follow-up sequence (initial email, follow-up #2, follow-up #3).

## Turning A/B Testing On

1. Open **Make.com** and go to **Data Stores**
2. Open the **Pipeline Config** data store
3. Find the record with key `main`
4. Change `ab_testing_enabled` from `false` to `true`
5. Save

All new enquiries will now be split 50/50 between Version A and Version B.

## Turning A/B Testing Off

1. Same steps as above, but change `ab_testing_enabled` from `true` to `false`
2. All new enquiries will receive Version A emails only
3. Existing enquiries keep their assigned variant -- nothing changes for leads already in the pipeline

## Customising Email Variants

### Where Templates Are Stored

Open **Make.com > Data Stores > Email Templates**. You'll see 8 active template records:

| Email | Version A Key | Version B Key |
|-------|---------------|---------------|
| Initial response (standard leads) | `initial_standard_a` | `initial_standard_b` |
| Initial response (hot leads) | `initial_high_a` | `initial_high_b` |
| First follow-up | `step_2_a` | `step_2_b` |
| Final follow-up | `step_3_a` | `step_3_b` |

### How to Edit a Template

1. Open Make.com > Data Stores > Email Templates
2. Find the record you want to edit (e.g. `step_2_b`)
3. Edit the `subject` and/or `body_html` fields
4. Keep the placeholders -- they get replaced with real data:
   - `##name##` -- the enquirer's name
   - `##topic##` -- what they enquired about
   - `##organisation##` -- their company (initial emails only)
   - `##ai_opening##` -- AI-generated personalised opening line
   - `##signature##` -- your email signature
5. Save

### What You Can Change

- Subject lines (great for testing different hooks)
- Email body text and tone
- Call-to-action wording
- Layout and formatting (HTML)

### What Not to Change

- The `key` field -- this is how the system finds the template
- Placeholder tokens (`##name##` etc.) -- removing these means that data won't appear
- The `active` field -- keep it `true`

## Reading Your Results

Open your Google Sheet and go to the **AB_Analytics** tab. You'll see:

| Metric | What It Means |
|--------|---------------|
| **Total Leads** | How many enquiries are in each group |
| **Replied** | How many people replied to your emails |
| **Reply Rate** | Percentage who replied -- **this is the key metric** |
| **Cold** | How many went through all follow-ups without replying |
| **Still Active** | How many are still in the follow-up sequence |
| **Lift (B vs A)** | The difference in reply rates -- positive means B is winning |

These numbers update automatically whenever you open the spreadsheet.

### When to Make a Decision

Wait for **at least 20-30 enquiries per variant** before drawing conclusions. With fewer leads, random chance can make one version look better even when there's no real difference.

## Common Scenarios

### "I want to test a new subject line"

1. Pick which email to test (e.g. the initial response)
2. Edit the Version B template's `subject` field
3. Keep everything else the same -- that way you know the subject line caused any difference

### "I want to test a completely different email"

1. Edit the Version B template's `subject` and `body_html`
2. Note: you won't know which change caused the difference (subject vs body vs both)

### "Version B is winning -- I want to use it for everyone"

1. Copy Version B's subject and body_html into the Version A template
2. Disable A/B testing (`ab_testing_enabled` = `false`)
3. All new enquiries now get the winning version

### "I want to start a fresh test"

1. Update Version B templates with new content
2. Note: the analytics show all-time totals, not per-test periods. To track individual tests, note the date you started and compare lead counts before/after.

### "I want to stop A/B testing completely"

1. Set `ab_testing_enabled` to `false` in Pipeline Config
2. All new enquiries get Version A
3. Existing leads continue with their assigned variant until they reply or go cold

## Rolling Back to Original Templates

If you want to completely undo the A/B setup:

1. Set `ab_testing_enabled` to `false` in Pipeline Config
2. In Email Templates, find the 4 original records (`initial_standard`, `initial_high`, `step_2`, `step_3`) -- they're marked `active: false`
3. Set them to `active: true`
4. Set all 8 `_a` and `_b` variants to `active: false`

The system will use the original single-version templates for all new enquiries.
