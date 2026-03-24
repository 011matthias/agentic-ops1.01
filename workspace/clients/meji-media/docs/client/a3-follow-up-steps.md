# A3: Scheduled Follow-Up Steps

## What It Does

This automation handles the timed follow-up sequence. Every 15 minutes, it checks the tracking sheet for enquiries that are due for their next follow-up email. If one is due, it generates a personalised AI opening line and sends the appropriate follow-up, then schedules the next step. After the final follow-up, it marks the enquiry as "cold" and stops.

**Runs:** Every 15 minutes, automatically.

---

## The Follow-Up Sequence

After the initial email (sent by A1), the follow-up sequence works like this:

| Step | What Happens | Email Sent? |
|------|-------------|-------------|
| **Step 1** | Initial email sent by A1 | Yes -- handled by A1, not A3 |
| **Step 2** | First follow-up -- a friendly nudge with AI-personalised opening | Yes -- from editable template (Version A or B if A/B testing is on) |
| **Step 3** | Final follow-up -- a last check-in with AI-personalised opening | Yes -- from editable template (Version A or B if A/B testing is on) |
| **Step 4** | Close-out -- marked as cold | No -- the enquiry is simply closed |

If the person replies at any point during this sequence, A2 detects it and stops everything. No more automated emails.

---

## Timing -- How Quickly Follow-Ups Are Sent

The timing between steps depends on the enquiry's priority. Higher-priority leads get follow-ups sooner:

| Step | Hot Leads | Warm Leads | Standard Leads |
|------|-----------|------------|----------------|
| Step 2 (first follow-up) | 6 hours after initial | 12 hours after initial | 24 hours after initial |
| Step 3 (final follow-up) | 30 hours after initial | 60 hours after initial | 96 hours after initial |
| Step 4 (close-out) | ~3 days after step 3 | ~3 days after step 3 | ~3 days after step 3 |

These timings are configurable -- ask your automation specialist if you'd like to adjust them.

**Note:** Hot leads (where your team is also notified immediately) enter the follow-up sequence with the fastest timing. They receive the same follow-up emails as other leads, just sooner.

---

## What You'll See

When A3 sends a follow-up:

- **In the Google Sheet:** The row updates:
  - `current_step` increases by 1 (e.g., 2 -> 3)
  - `next_step_due` is set to the next follow-up time
  - `status` changes to `following_up`
  - `last_email_sent` shows when the email went out
- **In your Gmail Sent folder:** The follow-up email will appear as a sent message
- **In the enquirer's inbox:** They receive a follow-up that looks like a natural, personal email -- each one opens with an AI-generated sentence referencing their specific enquiry topic

When A3 marks an enquiry as cold:

- **In the Google Sheet:** The row updates:
  - `status` changes to `cold`
  - `stopped` changes to `TRUE`
- **No email is sent** -- the enquiry is simply closed out

---

## What "Marked as Cold" Means

When an enquiry reaches step 4 without a reply, it's marked as "cold". This means:

- The person didn't respond to any of the 3 emails (initial + 2 follow-ups)
- All automated follow-ups are stopped
- The row stays in the Google Sheet for your records
- You can still reach out to them manually if you wish -- the automation won't interfere

Being marked as cold is a normal part of the process. Not every enquiry turns into a conversation, and the system handles that gracefully.

---

## Troubleshooting

### "A follow-up wasn't sent when I expected it"
- A3 checks every 15 minutes, so there can be up to a 15-minute delay after a follow-up becomes due.
- Check the `next_step_due` column in the sheet -- the follow-up won't be sent until that time has passed.
- Verify A3 is running: log in to Make.com and check the A3 automation is active (green toggle).

### "An enquiry was marked as cold too quickly"
- Check the `priority` column. Hot leads move through the sequence faster than standard leads.
- If the cadence feels too aggressive, the timing can be adjusted. Contact your automation specialist.

### "A follow-up went out after someone replied"
- This can happen if the reply arrived in the few minutes between A2's last check and A3's run. See the A2 troubleshooting guide for details.
- It's rare and limited to at most one extra email.

### "The follow-up email didn't have a personalised opening"
- The AI that generates the opening line occasionally has temporary issues. When this happens, the email still sends -- it just skips the personalised opening sentence. This is by design (better to send a slightly less personal email than to delay the follow-up).
- If it happens consistently, check the AI settings in Pipeline Config (see the "What You Can Configure" section in the overview doc).

### "I see errors in the A3 run history"
- If a single email fails to send (e.g., temporary Gmail issue), A3 skips that enquiry and will retry on its next run (15 minutes later).
- If the Google Sheet update fails, A3 retries up to 3 times to make sure the step tracking stays accurate.
- If errors persist, check that both the Gmail and Google Sheets connections are active in Make.com.

---

*Version 3.1 | Last updated: 23 March 2026*
