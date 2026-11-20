# Checkpoint: Air to Sea Shuttles First Call and Access Plan

**Date:** 2026-11-20
**Status:** First call held 2026-11-18; a1 plan on main; access checklist email drafted, Matthias sends

---

## Summary
Harold Riley agreed on the 2026-11-18 call that Matthias starts with his Google Business Profile and AI-search presence, and asked for pay tied to the revenue the work brings in. This session produced the a1 plan with the access and facts list (PR #1762), the performance-pay structure, and a self-serve access checklist email for Harold.

---

## What Was Done This Session
### Call support
1. Live briefing as Matthias entered the call, then SEO, site-conversion and booking/quoting/follow-up automation ideas against Harold's 11-16 priorities.
2. Performance-pay model: setup fee + share of tracked bookings + monthly minimum + 12-month term + 6-month tail/buyout. The tracked-booking measurement doubles as the booking/quote system he wants, so the deal never needs his books.
3. Logged the 11-18 call in `context/comms-log.md` (terms discussed, no number yet).

### a1 plan (PR #1762, merged 2026-11-18)
1. Checked the live site and DNS: WordPress 7.0.8 + Elementor Pro on Hostinger, Zaui engine at `air2seashuttles.zaui.net`, no analytics/GTM/Search Console, no SEO plugin or structured data, no GBP, no third-party listings, the $55/$45 fare conflict.
2. Verified Zaui's surface (E2): GTM/GA4 supported via Settings > Marketplace; the Google Things to Do connector ruled out (airport transfers excluded).
3. Wrote `status/a1-gbp-ai-search.md`: elements, 12-row access table, facts list, monthly AI-answer baseline prompts.

### Delivery of the asks (2026-11-20)
1. Recommended a screen-share setup call; Matthias chose a self-serve checklist email, invites to the address he mailed Harold from.
2. Drafted `context/drafts/2026-11-20-access-checklist.md` via `/comd_draft`: GBP (create, verify, add Manager), Zaui employee, WordPress Administrator, Hostinger Collaborator, then the questions only Harold can answer. Menu paths checked: Hostinger from its own help, GBP from agreeing setup guides, Zaui from a search excerpt of its help article.
3. Critic flagged 2 imperative-tone phrases, output gate flagged "whether it's"; all fixed in one pass.
4. Status file updated (PR #1794).

---

## Key Decisions Made
### Harold's checklist is only what he alone can do
- **Choice:** He handles GBP, Zaui, WordPress, Hostinger, photos and the owner-only questions. Matthias sets up Search Console, GA4 and GTM himself (DNS via Hostinger) and adds Harold's business Google account as owner/admin.
- **Rationale:** Self-serve delivery fails on long lists; Zaui reports answer bookings per month, value and source, so those questions drop out.

### Measurement before the profile goes live
- **Choice:** Pull the 12-month Zaui baseline and install tracking during Google's verification wait.
- **Rationale:** A profile live before tracking leaves the first uplift unattributable, which is the billing basis of the performance deal.

### Terms after the baseline
- **Choice:** No prices in the checklist mail; the percentage goes in writing once the Zaui numbers are in, and no build work beyond setup before he agrees.
- **Rationale:** The share can't be sized without his booking volume and value.

### Hostinger role Collaborator, not Admin
- **Rationale:** Admin can make purchases with his saved payment method.

---

## What Did NOT Work (and why)
- **WebFetch of Zaui's help article (support.zaui.com/hc/en-us/articles/360044844191):** HTTP 403; the Settings > Employees path came from the search excerpt instead.
- **RDAP registrar lookup piped into python json:** JSONDecodeError; registrar inferred as Hostinger from DNS, hosting and mail.
- **Resolve-DnsName batched with other calls:** auto-mode classifier gave no verdict; reissued alone, it ran.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/air-to-sea-shuttles/status/a1-gbp-ai-search.md | Created (#1762), updated (#1794) | a1 plan, access table, facts, baseline prompts |
| workspace/clients/air-to-sea-shuttles/context/comms-log.md (gitignored) | Edited | 2026-11-18 call entry |
| workspace/clients/air-to-sea-shuttles/context/drafts/2026-11-20-access-checklist.md (gitignored) | Created | Checklist email, not sent |

---

## Current Status
- Checklist email drafted; `[YOUR EMAIL]` still a placeholder. Not sent.
- No pay terms agreed in writing.
- Ops status: air-to-sea-shuttles has no infrastructure.yaml (no orchestrator yet; expected at this stage).

---

## Next Steps
1. Matthias makes sure a Google account exists on his invite address, fills the placeholder, sends the checklist; log the sent copy verbatim and mark the Access element sent.
2. On Zaui + Hostinger access: pull the 12-month baseline by source and value, run the AI-answer baseline prompts, install tracking (tagged GBP booking link, GA4/GTM on site and in Zaui).
3. Send the pay terms in writing with a percentage sized on the baseline.
4. After GBP verification: follow-up mail for Bing Places and Apple Business Connect; then the profile build, site SEO basics and route/FAQ pages.
5. Raise the $55/$45 fare conflict on the next call if it didn't come up on 11-18.

---

## Context for Next Session
### Files to Read First
- workspace/clients/air-to-sea-shuttles/status/a1-gbp-ai-search.md
- workspace/clients/air-to-sea-shuttles/context/comms-log.md
- workspace/clients/air-to-sea-shuttles/context/drafts/2026-11-20-access-checklist.md

### Open Questions
- Which address Matthias mails Harold from (Zoho Mail; unknown here).
- Was the fare conflict raised on the 11-18 call?
- Can GBP managers be added before verification? The draft says "once it's verified" to be safe.

### Working Notes
- Zaui says extra user accounts carry no per-user fee (its own marketing; unconfirmed for Harold's plan), so it was left out of the mail.
- Bing Places imports from GBP, so it follows verification at low cost.

### Reference Materials
- https://air2seashuttles.com
- https://support.google.com/business/answer/9272778
- https://www.hostinger.com/support/1583777-how-to-share-access-to-your-account-at-hostinger/

---

## How to Continue
`/comd_resume air-to-sea-shuttles`. Wait for Matthias to confirm the send, then log it; build nothing until Harold's access arrives.

---

## Strategic Feedback

### What Worked Well This Session
- Cutting Harold's list to what only the owner can do (Zaui reports replace half the facts, Matthias sets up the Google tools) made the self-serve route viable instead of a 12-item homework list.

### Suggestions
- The client-comms skill wants `context/comms-profile.md`, which this prospect lacks; the 11-16 and 11-20 drafts both ran without one. Create it at the first paid engagement, from the comms log, without the setup interview.

### System Health
- The critic caught 2 imperative-tone phrases that the output validator passed; the second-agent gate earns its place for outbound mail.
- Autonomy: 1 human intervention (delivery format + invite address decision).
