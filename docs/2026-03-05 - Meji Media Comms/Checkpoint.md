# Checkpoint: Meji Media Comms

**Date:** 2026-03-05
**Status:** Integration — waiting on client DB credentials

---

## Summary
Processed multi-day inbound conversation with Meji Media's developer (Anuj) to determine the integration path for connecting Christmas Office Party enquiry forms to the Make.com automation. Diagnosed that the site is PHP/CodeIgniter/MySQL (not WordPress), evaluated integration options, and arrived at MySQL polling via Make.com's native MySQL module. Currently waiting on DB credentials and IP whitelisting.

---

## What Was Done This Session
### Client Communication
1. Processed Anuj's initial reply: "no webhooks or APIs, data goes directly to database"
2. Ran technical sanity check on integration options (WordPress plugins, DB triggers, Make MySQL polling, cURL in controller)
3. Discovered DB triggers are an anti-pattern for HTTP (MySQL has no native HTTP capability) — removed from options
4. Learned site is PHP + CodeIgniter + MySQL — eliminated all WordPress-based approaches
5. Presented two options: (A) cURL in CodeIgniter controller, (B) Make polls MySQL directly
6. Anuj chose Option B (MySQL polling) — "easier to maintain"
7. Provided MySQL requirements checklist (5 items) to Anuj
8. Looked up Make.com EU2 IP addresses for whitelisting (initially pulled EU1 — caught and corrected)
9. Drafted and iterated multiple messages, applying style rules (no em-dashes, no banned phrases, Upwork formatting)

### Technical Findings
1. Make.com EU2 IPs for whitelisting: 34.254.1.9, 52.31.156.93, 52.50.32.186
2. Database name revealed by Anuj: `xmas_2020`
3. Anuj confirmed external DB access is feasible (already done for Looker)
4. A/B testing: user committed to Option 1 (spreadsheet summary tab)

---

## Key Decisions Made
### Integration Approach: Make MySQL Polling
- **Choice:** Make.com polls the client's MySQL database directly (Option B)
- **Rationale:** No code changes on client side, Anuj preferred it for maintainability. 5-10 min delay is acceptable for follow-up email system.

### A/B Testing Reporting: Spreadsheet Summary Tab
- **Choice:** Option 1 (analytics tab in the spreadsheet)
- **Rationale:** Simpler, no additional automation to maintain. Can upgrade to automated weekly report later.

### IP Zone Correction
- **Choice:** EU2 IPs (not EU1) for whitelisting
- **Rationale:** Client org 5473701 is on eu2.make.com. Automations will be ported to client's Make instance.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| This checkpoint | Created | Session continuity |

---

## Current Status
- **Blocking on client:** Anuj asked for IPs to whitelist (we have them ready: EU2). Gurmej needs to create read-only MySQL user and share credentials.
- **Conversation state:** Anuj asked for IPs at 1:01 PM. Gurmej said "lets wait for the IPs" at 3:40 PM. Ball is in our court to send the IPs.
- **Comms log needs update:** Multiple exchanges from Mar 3-5 not yet logged (user hasn't approved logging yet).

### Checklist Status (from Anuj)
| # | Item | Status |
|---|------|--------|
| 1 | MySQL host and port | Pending |
| 2 | External connections allowed | Confirmed (done for Looker) |
| 3 | Database name | `xmas_2020` (revealed by Anuj) |
| 4 | Enquiry table name | Pending |
| 5 | Read-only username and password | Pending (Gurmej to create) |

### Other Open Items
- Email templates x4 from Gurmej (no update yet)
- Message with EU2 IPs ready to send but not yet sent

---

## Next Steps
1. **Send EU2 IPs to Anuj** (draft ready, user approved content)
2. **Log all comms** from Mar 3-5 to comms-log.md (ask user first)
3. **Receive MySQL credentials** from Gurmej/Anuj once IP whitelisting is done
4. **Build MySQL polling scenario** in Make.com once credentials arrive
5. **Port A1/A2/A3 scenarios** to client's Make instance (eu2, org 5473701)
6. **Build A/B analytics tab** in Google Sheet (Option 1)
7. **Receive email templates** from Gurmej and update DS 98605

---

## Context for Next Session
### Files to Read First
- `workspace/clients/meji-media/context/comms-log.md` — conversation history (needs updating)
- `workspace/clients/meji-media/context/comms-profile.md` — contact details and tone
- `workspace/clients/meji-media/context/infrastructure-ids.md` — Make.com IDs, connections, data stores
- `workspace/clients/meji-media/specs/a1-enquiry-follow-up-sequence.md` — A1 spec (trigger type will change from webhook to MySQL polling)

### Open Questions
- What is the enquiry table schema in `xmas_2020`? (will discover via DESCRIBE once connected)
- Will A1's trigger be modified from webhook to MySQL, or will a new bridge scenario poll MySQL and POST to the existing A1 webhook?
- Does the hosting allow external MySQL connections on port 3306, or is there a non-standard port?

### Reference Materials
- Make.com IP whitelist docs: https://help.make.com/allow-connections-to-and-from-make-ip-addresses
- EU2 IPs: 34.254.1.9, 52.31.156.93, 52.50.32.186
- Plan file: C:\Users\neuma\.claude\plans\immutable-dreaming-sunbeam.md

---

## How to Continue
1. Run `/resume meji-media` to reload context
2. Check if Anuj/Gurmej have responded with MySQL credentials
3. If credentials received: connect Make to MySQL, build polling scenario, port automations to eu2
4. If not: follow up on IP whitelisting and credentials

---

## Strategic Feedback

### What Worked Well This Session
- User caught the EU1/EU2 IP mistake before sending — good instinct to verify technical details
- Iterative draft refinement worked well: each round got tighter and more accurate
- User's push to sanity-check technical claims prevented sending incorrect DB trigger advice to the client

### Suggestions
- Consider logging comms entries incrementally (after each exchange) rather than batching — prevents the log from falling behind during active conversations

### System Health
- Comms log is stale (last entry Mar 2, but active conversation through Mar 5). The skill's style rules caught a banned phrase ("don't hesitate to") but only after the message was sent. Consider adding a pre-send validation step to the workflow.
