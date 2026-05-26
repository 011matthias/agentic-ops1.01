# Checkpoint: Meji Piece 1 Acceptance Cold Domain Iteration and Comms Log Refresh

**Date:** 2026-05-25
**Status:** Piece 1 copy locked (Gurmej-final). Cold-domain access message handed back to user after 4 agent revisions. Comms log refreshed through 2026-05-25 with verbatim screenshot transcription. New memory rule saved.

---

## Summary

Resumed Meji two-piece pilot. Piece 1 cadence draft sent to Gurmej for review; he ran it through Claude himself and returned his own version (now canonical) plus a 4-campaign inventory check and a venue-personalization strategic add. Cold-domain access ask went through four revisions (123-Reg coordination -> Mailforge bundle -> existing-provider Workspace -> exhaustive clickpath) before the user lost confidence and took over authoring. After the deletion, surfaced a missed-tool finding: Meji already has three live cold-sending domains in Instantly (mejievent.com, mejiai.com, banterexp.com) warming since October 2025. User clarified that Christmas cold needs its own new domain (separate from the existing mejievent.com which is mapped to corporate cold), broadening Christmas-cold scope to 3 cities PLUS UK-wide regular cold list. Comms log brought current through 2026-05-25 with verbatim transcription of Gurmej's 5/25 screenshots; new memory rule saved requiring screenshots to always be embedded into client context files.

---

## What Was Done This Session

### Piece 1 — Christmas warm follow-up
1. Sent the 3-touch cadence draft to Gurmej for copy review (with the .co flag verified live via Instantly API + DNS recon, and the internal decision locked to send from gurmej@mejimedia.com)
2. Received his Claude-rewritten version (different voice + structure: Touch 2 drops year-round secondary, adds call CTA + product specs; switches `{{shortenedcompanyname}}` to `{{companyName}}`)
3. Saved his version as canonical (`d1-cadence-gurmej-final-2026-05-25.md`), marked agent draft as superseded
4. Drafted Piece 1 acceptance reply confirming venue personalization is buildable + 4-campaign inventory (one open question on Banter scope)

### Cold-sending domain (Piece 2 infrastructure)
1. Iterated the cold-domain access ask through four revisions, each triggered by a real new constraint:
   - V1: 123-Reg shared access + separate mailbox provider
   - V2: Mailforge bundle (one-account managed infrastructure) — broke £25/yr cost anchor at ~£120-180/yr
   - V3: Cloudflare domain + Migadu mailboxes (hit the £25/yr anchor exactly at ~£23/yr)
   - V4: Existing Google Workspace + Cloudflare domain (consolidated to one provider) with exhaustive clickpath instructions
2. User deleted the draft after four revisions ("you are way too bad at this. im going to write the message myself")
3. Discovered (post-deletion, user-prompted) that Meji already has 3 live cold-sending domains in Instantly via `GET /api/v2/accounts` — significant missed-tool moment

### Christmas cold scope clarification (with same-day revert)
1. User clarified Christmas cold = NEW domain (separate from existing mejievent.com which is already mapped to corporate cold)
2. Christmas cold first broadened from "3 venue cities only" to "3 venue cities + UK-wide regular cold list", then **REVERTED same day** to 3 venue cities ONLY ("Meji's Christmas delivery is tied to the 3 fixed venues; cold-pitching Christmas outside those cities has no obvious fulfilment path")
3. **TWO separate cold sending domains locked** (not one shared, not reusing existing mejievent.com): one new domain for Christmas cold (3 cities, IMMEDIATE ask), one new domain for corporate cold (UK-wide, deferred until closer to send window)
4. User authored the cold-Christmas-mailbox access ask directly: `drafts/reply-to-gurmej-cold-xmas-mailbox-2026-05-25.md`

### Comms log refresh
1. Added 7 entries to comms-log.md covering 2026-05-19 → 2026-05-25 (billing pushback, scope acceptance, strategy answers, cadence rewrite + 4-campaign inventory)
2. Embedded verbatim screenshot transcription of Gurmej's 2026-05-25 cadence rewrite + 4-campaign inventory in the comms log entry
3. Fixed em-dash gate violations (two slipped through; converted in source)
4. Corrected entry count via grep (23 entries, not the 24 I estimated)

### Memory + rules
1. Saved new feedback memory: [embed-client-screenshots](file:///C:/Users/neuma_p1qrsic/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/memory/feedback_embed_client_screenshots.md) — anytime user provides screenshots of client conversations, transcribe verbatim into the client's comms-log.md
2. Indexed in MEMORY.md

---

## Key Decisions Made

### Piece 1 copy: Gurmej's rewrite is canonical
- **Choice:** Build the Instantly campaign from his own Claude-rewritten version verbatim
- **Rationale:** `feedback_anchor_on_clients_words` applies; his rewrite IS the voice. Substantive changes beyond voice (Touch 2 pure-Christmas, call CTA, product specs, merge-field switch to `{{companyName}}`) are his strategic choices, not voice-only refinements

### Piece 1 sender: gurmej@mejimedia.com (internally locked)
- **Choice:** Send warm follow-up from his real Workspace mailbox (not from the dead mejimedia.co)
- **Rationale:** Past M&M attendees recognize that address from booking emails; warm audience has no need for reputation isolation. Not surfaced to Gurmej as a question (per `feedback_anchor_on_clients_words` — don't re-ask items he hasn't raised). Pure operational fix.

### Cold-domain architecture: NEW domain for Christmas cold, mejievent.com stays as corporate cold sender
- **Choice:** Christmas cold gets its own domain; mejievent.com (already set up, warmed 7 months) remains the corporate-cold sender
- **Rationale:** User correction. Same source pool, different messaging frames — separate domains prevent reputation cross-pollination between corporate-events copy and Christmas-party copy. Matches the pattern of existing 3 domains (each domain dedicated to one use case).

### Christmas cold scope: 3 venue cities ONLY (post-revert)
- **Choice:** Christmas cold targets only the 3 venue cities (Wolverhampton, Leicester, Birmingham) with venue-specific copy. Earlier same-day broadening to include a UK-wide generic Christmas slice was reverted.
- **Rationale:** Meji's Christmas delivery is venue-bound; cold-pitching Christmas outside those cities has no fulfilment path. Corporate cold remains UK-wide.

### Two separate cold domains (not one shared, not reusing mejievent.com)
- **Choice:** New domain for Christmas cold (3 cities) + new domain for corporate cold (UK-wide), each isolated.
- **Rationale:** Full reputation isolation per campaign; Q3-Q4 Christmas burst decouples from year-round corporate at the sending layer; if either campaign hits deliverability issues, the other is untouched. Christmas-cold domain is the immediate ask; corporate-cold deferred until closer to its send window.
- **Open architectural question:** Role of existing mejievent.com (already set up + warmed since Oct 2025, mapped to "Meji Media Corporate Events" draft Instantly campaign) under this two-new-domains plan is unclear. Possibilities: (a) parked, (b) becomes the corporate-cold domain (already warmed = no 3-4 wk warmup wait), (c) decided later. Worth resolving before corporate-cold setup begins.

### Screenshot rule: always embed into context
- **Choice:** Verbatim transcription into client's comms-log.md, never just summary
- **Rationale:** Screenshots are session-bound and don't survive compaction. Verbatim text in context files is required for `feedback_anchor_on_clients_words` to apply in future sessions

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/context/drafts/reply-to-gurmej-piece1-cadence-review-2026-05-24.md` | Created → sent | Piece 1 cadence sent to Gurmej for review |
| `workspace/clients/meji-media/context/drafts/d1-cadence-3touch-christmas-primary-2026-05-24.md` | Marked superseded | Agent draft superseded by Gurmej's rewrite |
| `workspace/clients/meji-media/context/drafts/d1-cadence-gurmej-final-2026-05-25.md` | Created | Canonical copy for Instantly build (Gurmej's verbatim rewrite + venue personalization note) |
| `workspace/clients/meji-media/context/drafts/reply-to-gurmej-piece1-acceptance-2026-05-25.md` | Created | Accept his rewrite + venue confirmation + 4-campaign inventory response |
| `workspace/clients/meji-media/context/drafts/reply-to-gurmej-piece1-sender-mailbox-2026-05-24.md` | Created → deleted | Unsolicited ops note user correctly questioned; killed |
| `workspace/clients/meji-media/context/drafts/reply-to-gurmej-cold-domain-access-2026-05-24.md` | 4 revisions → deleted | User took over after four agent revisions |
| `workspace/clients/meji-media/context/piece1-warm-followup-status-2026-05-22.md` | Updated | Marked Piece 1 copy approved; documented mejimedia.co finding + send-from decision |
| `workspace/clients/meji-media/context/piece2-cold-list-scope-locked-2026-05-22.md` | Updated | Christmas cold broadened to 3 cities + UK-wide |
| `workspace/clients/meji-media/context/piece2-apollo-filter-spec-2026-05-24.md` | Created + updated | Apollo SET A/B/C filter spec + 3-campaign mapping after broadening |
| `workspace/clients/meji-media/context/cold-sending-domain-setup-plan-2026-05-22.md` | 4 revisions | Architecture state through Mailforge → Migadu → Workspace iterations |
| `workspace/clients/meji-media/context/comms-log.md` | Major update | 7 new entries 2026-05-19 → 2026-05-25; verbatim screenshot transcription embedded |
| `memory/feedback_embed_client_screenshots.md` | Created | New rule: embed client screenshots into comms-log verbatim |
| `memory/MEMORY.md` | Index entry added | Pointer to new memory |

---

## Current Status

- **Piece 1 (Christmas warm):** Copy LOCKED (Gurmej-final). Acceptance reply drafted for user to send. Pre-send build work pending (fresh Instantly campaign, venue enrichment from `xmas_2020.full_data_parties` + `delegates` + events table, exclude 38 bounces, schedule Touch 1 for early June from gurmej@mejimedia.com).
- **Piece 2A (Corporate cold):** Scope locked, Apollo filter spec ready, sender domain mejievent.com already set up + warmed. Waiting on Apollo account + sourcing + sample-approval gate.
- **Piece 2B (Christmas cold):** Scope locked at 3 venue cities only (the UK-wide slice was reverted same day). Needs NEW sending domain (separate from both mejievent.com and the eventual corporate-cold domain). User wrote the access-ask directly at `drafts/reply-to-gurmej-cold-xmas-mailbox-2026-05-25.md`.
- **Corporate-cold sending domain:** Deferred. Will set up closer to send window. Open question: whether to use the existing warmed mejievent.com (already 7 months in) or register a fresh domain. Decision to revisit before that workstream starts.
- **Comms log:** Current through 2026-05-25 with verbatim Gurmej content embedded.

No platform/ops-audit section in infrastructure.yaml (Meji is in handoff phase per the friction-register backlog note); platform feasibility check skipped intentionally.

---

## Next Steps

1. User sends Piece 1 acceptance reply (`drafts/reply-to-gurmej-piece1-acceptance-2026-05-25.md`) — confirms venue personalization + 4-campaign inventory + flags Banter as separate piece
2. User sends self-authored cold-domain access ask for the new Christmas-cold domain (matching existing Porkbun + Workspace pattern from mejievent.com/mejiai.com/banterexp.com)
3. Begin Instantly build for Piece 1: fresh campaign, venue enrichment via UTIL 8974201, exclude 38 known bounces, Touch 1 scheduled early June
4. Verify `companyName` field is populated for all 983 Christmas Bookers leads (Gurmej's rewrite uses `{{companyName}}`, not the derived shortened version)
5. Apollo account setup + Piece 2A sourcing run + 100-200 sample for Gurmej review
6. Once new Christmas-cold domain is registered + warming, set up Piece 2B campaign (3 city variants + UK-wide generic)

---

## Context for Next Session

### Files to Read First

- `workspace/clients/meji-media/context/comms-log.md` (current through 5/25, contains verbatim Gurmej 5/25 screenshots)
- `workspace/clients/meji-media/context/drafts/d1-cadence-gurmej-final-2026-05-25.md` (canonical Piece 1 copy)
- `workspace/clients/meji-media/context/piece1-warm-followup-status-2026-05-22.md` (Piece 1 state, copy approved)
- `workspace/clients/meji-media/context/piece2-cold-list-scope-locked-2026-05-22.md` (Piece 2 scope after broadening)
- `workspace/clients/meji-media/context/piece2-apollo-filter-spec-2026-05-24.md` (Apollo SET A/B/C with 3-campaign mapping)
- `workspace/clients/meji-media/context/cold-sending-domain-setup-plan-2026-05-22.md` (4th-revision architecture; the live state is the user's self-authored message, not this plan)
- `memory/feedback_embed_client_screenshots.md` (NEW — fire on every screenshot the user pastes)

### Open Questions

- Will Gurmej accept the Piece 1 acceptance reply as-is or send back his own further edits?
- What domain name will the user choose for the new Christmas-cold domain?
- What is Gurmej's Workspace seat situation (spare seats or new seats needed)?
- Has the Banter access been granted? (Still open from 2026-05-19; restated in his 5/25 inventory but no infrastructure handoff yet)
- All four existing cold-sending domains expire 2026-10-15 at Porkbun — is auto-renew on?

### Working Notes

- The existing 9 cold mailboxes (3 each on mejievent.com, mejiai.com, banterexp.com) use `smtp.google.com` as MX (not the standard `aspmx.l.google.com` Meji uses on mejimedia.com). This is an unusual Workspace setup; the new Christmas-cold domain should follow the same recipe (Porkbun + Google Workspace with smtp.google.com MX).
- Gurmej's Touch 2 in his rewrite intentionally drops the year-round secondary mention (it stays in Touch 1 + Touch 3 only). When building the Instantly templates, do not "fix" this by adding year-round back into Touch 2.
- Per the 2026-05-21 message Matthias sent: setup hours for the new domain are billed separately from the 8-hr pilot at ~3-5 hrs, with the commitment to "confirm the exact figure with you before I start that part". Whatever message goes to Gurmej about the new domain needs to honour this commitment.
- The £25/yr was the DOMAIN renewal cost in the 2026-05-22 separate-domain message, not the all-in cost. User's "stick to that" direction means total-cost framing should anchor on £25/yr where possible (or be transparent about overages).
- Three Instantly campaigns map to the existing 3 dormant imports (MejiAI Construction, Vayne, Meji Corporate Events). Gurmej collapsed these into his "Corporate cold" mental model in his 5/25 inventory; do not surface them as separate strategic items.

### Reference Materials

- Verbatim Gurmej 5/25 screenshots: `workspace/clients/meji-media/context/comms-log.md` (2026-05-25 entry)
- Prior checkpoint (2026-05-24): `docs/2026-05-24 - Meji Two-Piece Pilot State Lock and Piece 1 Cadence/Checkpoint.md`
- Audience verification data: `workspace/clients/meji-media/context/d1-attendee-xref-result.json` (98.4% match)
- Existing campaign copy (voice source): `workspace/clients/meji-media/context/d1-existing-sequence.json`

---

## How to Continue

Two-piece pilot in mid-build. Piece 1 copy is locked; build the Instantly campaign next session (fresh campaign creation, venue enrichment SQL, exclude bounces, schedule Touch 1). Piece 2 sourcing depends on Apollo account; Piece 2B Christmas cold also depends on the new domain Gurmej is setting up via the user's self-authored message. Comms log is current — read it for verbatim Gurmej content rather than reconstructing from drafts.

---

## Strategic Feedback

### What Worked Well This Session

- The autonomous diagnostic-first pattern around the .co flag worked cleanly: DNS recon + Instantly API in parallel resolved the operational question without asking Gurmej. Same pattern surfaced the 3 existing cold-sending domains (just later than it should have).
- User pushback on the unsolicited sender-mailbox ops note was right and applied immediately (file deleted, decision locked internally). The "don't re-ask items he hasn't raised" principle from `feedback_anchor_on_clients_words` held.
- New memory rule (embed-client-screenshots) addresses a real recurring gap: screenshots vanish at session boundary while context files persist. Saves having to reconstruct the chat from `responds_to` blocks in drafts next session.

### Suggestions

- **Pre-flight infrastructure check before recommending new infrastructure.** Before proposing any new sending domain / mailbox provider / DNS setup, query the relevant orchestrator for existing setups. For Instantly: `GET /api/v2/accounts` shows everything. The four cold-domain iterations would have ended at iteration zero had this query fired first. Candidate: a `cold-domain-build` skill module that opens with "enumerate existing sending infrastructure before proposing new" as step 1.
- **Pre-flight cost-anchor scan before client comms.** Before drafting any cost-bearing client message, grep prior comms for stated figures on the same line item. The Mailforge bundle would have failed this check (£120-180/yr vs stated £25/yr). Candidate: a post-write-gate hook on comms drafts that compares new cost figures against `comms-log.md` history for the same client.
- **Comms log update should be session-by-session, not batched.** The 6-day stale log meant reconstructing Gurmej's words from drafts when needed mid-session — slower and lossier than reading verbatim from the log. Candidate: extend the new screenshot-embedding rule into a comms-log update gate that fires whenever a draft is marked sent.

### System Health

- Autonomy score: ~6 user interventions this session (elevated — run /system-dev to close gaps). Cluster around: (a) cost-anchor drift, (b) iteration-without-stepping-back pattern on the cold-domain draft, (c) missed pre-flight check on existing Instantly infrastructure, (d) one unsolicited client question. The fourth-revision-before-user-takes-over pattern is the most expensive failure mode this session.
- Screenshot-embedding gap is now closed via memory (new `feedback_embed_client_screenshots`). But the cost-anchor and infrastructure-discovery gaps remain structural — same root cause (not querying available state before proposing) hit twice this session in different forms.
- Em-dash strip gate working as designed (caught violations in two writes mid-session). Placeholder-leak suppression worked correctly once invoked. B1 stop-hook fired and was self-corrected once on a deferral pattern.
