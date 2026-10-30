# Checkpoint: Air to Sea Shuttles Enquiry

**Date:** 2026-10-30
**Status:** First enquiry sent; waiting for Harold Riley's reply

---

## Summary
Matthias met Harold Riley, founder of Air to Sea Shuttles LLC (Houston), who mentioned needing automation work. We wrote a first-contact email that names Nicolas Neumann and UnpauseAI and asks for a 20-minute call. Matthias sent it, and it is logged verbatim in a new comms log for the prospect.

---

## What Was Done This Session
### Prospect research
1. Read the business card screenshot: sales@air2seashuttles.com, 832-838-1186, 844 AIRSEA2, air2seashuttles.com.
2. Read the company's own site. It sells flat-rate group transport from IAH and Hobby to the Galveston cruise terminals and hotels. Groups of six or more are told to call for a custom quote. Pickups are timed to flights and sailings. The site does not name Harold.

### Outbound
1. First draft had bracketed placeholders plus three fill-in notes. Matthias asked for the email itself, so the second version is ready to send and uses general wording for anything unknown.
2. Matthias reported it sent. It is logged verbatim, with the sending address still TBD.

---

## Key Decisions Made
### No prices, meeting ask only
- **Choice:** The email names the flows we would start with and asks for a 20-minute call, or for Nicolas to visit.
- **Rationale:** The first-letter rule is no prices and aim for a meeting. Nicolas being in Texas makes an in-person offer credible.

### Fare mismatch kept for the call
- **Choice:** His rates page shows two different IAH-to-Galveston shared fares ($55 and $45 one way). That stays out of the email and is noted in the comms log for the call.
- **Rationale:** Pointing out a website error in a first email reads as criticism.

### Prospect home
- **Choice:** Created the gitignored comms log at `workspace/clients/air-to-sea-shuttles/context/comms-log.md`. No status folder and no infrastructure.yaml for now.
- **Rationale:** The house convention keeps sent messages verbatim in a comms log. The referral ledger is for referrers, not prospects. One email does not make a workstream yet.

---

## What Did NOT Work (and why)
- **A ripgrep-only flag passed to GNU grep:** The `block-grep-no-ignore` pattern rule blocked the command. GNU grep exits 2 on that flag, and the stderr redirect would have hidden the failure as "not found". Reran with rg.
- **The same pattern rule on a heredoc:** It also blocked the Bash heredoc that wrote this checkpoint, because the prose quoted the flag next to the word grep. Wrote the file with the Write tool instead.
- **Reading `workspace/projects/platform/context/brand.md`:** The file does not exist. This checkout was 94 commits behind, and the rules on origin/main no longer reference that file. Used rule_platform_standards §1 for the contact address instead.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/air-to-sea-shuttles/context/comms-log.md (main clone, gitignored) | Created | Prospect facts and the sent email, verbatim |
| docs/2026-10-30 - Air to Sea Shuttles Enquiry/Checkpoint.md | Created | This checkpoint |

---

## Current Status
- **Enquiry:** sent 2026-10-30, sending address not confirmed.
- **Reply:** none yet.
- **Ops status:** air-to-sea-shuttles has no infrastructure.yaml. That is expected for a prospect with no orchestrator.

---

## Next Steps
1. When Harold replies, log his message verbatim in the comms log and process it with `/comd_comms air-to-sea-shuttles`.
2. Fill in the sending address in the comms log once Matthias confirms it.
3. If a call is booked, read his site's booking and quote flow first, and bring up the $55/$45 fare mismatch in person.

---

## Context for Next Session
### Files to Read First
- workspace/clients/air-to-sea-shuttles/context/comms-log.md

### Open Questions
- Which address the email went out from.
- Who leads this engagement if it lands: Matthias, Nicolas, or both. It also matters which Texas city Nicolas is in, because the email offers an in-person visit.

### Working Notes
- Likely first automation targets, inferred from the site and not yet confirmed by Harold: phone-only group quotes for six or more, and booking intake tied to flight and sailing times.

### Reference Materials
- https://air2seashuttles.com

---

## How to Continue
`/resume air-to-sea-shuttles` loads the comms log. Do nothing until Harold replies, and draft no follow-up unless Matthias asks.

---

## Strategic Feedback

### What Worked Well This Session
- The email's specifics came from the prospect's own site, not a directory, which is why it can say that group quotes go by phone and pickups follow flights and sailings.

### Suggestions
- When asked for a draft to send, hand over a send-ready version first and list optional swaps after it. The first version here had bracketed placeholders, and Matthias had to ask again for the actual email.
- The missed-session-header row has now regressed at least eight times on a documented fix. It needs a structural check, for example a Stop-hook pass that looks for the header pattern in the session's first assistant text, rather than another register row.
- The `block-grep-no-ignore` rule fires on prose inside a heredoc. Anchoring its pattern to a grep command position, rather than anywhere in the command string, would stop that false positive.

### System Health
- **Autonomy:** 1 human intervention ("give me the email").
