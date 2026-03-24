# System Thinking

The core differentiator. Most freelancers say "connect A to B." You design the flow, logic, edge cases, and failure handling.

## Step 1 — Distill the Job Post

Translate messy client language into system components.

**Client says:** "I need help with emails and automation"

**You translate to:**
- Trigger source? (form, CRM event, schedule, webhook)
- Routing logic? (conditions, segmentation, priority)
- Personalization? (dynamic fields, templates, merge tags)
- Sending infrastructure? (SMTP, API, platform)
- Tracking? (opens, clicks, bounces, deliverability)

**Client says:** "Connect Typeform to HubSpot"

**Freelancer hears:** "Use Zapier"

**You hear:**
- Validate fields before writing
- Check for duplicates against existing records
- Map form schema to CRM schema
- Log failures for visibility
- Handle retries on API errors

## Step 2 — Build the Pipeline

Break every job into: **Input -> Process -> Output**

Example:
```
Input:    Form submission (webhook)
Process:  Validate -> Enrich -> Deduplicate -> Route
Output:   CRM entry + Notification + Follow-up email
```

Name each stage. Identify what data transforms happen at each step. This becomes your video walkthrough structure.

## Step 3 — Create the Anchor Artifact

Pick ONE concrete thing to show the client:

| Artifact | Best for |
|----------|----------|
| Flow diagram | Complex multi-step systems |
| Partial build | Jobs where you can demo in the tool |
| Structured breakdown | When the job needs clarification |
| Loom walkthrough | Almost always (default choice) |

The artifact is the proof. Everything else (proposal text, follow-ups) supports it.

## Step 4 — Build Around It

- Proposal = intro to the artifact
- Video = explanation of the artifact
- Follow-up = clarification of the artifact

One artifact. One system. One clear thread.

## Edge Case Thinking

For every pipeline, ask three questions:

1. **What breaks?** — Invalid data, API downtime, rate limits, auth expiry, schema changes
2. **What scales poorly?** — Sequential processing, polling intervals, manual steps, hard-coded values
3. **What's missing?** — Error visibility, retry logic, logging, deduplication, idempotency

Name these in your video. This is what separates "connect A to B" from systems thinking.

## Example Decomposition

**Job post:** "Need help automating lead capture and CRM integration"

### Decomposition:
```
1. Capture:     Where do leads come from? (form, chat, API, email)
2. Validation:  What makes a lead valid? (required fields, format, domain)
3. Enrichment:  What data do we add? (company info, social, scoring)
4. Dedup:       How do we prevent duplicates? (email match, phone match)
5. Routing:     Where does the lead go? (CRM, notification, sequence)
6. Follow-up:   What happens next? (auto-email, task creation, alert)
7. Visibility:  How do we know it's working? (logging, dashboard, alerts)
```

### Video structure from this:
"Here's how I'd structure your lead pipeline..." → walk through each stage → name the failure points at stages 2 and 4 → show the output at stages 5-6 → close.