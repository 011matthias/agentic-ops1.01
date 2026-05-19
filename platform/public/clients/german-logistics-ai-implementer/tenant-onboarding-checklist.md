# Tenant onboarding checklist

A working checklist I use to take a logistics tenant from sold to live on the AI-OS, end to end. Reusable, the same shape each time, tuned per tenant where it matters.

Prepared by Matthias, UnpauseAI. Karlsruhe, Germany. 2026.

---

## Step 0: Before kickoff (your side)

- [ ] Contract or scope memo signed with the tenant.
- [ ] Tenant's primary contact named (the person I'll be on the onboarding call with).
- [ ] Tenant slot reserved on the AI-OS roadmap (you confirm I can scaffold).
- [ ] Bonus criteria for the 30-day check agreed in writing (what counts as "successful onboarding").

---

## Step 1: Kickoff intake (async, 1 to 2 hours)

Tenant information I collect via the Get-started form or a written exchange.

- [ ] Tenant company name + industry sub-segment (freight forwarding, last-mile, warehousing, etc.).
- [ ] Primary contact: name, email, phone, preferred language.
- [ ] Inbound channels in scope for this tenant (email/IMAP, Amazon Message Center, web form, other).
- [ ] IMAP/SMTP credentials (received through a secure channel of their choice, not via a plain form).
- [ ] Branding: logo file or URL, brand colors, sender display name, signature block.
- [ ] Module flags: which AI-OS modules are enabled for this tenant.
- [ ] German tone / terminology: formal "Sie" vs informal "du", specific terms they use (Sendung vs. Lieferung, Lieferschein vs. Frachtbrief, etc.).
- [ ] Business rules: escalation triggers, refund / return rules, opening hours.
- [ ] Escalation contacts: name and email of human(s) who handle handoffs.
- [ ] Test data: 5 to 10 representative real tickets I can use for dry-run tuning.

---

## Step 2: Tenant scaffold (2 to 3 hours)

Configuration work inside the AI-OS.

- [ ] Tenant record created with branding applied.
- [ ] Module flags set per intake.
- [ ] IMAP credentials wired, inbound test from a real address reaches the configured queue.
- [ ] SMTP credentials wired, outbound test reaches a real inbox.
- [ ] Sender display name + signature block configured.
- [ ] Per-tenant prompt template inheriting the base, branding-customized where it matters.
- [ ] Job queue (ARQ/Redis) processes a test ticket end to end without errors.
- [ ] Error logging hooked to a place I can read it for the first weeks.

---

## Step 3: Workflow customization (2 to 4 hours)

Adapting the AI-OS prompts and rules to fit this specific tenant.

- [ ] Prompt template adapted to the tenant's voice (formal vs informal, brand-specific terminology).
- [ ] Confidence thresholds tuned on dry-run tickets, what auto-replies and what escalates.
- [ ] Escalation rules wired (who gets pinged, in what channel, with what context).
- [ ] Edge cases sampled from real tickets, model judgment checked against expected outcome.
- [ ] Per-tenant business rules in place (special carrier handling, regional shipping quirks, etc.).
- [ ] Dry-run pass: 5 to 10 representative tickets processed, outcomes reviewed with you.

---

## Step 4: Onboarding call in German (60 to 90 minutes)

The customer-facing call I run with the tenant's primary contact and stakeholders.

- [ ] Calendar invite sent in German with agenda.
- [ ] Recording set up (only if tenant confirms in writing).
- [ ] Agenda:
  - Walkthrough of their configured tenant inside the AI-OS.
  - Live IMAP/SMTP test: send a real test ticket from their inbox, watch the AI-OS reply.
  - Walk through one real ticket end to end, including the escalation path.
  - Q&A.
  - Set their expectations for the first 2 weeks (what they'll see, when to flag what).
- [ ] Post-call summary email in German, sent within 24 hours, restating decisions made on the call.

---

## Step 5: First weeks of support (2 hours per week, 2 to 4 weeks)

- [ ] Slack or email channel set up with their primary contact and at least one escalation contact.
- [ ] Daily error-log check for the first 14 days, anything unexpected gets flagged the same day.
- [ ] Weekly summary email in German: what triggered, what was auto-handled, what needed human attention, anything that should be tuned.
- [ ] Tuning rounds applied as patterns emerge, never silent changes, tenant confirms each tuning.
- [ ] Onboarding-call recording (if any) shared with the tenant for their reference.

---

## Step 6: 30-day quality check (1 hour)

Joint review with the tenant and with you.

- [ ] Pull the 30-day stats from the AI-OS: tickets handled, escalation rate, false-positive escalations, response-time distribution.
- [ ] Compare to the bonus criteria agreed in Step 0.
- [ ] Identify what worked, what surprised us, what to change for tenant N+1.
- [ ] Decide together: bonus criteria met or not, and what the next 30 days look like.
- [ ] If criteria are not met: written postmortem within 1 week, with concrete tuning items, not vague intentions.

---

## Cross-tenant maintenance

Things I track across all tenants to keep the playbook getting tighter.

- [ ] Pattern library: edge cases seen at one tenant that might apply elsewhere.
- [ ] Prompt-template versions: which version of the base prompt each tenant is on, when it was last touched.
- [ ] Tenant-to-tenant config diff: what's actually different per tenant vs what should be standardized.
- [ ] Sustainable cadence: one tenant every 2 to 3 weeks is the comfortable pace. Two in parallel is doable. Three in parallel only if onboarding calls are spaced by a week minimum.
