# A2: Reply Detection & Stop

## What It Does

This automation watches your Gmail inbox for new emails. Every 5 minutes, it checks whether any incoming email is a reply from someone in your tracking sheet. If it finds a match, it immediately stops all automated follow-ups for that enquiry — so you never send an automated email to someone who's already in conversation with you.

**Runs:** Every 5 minutes, automatically.

---

## What Happens Step by Step

1. **Inbox check** — Every 5 minutes, the automation looks at any new emails that have arrived in your shared Gmail inbox
2. **Sender lookup** — For each new email, it checks whether the sender's email address matches anyone in your tracking sheet
3. **Match found?**
   - **Yes, and follow-ups are still active** → The enquiry is marked as "replied" and follow-ups are stopped
   - **Yes, but already stopped** → No action (already handled)
   - **No match** → Ignored (it's an email from someone not in the tracking sheet — a colleague, a supplier, etc.)

---

## What You'll See

When A2 detects a reply:

- **In the Google Sheet:** The matching enquiry row will update:
  - `stopped` changes from `FALSE` to `TRUE`
  - `status` changes to `replied`
- **In your inbox:** Nothing changes — you'll see the reply as normal. The only difference is that the system won't send any more automated follow-ups to that person.

---

## Why This Matters

Without reply detection, the system would keep sending follow-up emails even after someone has already replied and started a conversation with your team. That would feel impersonal and spammy — the opposite of what you want.

With A2 running every 5 minutes, the maximum delay between someone replying and follow-ups stopping is 5 minutes. In practice, it's usually faster.

---

## Troubleshooting

### "Someone replied but they still got another follow-up"
- There's a small window (up to 5 minutes) between when a reply arrives and when A2 detects it. If the follow-up automation (A3) happened to run in that exact window, one extra email may have gone out. This is rare and unavoidable with a polling interval.
- Check the Google Sheet — if `stopped` is now `TRUE` and `status` is `replied`, A2 did its job. The extra email was sent before the detection happened.

### "Follow-ups didn't stop even though the person replied"
- **Check the email address.** The reply must come from the exact same email address listed in the Email column of the tracking sheet. If someone replies from a different address (e.g., a personal email instead of their work email), A2 won't match it.
- **Check A2 is running.** Log in to Make.com and verify the A2 automation is active (green toggle). Look at the run history — is it running every 5 minutes?
- **Check the Gmail connection.** If the connection expired, A2 can't read the inbox. Go to Connections → Gmail → Reauthorize if needed.

### "A2 shows errors in the run history"
- If Google Sheets is temporarily unavailable, A2 will skip that cycle and try again in 5 minutes. One missed cycle isn't a problem.
- If errors persist, check that the Google Sheets connection is still active and that the spreadsheet hasn't been moved or renamed.

---

*Version 2.0 | Last updated: 25 February 2026*
