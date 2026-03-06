# Inbound Processing

Processes client responses to extract decisions, resolve open items, flag implications, and maintain conversation continuity. Invoked via `/comms {client} inbound`.

---

## Step 1: Accept Input

The user will provide client messages in one of these ways:
- **Paste a chunk of chat** — may include multiple messages, possibly more than just the new ones
- **Describe what was said** — "Anuj replied that the CRM uses Zapier"
- **Paste a single message** — just the new reply

Accept whatever format they give. Don't ask them to reformat.

---

## Step 2: Deduplicate Against Comms Log

**This step is critical.** Users will often over-paste — selecting a larger portion of the chat thread because it's faster than surgically finding just the new part.

1. Read `workspace/clients/{client}/context/comms-log.md`
2. Compare the pasted content against existing log entries:
   - Match by content similarity (summaries of logged entries vs pasted messages)
   - Match by date/time if timestamps are visible in the paste
   - Match by sender names
3. Identify which messages are **already logged** vs **genuinely new**
4. Report to the user: "I see N messages pasted. M are already in the log. Processing the K new ones."
5. If everything appears to be already logged, say so: "These all look like they're already captured in the log. Is there something new I'm missing?"

**If no comms-log exists yet:** Everything is new. Note this and proceed.

---

## Step 3: Detect Gaps

Compare timestamps between the last comms-log entry and the first new message.

- **Same day or next day:** No gap. Proceed normally.
- **2-3 day gap:** Minor. Mention it briefly: "Last logged contact was March 2, this is from March 5. Anything happen in between?"
- **Week+ gap:** Flag it: "There's a week gap since the last logged conversation. Were there messages in between you want to capture?"

Don't block on this. Surface it, let the user decide, and continue processing.

---

## Step 4: Extract From New Messages

For each genuinely new message, extract:

### Facts
Concrete information that updates the project understanding.
- Technical details ("CRM uses Zapier", "payload has 4 fields")
- Preferences ("they want weekly reports, not daily")
- Contact info, access details, credentials shared

### Decisions
Explicit choices the client made.
- "Go with Option 1"
- "We'll handle the website changes ourselves"
- "Let's skip the A/B testing for now"

### Action Items
Things someone committed to doing.
- "Anuj will send the API docs by Friday"
- "Gurmej will set up the Gmail access"
- Client asked you to do something specific

### Questions
New questions the client asked that need answering.

### Tone/Sentiment (note, don't log)
How are they feeling? Frustrated? Enthusiastic? Confused? This informs the next `/draft` but doesn't go in the log explicitly.

---

## Step 5: Sanity Check the Input

**Check the client's statements against known project state.** This is where you push back or flag issues.

### Contradiction Check
If the client says something that contradicts known project state:
- "Client says 'the webhook is working' but spec shows A1 is still in build stage. Worth clarifying?"
- "They mention 'the daily emails' but A2 is configured for 5-day follow-ups, not daily."

### Feasibility Check
If the client requests or confirms something that has technical implications:
- "They're asking for real-time sync but the current architecture is batch-based. This would be a significant scope change."
- "They want to add 3 more email templates. This is straightforward — just add rows to the Email Templates data store."

### Ambiguity Check
If what they said is unclear or could be interpreted multiple ways:
- "Anuj says 'the data goes through our system.' Unclear if that means Zapier, custom API, or manual entry. Worth clarifying before building."
- "Gurmej says 'make it automatic.' Unclear if they mean scheduled or triggered by an event."

### Unblock Check
If what they said resolves a known blocker or open item:
- "This confirms the webhook format. A1 webhook parsing is now unblocked."
- "Templates received. Email content creation can proceed."

Present all flags clearly. Don't bury them.

---

## Step 6: Identify Implications

Map extracted content to project impact:

### Spec Implications
- Does a decision require a spec update? Flag which spec and what changes.
- "Decision to skip A/B testing means spec a3 needs the A/B section removed."
- Don't auto-update specs. Present the implication and let the user decide.

### Infrastructure Implications
- Does new information change the architecture?
- "Zapier webhook format means A1 needs a different JSON parser than planned."
- "They want a third venue added. Need to update the sheet structure and A1 routing."

**Action:** When a decision has spec impact, include in the log entry:
- `spec_impact: [a1, a3]` — list of affected spec IDs
- Suggest: "Run `/spec-updater {spec-id}` to apply this decision."

### Scope Implications
- Does this expand or shrink scope?
- "Adding real-time sync wasn't in the original spec. This is new scope — approximately 6-8h."
- "Skipping A/B testing reduces the remaining work by about 3-4h."

### Next Action Suggestions
Based on everything extracted, suggest concrete next steps:
- "Update spec a1 to reflect Zapier payload format"
- "Start implementing A1 webhook parsing (now unblocked)"
- "Draft a reply asking Anuj to clarify 'our system'"
- "Load the email templates Gurmej sent into the Email Templates data store"

---

## Step 7: Offer to Log

After presenting the analysis, ask: "Want me to log this?"

If yes, follow COMMS-LOG.md write procedures:
1. Generate one inbound entry per sender (if multiple people replied, separate entries)
2. Include: summary, decisions, implications, resolved items
3. Show the proposed entry(ies) to the user before writing
4. Append to comms-log.md
5. Auto-resolve matching open items

---

## Temporal Context for Reply Drafting

If the user wants to reply after processing inbound messages, pass temporal context to `/draft`:

- **When was the client's message sent?** (extracted from paste if timestamps visible)
- **What time is it now?** (current date/time)
- **How long since they messaged?** (same day, next morning, days later)

This feeds into STYLE-RULES.md temporal opener rules:
- Same-day rapid exchange → no greeting, jump in
- Next morning → "Good morning" / "Morning"
- Days later → context re-establishment opener

---

## Edge Cases

### Multiple People Replied
Process each person's messages separately. Create separate log entries per sender. Flag if different people said contradictory things.

### Client Forwarded Something
If they forwarded an email, shared a screenshot, or referenced something external — note what it is and whether you need the actual content to proceed.

### Very Long Paste
If the user pastes a huge thread, focus on extracting the new and relevant parts. Don't summarize every message. The log entries should be concise.

### No Actionable Content
Sometimes a client just says "thanks" or "sounds good." That's fine. Log it briefly if the user wants ("Gurmej acknowledged the update, no action items") or skip logging.
