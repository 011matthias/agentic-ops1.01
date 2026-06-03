# Checkpoint: Meji 3-Piece Pilot Restructure

**Date:** 2026-05-26
**Status:** Awaiting Gurmej reply on 3 blocking asks (final blocking-ask bundle sent 00:40 + 00:50 BST). Piece 1 build greenlit, ready to execute on user word.

---

## Summary

Restructured the Meji pilot from a 2-piece deal (warm + cold-list) into a 3-piece structure (Piece 1 warm Christmas / Piece 2 corporate cold reusing existing `mejievent.com` infra / Piece 3 Christmas cold on a new isolated domain). Drafted, iterated 4x against scope reversals, then helped the user ship the final 2-message blocking-ask bundle to Gurmej. Built the Piece 3 Christmas-cold domain setup runbook with both guided + access-based execution variants.

---

## What Was Done This Session

### Investigation
1. Pulled live state on `Meji Media | Corporate Events` Instantly campaign (`245913f7-...`) via new `meji_corporate_events_live_state.py`: status=-2 ACCOUNTS_UNHEALTHY, 880 leads, 2-step sequence (3 variants Touch 1), sender = 3 `*@mejievent.com` mailboxes, last send 2026-01-23
2. DNS-verified `mejievent.com` via 1.1.1.1: A resolves, MX=smtp.google.com, SPF=v=spf1 include:_spf.google.com ~all, google-site-verification TXT present (i.e. a fully working Google Workspace cold-sending domain Gurmej already owns)
3. Sampled 10 leads via new `meji_corporate_events_icebreaker_check.py` to locate the `{{icebreaker}}` field: lives in `payload.icebreaker` per-lead, externally pre-generated (template "Hi {name}, Respect your work at {company}. Also got some chops in the {industry} space, wanted to see if there was overlap.")

### Scope restructuring (4 reversals in one session)
1. Pivot 1: Christmas cold narrowed from "3 cities + UK-wide generic slice" → "3 cities only" (user direction)
2. Pivot 2: "Two separate cold-sending domains" (one for corp, one for Christmas)
3. Pivot 3 (after live-state check): "No new domain needed; reuse mejievent.com for both cold campaigns"
4. Pivot 4 (user correction): "For Christmas cold, we should still use a new domain — that is Piece 3"
5. **Final lock:** Piece 1 warm (mejimedia.com) / Piece 2 corporate cold (reuse mejievent.com via mailbox reauth) / Piece 3 Christmas cold (NEW separate domain). Banter OUT of scope.

### Client comms
1. Drafted `reply-to-gurmej-mailbox-reauth-2026-05-25.md`, revised through 4 iterations matching the scope pivots
2. User merged the draft assets + sent the final 2-message blocking-ask bundle on Upwork at 00:40 + 00:50 BST 2026-05-26:
   - 00:40: Piece 1 implementation confirmation + reengagement-list note + Apollo/ZoomInfo question + Piece 2 reauth walkthrough (Instantly UI reconnect path)
   - 00:50: Piece 3 alt-path ("I take it all on with access"), 2 things needed from Gurmej (Namecheap login + temp Workspace Super Admin user)
3. Piece 1 acceptance reply (drafted earlier this session) was sent by user — Piece 1 comms-closed
4. Locked verbatim transcripts of 6 prior Gurmej screenshots + the 2 sent messages into `comms-log.md` appendix (8 blocks total)

### Documentation
1. **NEW:** `piece3-christmas-cold-domain-runbook.md` — 4 stages (Namecheap registration → Workspace + DNS + mailbox → Instantly connection → DKIM/DMARC hardening) with ready-to-paste-into-Upwork blocks per stage, PLUS alt-path "Matthias does it all with access" variant
2. Updated `piece2-cold-list-scope-locked-2026-05-22.md` — retitled to "Pieces 2 + 3"; sending-infra section split per piece
3. Updated `piece2-apollo-filter-spec-2026-05-24.md` — routing split (SET A+B → existing 245913f7 campaign on mejievent.com; SET C → new campaign on new Piece 3 domain); added icebreaker-generation pipeline step
4. Updated `cold-sending-domain-setup-plan-2026-05-22.md` — banner revised 3x as scope pivoted, final state: NOT superseded, needed for Piece 3 only
5. Updated `piece1-warm-followup-status-2026-05-22.md` — status: PLANNING DONE, BUILD PENDING
6. Updated `comms-log.md` — added 2026-05-26 outbound entry + 6-block verbatim appendix from screenshots

### Memory
1. **Created:** `feedback_enumerate_existing_infrastructure.md` — lesson from the "no new domain needed" reversal; before designing new infra, query live state of all existing infra serving the same purpose
2. **Reinforced (user-written):** `feedback_no_auto_commit.md` — reinforced after user flagged scrapling PR #59 + earlier PR #57/#58 as unverified auto-commits. Overrides the rule_behaviors ship-gate for git/GitHub ship-class actions.

---

## Key Decisions Made

### Decision 1: 3-piece pilot structure (replaces earlier 2-piece framing)
- **Choice:** Pieces 1/2/3 = Warm Christmas / Corporate cold / Christmas cold (was previously bundled as Piece 1 + Piece 2 where Piece 2 was both cold campaigns)
- **Rationale:** Each piece has distinct infrastructure needs and timing. Easier to plan/execute/explain as 3 distinct pieces.

### Decision 2: Piece 2 reuses existing mejievent.com Instantly campaign
- **Choice:** Reauth existing 3 mailboxes on the dormant `245913f7-...` campaign, refresh contacts via Apollo, keep existing 2-touch sequence (Gurmej's preferred copy)
- **Rationale:** DNS check + Instantly API confirmed the existing setup is alive and just needs reconnection. Saves ~3-5 hrs of new domain setup. Existing sequence is what Gurmej wants kept.

### Decision 3: Piece 3 gets its own NEW separate domain (despite Piece 2 reusing)
- **Choice:** New Christmas-themed Namecheap domain → Workspace secondary domain → 1 new mailbox → new Instantly campaign with venue-specific copy
- **Rationale:** Reputation isolation per cold campaign. If Christmas cold takes a knock in Q3-Q4 burst (concentrated send window, sharper rejection signal), corporate cold sender stays clean.

### Decision 4: Banter (Gurmej's Campaign #4) OUT of scope for this pilot
- **Choice:** Defer Banter re-engagement to a separate engagement
- **Rationale:** User direction. Keeps pilot scope tight at 3 pieces matching the 8hr/$266 + ~3-5hr Piece 3 setup commercial envelope.

### Decision 5: Reengagement-list cross-reference handled internally (don't ask Gurmej)
- **Choice:** Pull "companies in conversation" via Instantly reply data + xmas_2020 `enquiries`; pull "already booked this year" via `full_data_parties`; auto-exclude from warm sends + fold into D7 weekly report
- **Rationale:** Data lives in his own systems; we have read access. Self-answering Gurmej's Block 6 question.

### Decision 6: Piece 2 mailbox unblock = Instantly UI reconnect (not Workspace app-password generation)
- **Choice:** Lead with "log into Instantly, click reconnect on each of 3 mailboxes" path; app-password fallback dropped
- **Rationale:** User caught that "existing passwords" can't be sent (app passwords shown once + hidden; OAuth has no password). Instantly UI reconnect requires no credential sharing and is the same 5-min effort with cleaner security.

### Decision 7: Piece 3 alt-path = "Matthias does it all with access" (chosen by user)
- **Choice:** Gurmej registers Namecheap domain (~5 min) + creates temp Super Admin user on Workspace + sends both credentials; Matthias does Stages 2-4 end-to-end
- **Rationale:** Gurmej unfamiliar with the technical steps. Trades a higher initial trust ask (Workspace Super Admin) for ~10 min total Gurmej time in one sitting instead of ~20-25 min spread across 6 weeks.

### Decision 8: Piece 1 build greenlit
- **Choice:** Matthias starts the 7-step Instantly build (venue enrichment SQL pull → fresh campaign → 3-touch branched Touch 1 → schedule for early June) once user gives the go-ahead
- **Rationale:** User's 00:40 BST message to Gurmej explicitly committed to implementing the 3 touches; the rest is Matthias-side execution with no further client dependencies.

---

## Files Modified

| File | Action | Purpose |
|---|---|---|
| workspace/clients/meji-media/context/drafts/reply-to-gurmej-cold-xmas-mailbox-2026-05-25.md | Created → SUPERSEDED | Initial wrong-premise mailbox ask (new domain for everything) |
| workspace/clients/meji-media/context/drafts/reply-to-gurmej-mailbox-reauth-2026-05-25.md | Created → revised 4x → SENT | Final mailbox/domain ask bundle (user-edited final sent at 00:40 + 00:50 BST 2026-05-26) |
| workspace/clients/meji-media/context/drafts/reply-to-gurmej-piece1-acceptance-2026-05-25.md | Modified → marked SENT | Piece 1 acceptance reply (user sent earlier this session) |
| workspace/clients/meji-media/context/piece1-warm-followup-status-2026-05-22.md | Modified | Status flipped to PLANNING DONE, BUILD PENDING |
| workspace/clients/meji-media/context/piece2-cold-list-scope-locked-2026-05-22.md | Modified (multiple) | Retitled "Pieces 2 + 3"; sending-infra split per piece |
| workspace/clients/meji-media/context/piece2-apollo-filter-spec-2026-05-24.md | Modified (multiple) | Routing split per piece; icebreaker-generation pipeline step added |
| workspace/clients/meji-media/context/cold-sending-domain-setup-plan-2026-05-22.md | Modified (3 banner revisions) | Final state: NOT superseded, still canonical for Piece 3 setup |
| workspace/clients/meji-media/context/piece3-christmas-cold-domain-runbook.md | **NEW** | 4-stage runbook + Matthias-does-it-all variant; ready-to-paste Upwork blocks per stage |
| workspace/clients/meji-media/context/comms-log.md | Modified | Added 2026-05-26 outbound entry + 6-block verbatim screenshot appendix |
| workspace/clients/meji-media/context/analysis-scripts/meji_corporate_events_live_state.py | **NEW** | Instantly API read script for Corporate Events campaign |
| workspace/clients/meji-media/context/analysis-scripts/meji_corporate_events_icebreaker_check.py | **NEW** | Sample-inspect leads for icebreaker field location |
| workspace/clients/meji-media/context/corporate-events-live-state.json | **NEW** | Live state JSON: status=-2, email_list, sequence steps, analytics |
| workspace/clients/meji-media/context/corporate-events-icebreaker-sample.json | **NEW** | 10-lead sample showing payload.icebreaker structure |
| memory/feedback_enumerate_existing_infrastructure.md | **NEW** | Lesson: enumerate existing infra before designing new |
| memory/MEMORY.md | Modified | Added new memory entries (one by linter/user, one by me) |

---

## Current Status

- **Piece 1 (Warm Christmas):** Planning + comms DONE. Build PENDING (~3 hr Matthias-side: venue enrichment SQL → fresh Instantly campaign → 3-touch branched Touch 1 → schedule for early June). User explicitly greenlit via the 00:40 message to Gurmej. Ready to execute on user word.
- **Piece 2 (Corporate cold):** BLOCKED on Gurmej replies — (a) Instantly UI reconnect on 3 `*@mejievent.com` mailboxes, (b) Apollo/ZoomInfo/Lusha tool question.
- **Piece 3 (Christmas cold):** BLOCKED on Gurmej replies — (a) Namecheap domain registration + login, (b) temp Workspace Super Admin user + credentials. Once received: ~30 min Matthias-side execution + 3-4 weeks warm-up + sequence copy drafting.
- **Banter:** OUT of scope. Logged for separate future engagement.
- **Platform usage:** No `infrastructure.yaml` exists for meji-media client (workspace/clients/meji-media/context/infrastructure.yaml not found). Cannot generate ops status line. Make.com is the orchestrator. Next steps include running platform feasibility assessment.

---

## Next Steps
1. **Wait for Gurmej replies** to the 00:40 + 00:50 messages (3 blocking asks pending)
2. **On user greenlight: execute Piece 1 Instantly build** (the 7-step plan in `piece1-warm-followup-status-2026-05-22.md`)
3. **On Apollo answer:** if Gurmej has an existing seat, use it; otherwise set up new (~$49/mo pass-through). Then run SET A + SET B + SET C Apollo pulls + sample for Gurmej review.
4. **On Namecheap + Workspace access:** execute Piece 3 Stages 2-3 (DNS + mailbox + Instantly connection), start 3-4 week warm-up
5. **During Piece 3 warm-up:** draft Christmas cold sequence copy (venue-branched Touch 1), Gurmej review
6. **Stage 4 (~1 week post Piece 3 mailbox warmup):** DKIM + DMARC hardening
7. **Run platform feasibility assessment for meji-media** (no `platform` section in infrastructure.yaml)

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/context/piece1-warm-followup-status-2026-05-22.md` — Piece 1 status + 7-step build plan
- `workspace/clients/meji-media/context/piece2-cold-list-scope-locked-2026-05-22.md` — Pieces 2+3 scope, sending-infra split
- `workspace/clients/meji-media/context/piece3-christmas-cold-domain-runbook.md` — Piece 3 execution recipe (both paths)
- `workspace/clients/meji-media/context/comms-log.md` — Full comms history + verbatim 8-block appendix
- `workspace/clients/meji-media/context/drafts/reply-to-gurmej-mailbox-reauth-2026-05-25.md` — Last sent message (text source)
- `memory/feedback_no_auto_commit.md` — DO NOT auto-commit anything, override the ship-gate

### Open Questions
- Apollo: does Gurmej have it (or ZoomInfo/Lusha)? Asked, pending.
- Mailbox reauth: which Piece 2 path will Gurmej confirm? Asked, pending.
- Piece 3 access: when will Namecheap + Workspace creds arrive? Asked, pending. Alt-path "I take it on" was pre-selected.
- NeverBounce (~$40 one-time): defer to a separate cost-approval message later.
- Piece 3 sequence copy: TBD; draft during the warm-up window.

### Working Notes
- **mejievent.com is alive** — DNS healthy, Google Workspace tenant, 3 mailboxes provisioned (gurmej.p@, gurmej.pawar@, gurmej@). Status -2 on the Instantly campaign = stale auth, not dead infra.
- **Icebreaker field is `payload.icebreaker` per-lead** — externally generated. New Apollo contacts need a Claude API gen step (~$5/5k leads) before upload to keep the existing template intact.
- **Em-dash strip gate has false positives** on tokens like `3-4 week`, `built-in`, `one-time` — flagged as em-dashes when they're plain hyphens. Confirmed via grep on U+2014 (zero matches).
- **Scrapling commit was PR #59 (d922dc2)** — merged before this session opened, not by me in this session, but the user surfaced it as an unverified-auto-commit incident. Reinforces feedback_no_auto_commit memory.
- **Failed approaches:**
  - "Two separate cold-sending domains" plan (Piece 2 + Piece 3 each get a new domain) — reverted when DNS check showed mejievent.com is alive.
  - "No new domain at all, reuse mejievent.com for both cold campaigns" plan — reverted when user clarified Piece 3 still needs isolation.

### Reference Materials
- Instantly API V2 docs: https://developer.instantly.ai/api/v2
- Namecheap registrar: https://www.namecheap.com
- Google Workspace admin: https://admin.google.com
- Verbatim screenshot transcripts: bottom of `workspace/clients/meji-media/context/comms-log.md` (8 blocks, lines ~486 onwards)

---

## How to Continue

Open this checkpoint + `piece1-warm-followup-status-2026-05-22.md` + `piece3-christmas-cold-domain-runbook.md`. Confirm Gurmej replies haven't landed yet (check `comms-log.md` and Upwork directly). If user greenlights Piece 1 build, start the 7-step execution from the status file. If any of Gurmej's replies have landed, follow the appropriate branch:
- Apollo answer → start sourcing pipeline
- Piece 2 reauth confirmation → refresh campaign 245913f7 contacts via Apollo, unpause
- Piece 3 Namecheap + Workspace access → execute runbook Stages 2-3, kick off warm-up

DO NOT commit anything to git without explicit user order (see `feedback_no_auto_commit.md`).

---

## Strategic Feedback

### What Worked Well This Session
- User pushed back early on each unverified premise (e.g. "Are you sure he needs to create 3 new passwords or can he just send the existing 3?") which saved a lot of churn before the wrong message went out
- The hand-screenshot → verbatim-into-comms-log pipeline worked great (per `feedback_embed_client_screenshots`) — 8 blocks of canonical client voice now locked in for future sessions
- The live-state check on the existing Corporate Events campaign (one Instantly API call + one DNS lookup) saved ~3-5 hours of new-domain setup work that would have otherwise been built unnecessarily

### Suggestions
- **Start-of-session scope confirmation** when client work has been actively evolving: a quick "current scope structure as I understand it: Piece 1 = X, Piece 2 = Y. Correct?" would have caught the 2-piece → 3-piece mismatch at the start instead of after 4 iterations.
- **Build `tools/instantly-campaign-state.py` as a generic tool** parametrized on campaign ID + .env path. The corporate-events-live-state pattern is reusable across clients; currently lives as a meji-specific analysis script.
- **Fix em-dash strip gate regex** to not match hyphens inside word-tokens (3-4, built-in, one-time). Two cycles wasted this session confirming false positives.

### System Health
- **Friction event regression risk:** the "design new infra without enumerating existing infra" failure that triggered `feedback_enumerate_existing_infrastructure.md` is structurally the same family as B1 (about-to-ask-user → check fixtures/tools first) but applied to client infra. The memory captures the lesson; a structural fix would be a pre-task hook that auto-runs an "enumerate existing client infra" check when client work involves new infrastructure design.
- **Auto-commit incident:** the user-written `feedback_no_auto_commit.md` is now in MEMORY.md and overrides the rule_behaviors ship-gate for git ship-class actions. Watch for hook-based auto-commits that bypass agent reasoning entirely — the user mentioned this happened with the scrapling skill (PR #59).
- **Autonomy score:** 6 human interventions this session (scope pivots ×4 + Instantly reconnect path correction + Piece 3 alt-path selection). Elevated — but mostly user surfacing new information rather than correcting agent errors. Real friction events: ~3 (see audit below).

### Friction Audit

| # | Type | Detected by | Gate | Description | Fix |
|---|---|---|---|---|---|
| 1 | over-literal | user | B3-style | Took initial 2-piece framing as spec instead of confirming the 3-piece structure existed; built revisions on top until user re-numbered as "that is piece 3" | documented |
| 2 | intent-misalignment | user | B2 | Declared "no new domain needed" + drafted message before confirming intent (user wanted reuse only for Piece 2, not both cold pieces) | documented |
| 3 | agent-deferred (B1) | user | B1 | Designed new cold-sending domain without first enumerating existing infra; user surfaced the Corporate Events campaign | memory (`feedback_enumerate_existing_infrastructure.md`) |
| 4 | slow-path | user | none | Led Piece 2 reauth flow with Workspace-admin app-password generation; user pointed out Instantly UI reconnect is simpler | documented |
| 5 | infrastructure-deferred | agent | none | Em-dash strip gate has false-positive bug on hyphens inside word tokens (3-4, built-in); wastes cycles to diagnose | documented (could be structural — fix regex) |
| 6 | verification-theater | user | B2 | (Outside this session, but surfaced now) Scrapling skill PR #59 was auto-committed without runtime verification | memory (`feedback_no_auto_commit.md`) |

**Gates:** B1:5+ B2:3 B3:0 B4:4 skipped:2 (B2 on Piece 3 intent, B3 on scope premise)

**Autonomy score:** 6 human interventions this session (elevated — but most were user surfacing new info; ~3 true friction events. Run `/system-dev` if pattern persists across sessions).
