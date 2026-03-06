# Email Reply Handler

Automatically processes email replies and bounces from your cold email campaigns in Smartlead, categorizing responses and creating follow-up tasks.

## What This Does

When leads reply to your Smartlead campaigns, this automation instantly:

1. **Categorizes the response** using AI (interested, meeting request, out of office, etc.)
2. **Updates your CRM** with the interaction details
3. **Extracts phone numbers** from email signatures
4. **Creates call tasks** for positive responses
5. **Routes to LinkedIn** if emails bounce and LinkedIn is available

**Runs:** Instantly when a lead replies or email bounces (webhook-triggered)

## How It Works

### For Email Replies

1. **Receives notification** - Smartlead sends a webhook when someone replies to your campaign
2. **Filters internal emails** - Ignores replies from your own team (@herbox.se, @herbox.com)
3. **Updates contact** - Finds the contact in Airtable or creates a new one
4. **Logs the interaction** - Records the full email conversation
5. **AI categorizes** - Uses OpenAI to understand the type of reply (interested, not interested, out of office, etc.)
6. **Extracts contact info** - Pulls phone numbers from email signatures
7. **Creates tasks** - Automatically creates call tasks for positive replies or when phone numbers are found

### For Email Bounces

1. **Receives bounce notification** - Smartlead alerts when an email bounces
2. **Checks for LinkedIn** - Looks up the contact in Airtable
3. **Routes to Heyreach** - If LinkedIn URL exists, adds the contact to the appropriate LinkedIn outreach campaign

## What You'll See

When this automation runs successfully, you'll see:

### In Airtable

- **Contacts table:** New contacts created or existing ones updated with:
  - Last Replied Date
  - Phone numbers (if found in signature)
- **Interactions table:** New record for each reply with:
  - Full email conversation
  - Timestamp
  - Channel: "Cold Email"
- **Tasks table:** New call tasks with:
  - Linked contact
  - Task Type: "Call"
  - Status: "To Do"

### In Dashboard

- Execution logs showing each step
- Categorization results
- Phone numbers extracted
- Tasks created

## Email Categories

The AI categorizes replies into these types:

| Category | What It Means | Follow-up Action |
|----------|---------------|------------------|
| **Interested** | Shows interest, mentions pricing/demo | ✅ Call task created |
| **Meeting Request** | Explicitly requests meeting/call | ✅ Call task created |
| **Not Interested** | Clearly declines | Phone extracted if available |
| **Do Not Contact** | Requests removal | No follow-up |
| **Information Request** | Asks questions, wants details | Phone extracted if available |
| **Out Of Office** | Auto-reply, temporary unavailability | 🔄 Routes to LinkedIn campaign |
| **Wrong Person** | Not the right contact | No follow-up |
| **Uncategorizable** | Unclear or very short reply | Manual review needed |

## Example

### Before (Manual Process)

1. Check Smartlead for new replies
2. Read each reply to understand intent
3. Copy email to CRM
4. Look for phone numbers in signature
5. Create reminder to call if positive
6. If bounce, manually add to LinkedIn campaign

⏱️ **Time per reply:** 5-10 minutes

### After (Automated)

1. Lead replies to your email
2. Automation processes instantly
3. Contact updated in Airtable
4. Call task created if positive
5. Phone number extracted and saved

⏱️ **Time per reply:** 0 seconds (automatic)

## Status Meanings

When you check the dashboard, you may see these statuses:

| Status | What It Means |
|--------|---------------|
| Success | Reply processed, contact updated, tasks created |
| Internal email filtered | Reply was from your team, safely ignored |
| Failed | Something went wrong - check logs for details |

## Special Features

### Internal Email Filtering

The automation is smart enough to ignore replies from your own team. If someone at @herbox.se or @herbox.com replies, it's automatically filtered out to prevent false signals.

### Intelligent Phone Extraction

When extracting phone numbers from signatures, the AI:
- Filters out Herbox team members' phone numbers
- Normalizes to international format (+31 6 1234 5678)
- Associates phone numbers with the correct person
- Only extracts external contact information

### LinkedIn Fallback

If an email bounces but the contact has a LinkedIn URL in Airtable, they're automatically added to your LinkedIn outreach campaign in Heyreach (routed to Patrick or Koen's campaign based on the original sender).

## Troubleshooting

### "Contact not created after reply"

**Check:**
- Is the reply from an internal email? (Will be filtered)
- Check the automation logs for errors
- Verify Airtable connection is working

**Solution:** Most replies should auto-create contacts. If missing, check logs for specific error.

### "Phone number not extracted"

**Possible reasons:**
- Phone not in signature or formatted unusually
- Phone belongs to internal Herbox team member (filtered)
- Email body is very short or image-based

**Solution:** Phone extraction works best with formatted signatures. You can manually add phones to the contact record.

### "Wrong category assigned"

The AI is highly accurate but occasionally misclassifies ambiguous replies.

**Solution:** Categories are logged in the Interactions table. You can manually review and adjust follow-up if needed.

### "No task created for interested reply"

**Check:**
- Was reply categorized as "Interested" or "Meeting Request"? (Check Interactions)
- Look in Tasks table filtered by the contact

**Solution:** If category is correct but task missing, check automation logs for task creation step.

## Internal Configuration

This automation uses:
- **Smartlead webhooks** - Instant notifications
- **OpenAI GPT-4o-mini** - Fast, cost-effective AI categorization
- **Airtable API** - CRM updates
- **Heyreach API** - LinkedIn campaign routing

Your team manages these integrations via environment variables. No action needed unless changing providers.

## Questions?

If you have questions about this automation:
- Check the **dashboard logs** at `/logs` for recent activity
- Review the **Interactions table** in Airtable for categorization details
- Contact your automation team if persistent issues occur

---

*Last updated: 2026-01-15*
*Version: 1.1.0*
