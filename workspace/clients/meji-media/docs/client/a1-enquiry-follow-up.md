# A1: Enquiry Follow-Up Sequence

## What It Does

When someone submits an enquiry through your website, this automation kicks in instantly. It logs the enquiry to your Google Sheet, scores the lead, generates a personalised AI opening line, and sends an appropriate first email -- all within seconds of the form being submitted.

**Runs:** Instantly, every time a form is submitted.

---

## What Happens Step by Step

1. **Enquiry received** -- The automation receives the form data the moment someone submits it on your website
2. **Logged to Google Sheet** -- A new row is created in your tracking sheet with all the enquirer's details (name, email, phone, topic, organisation, message), a unique enquiry ID, and a timestamp
3. **Lead scored** -- The system calculates a lead score based on 9 configurable factors from the enquiry details. This determines the priority: hot, warm, or standard
4. **A/B variant assigned** -- If A/B testing is enabled, the enquiry is randomly assigned to Group A or Group B. This determines which email version they receive throughout the entire sequence
5. **AI personalisation** -- The system generates a unique opening sentence for the email, referencing the enquirer's specific topic. If the AI is temporarily unavailable, the email still sends -- just without the personalised opener
6. **Email sent** -- Based on the priority:

| Priority | What Gets Sent |
|----------|----------------|
| **Hot** (score 50+) | **Your team** receives an instant notification email with full enquiry details, priority score, and a prompt to follow up quickly. **The enquirer** receives a warm, personalised acknowledgement. Follow-ups are stopped -- your team handles it from here. |
| **Warm / Standard** | The enquirer receives a friendly acknowledgement email. The system schedules the next follow-up (A3 handles this). |

7. **Done** -- The website form receives a confirmation that everything went through successfully

---

## What You'll See

When A1 runs successfully:

- **In the Google Sheet:** A new row with all fields filled in. The `status` column will show `new` (or `handoff` for hot leads). The `priority` column will show `hot`, `warm`, or `standard`.
- **In your Gmail inbox:** The sent email will appear in your Sent folder (since it's sent from your shared inbox). The email will have a personalised opening sentence that references the enquirer's specific topic.
- **For hot leads:** Your team will receive a separate notification email with a subject like "HOT LEAD: Sarah Thompson - Wedding DJ (Score: 85)"

---

## Before and After

### Before (Manual Process)
1. Enquiry arrives via form -> CRM logs it
2. SendGrid sends a generic auto-confirmation
3. Staff manually reads the enquiry
4. Staff decides priority
5. Staff writes and sends a personalised email
6. **Hours or days pass** before the first real response

### After (Automated)
1. Enquiry arrives via form
2. Within seconds: logged, scored, AI-personalised email sent (opening line references their specific enquiry)
3. Hot leads: team notified immediately with full context
4. Staff only needs to step in when someone replies

---

## Troubleshooting

### "An enquiry came in but no email was sent"
- Check the A1 automation in Make.com -- click on it and look at the run history. If the most recent run shows an error (red), the issue will be described there.
- Most common cause: the Gmail connection expired and needs to be reconnected. Go to Make.com -> Connections -> find Gmail -> click "Reauthorize".

### "The enquiry isn't in the Google Sheet"
- Check that the form is actually submitting to the automation. The submission link in your website form must match the one configured in A1.
- If the form is correct, check the A1 run history -- if Google Sheets was temporarily unavailable, the email may still have been sent even though the row wasn't created.

### "The lead was scored as standard but should have been hot"
- Lead scoring is based on the information provided in the form. If the enquiry details didn't meet the scoring thresholds, it will be scored lower.
- The scoring weights and thresholds can be adjusted -- contact your automation specialist.

### "I got a team notification for a lead that isn't actually high-value"
- The scoring system uses the information available at submission time. You can adjust the handoff threshold to be more or less sensitive.

---

*Version 3.0 | Last updated: 6 March 2026*
