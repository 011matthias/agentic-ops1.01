# Checkpoint: UWI Phase-2 Shape + Voice-Line Assessment

**Date:** 2026-09-09
**Status:** Strategy is canon on main; zero execution started; phase-2 go still with the owner

---

## Summary

Second half of the session that committed the upwork-independence monetization
strategy (PR #669, covered by Mini-Checkpoint-2 on 2026-09-05): oriented the
owner on what was decided, laid out the phase-2 timeline, assessed a 24/7
automated phone line as a care-tier module, and settled the build-vs-outreach
ordering question. Nothing was built or sent.

---

## What Was Done This Session

### Owner orientation (three passes, each a different altitude)
1. Plain-language walkthrough of the committed strategy: why the floor exists,
   what the four rulings mean, how income decouples from hours, what the
   tripwires catch.
2. Phase-2 as a dated timeline (week 0 machinery, September triage, Oct-Nov
   local motion, exit trigger to build phase, months 9-12 subcontract trial).
3. Answered the ordering question with a rule, not a preference (see decisions).

### Voice-line feasibility assessment
4. Costed and scoped a 24/7 automated phone line for local businesses; placed it
   against the committed strategy rather than as a standalone idea. All economics
   ASSUMED (general knowledge, no repo source) and tagged as such in the answer.

### Ledger
5. Mini-Checkpoint-2 + session log + INDEX row shipped as PR #670 (docs-only).

---

## Key Decisions Made

### The voice line is a care-tier module candidate, not a second wedge
- **Choice:** If pursued, it enters as substance inside the existing local offer
  (EUR1,225 build + EUR200/mo care), validated by one bounded probe on our own
  number, in the same walk-in pitch as the website demos. Not a new product line,
  not a new persona, not a new channel.
- **Rationale:** The strategy's do-nots bar a second wedge before month 4 without
  an enumeration gate. Meanwhile the care annuity is the weakest observed part of
  the plan (attach 0-for-1; site care alone is thin), and "never miss a call
  again" is a stronger reason to pay EUR200/mo than site maintenance. The module
  reading captures the upside without breaking the concentration ruling.

### Build once, then outreach; per-client work only after money
- **Choice:** Build one shared demo line (one vertical scenario, German,
  disclosure included), then pitch continuously. Client-specific greeting,
  calendar and routing are paid delivery, never speculative inventory. Further
  assets (pricing page, second scenario, booking integration) are demand-pulled.
- **Rationale:** Two observed facts pull opposite ways: demo-first is the winning
  motion (all wins were rescue-shaped, showing beats describing), but build-first
  is the documented failure mode (five finished demo sites unpitched for thirteen
  weeks; 30 of 33 proposals died at draft). A phone agent breaks the tie because
  one demo serves every prospect, unlike the per-business website demos, so the
  build is a one-time cost rather than a per-send tax.

### Phase-2 go deliberately not taken
- **Choice:** The go was offered as a fork; the owner asked for explanation
  instead, and the fork was left open rather than re-pressed.
- **Rationale:** The owner sets pace on a plan whose first moves include two
  irreversible client messages. Re-asking would have been pressure, not clarity.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `docs/2026-09-05 - UWI Monetization Strategy Committed/Mini-Checkpoint-2.md` | created (PR #670) | Mid-session mini checkpoint after the strategy ship |
| `docs/sessions/2026-09-05.md`, `docs/INDEX.md` | appended (PR #670) | Session log entry + index row |
| `docs/2026-09-09 - UWI Phase-2 Shape + Voice-Line Assessment/Checkpoint.md` | created (this PR) | This checkpoint |
| `docs/friction-register.md` | archived + appended (this PR) | 14-day archive split; two new rows |

No repo code, strategy, or status files changed after the PR #669 merge. The
strategy doc is untouched since commit, by design.

---

## Current Status

`context/monetization-strategy.md` is canon on main with the owner's four
rulings recorded as decisions 4-6 in `status/uwi-general.md`. Execution has not
started: no sends, no Brisken proposal, no week-0 machinery, no purchases.
Ops status: the pre-flight found no `infrastructure.yaml` for
upwork-independence because it looks under `workspace/clients/`; the project is
internal and keeps its own accounts roster at
`workspace/projects/upwork-independence/infrastructure.yaml`. No comms-log
exists for it (correct — internal project, no client thread).

Sibling sessions are live in this clone (the primary tree sits on
`client/brisken/outreach-packet-link-sent` with dirty meji-media files), so this
checkpoint's ledger edits went through the dedicated worktree
`C:/Users/neuma_p1qrsic/Repo/ao1-docs-uwi`.

---

## Next Steps

1. Owner's phase-2 go (or an explicit hold). Everything below waits on it.
2. On go: week-0 machinery — sends-ledger table, send-queue, weekly counting task
   (run by hand and read real output before registering), letter template,
   QR-card contact lines, gauntlet re-run on all five demo sites, Beauty Lounge
   SSL re-check.
3. On go: u5 desk work — tier scopes (0.20 audit-shaped + 0.55) for owner
   sign-off, case-study draft from delivery records (publication consent-gated).
4. The two per-send-gated messages: Brisken rate+cap proposal (open EUR33-35/hr,
   accept >=25, hard 10-13 h/wk cap, lapse as walk-away) and Meji ask-1.
5. If the voice line is wanted: its own purchase approval (~EUR20-50 platform
   credits + number), then the probe lands inside week 0.

---

## Context for Next Session

### Files to Read First
- `workspace/projects/upwork-independence/context/monetization-strategy.md`
- `workspace/projects/upwork-independence/status/uwi-general.md` (decisions 4-6)
- `C:/Users/neuma_p1qrsic/.claude/plans/evidence-first-from-the-rosy-giraffe.md`
  (full evidence base + the three-workflow design that produced the strategy)

### Open Questions
- Phase-2 go: full (machinery + messages prepped) vs machinery-only vs hold.
- Voice-line probe: approve the small spend, or leave the module unbuilt.
- u5 tier-scope sign-off: 650 recurring with audit as month-1 deliverable
  (recommended, menu untouched) vs one-off EUR850 audit creditable against 1850
  month one (a menu amendment, changes period semantics).
- German editorial piece #33: language + entity call.
- LinkedIn DE-DM legality check before any DE cadence at rebalance.

### Working Notes

**Voice-line assessment, expensive to re-derive (all ASSUMED, no repo source):**
Stack is commoditized in 2026 — a DE number plus Retell / Vapi / ElevenLabs
Conversational, or OpenAI Realtime with Twilio or sipgate; the platform handles
turn-taking, interruption and latency, which used to be the hard part. Working
demo (German, captures name/need/callback window, emails or WhatsApps a summary):
1-2 days, EUR20-50 in credits. First production client (their voice, appointment
capture or real booking, emergency routing to mobile, human fallback): 1-2 weeks,
then days per client once templated. Running cost roughly EUR0.05-0.15/minute
plus a few euros for the number, so a few hundred minutes a month costs EUR20-50
against a EUR100-300/mo price — sticky, because nobody churns off their phone
line. Two DE-specific compliance points: DSGVO handling of call recordings and
transcripts, and the EU AI Act transparency duty (the agent must disclose it is a
machine). Real risk is support load: every deployed line is a small live system
that will mishandle a 2am call, and without monitoring plus a runbook the module
quietly re-couples income to hours — design that in from client one, which is
what the u5 kit discipline exists for. Verify German conversational quality by
calling it yourself, never from a vendor page.

**Why the ordering answer came out the way it did:** the tie-break is the
shared-asset property, not a preference about sequencing. Website demos are
per-business, so building ahead of outreach means N builds before the first
conversation; a phone demo is one number where only greeting and scenario swap,
so the build cost is paid once and every subsequent send is free. That is what
makes "build once, then outreach" safe here when "build first" is the documented
failure mode elsewhere.

**Cross-session state (not verified against the comms log):** a parallel session
finalized the Meji September launch line-up (ask 1) and the Jess workload
proposal on 2026-09-06; both were with the owner for send, with all execution
gated on Gurmej's reply. Source was that session's scratch payload, not a
first-hand read — re-check `workspace/clients/meji-media/context/comms-log.md`
before relying on it. This matters to the uwi plan because Meji's
end-of-September gate is the single largest warm-income variable in the floor.

### Reference Materials
- PR #669 (strategy + supersession), PR #670 (mini checkpoint ledger)
- `docs/optimize/upwork-independence-portfolio-no-cold/SUMMARY.md` (operative mix)

---

## How to Continue

Read the strategy doc first, then answer the phase-2 fork. If the answer is go,
start with week-0 machinery (all local, no client contact) and bring the two
client messages back for individual approval before any send. If the voice line
is in scope, fold its probe into week 0 rather than treating it as separate work.

---

## Strategic Feedback

### What Worked Well This Session
- The generate-judge-verify pipeline earned its cost. The 12-class refute-first
  pass caught four material defects that would have shipped: the EUR2,500 floor
  failed its own arithmetic in the binding case (which flipped the recommendation
  to EUR2,000), "1850 has observed corroboration" was actually a refusal plus an
  un-invoiced projection, the u7 pass bar sat exactly on the gtm-v3 failure
  trigger, and 8 x 1850 had been written as EUR12.4k. Verification changed the
  answer, not just its confidence.
- Splitting the deliverable from the decision: the strategy doc shipped complete
  with fork stances marked OPEN, so the owner ruled on four clean questions
  instead of reviewing a 400-line document for hidden assumptions.

### Suggestions
- Fold an orient-before-forking rule into the AskUserQuestion guidance: after
  shipping a large artifact, the next turn defaults to a plain-language
  walkthrough, and the decision fork waits for the owner to signal readiness.
  This session spent three turns getting to the altitude the first answer should
  have had, and the memory that covers it
  (`feedback_reviews_in_plain_language`) was loaded and did not fire.

### System Health
- The B1 deferral class keeps recurring despite structural coverage: the
  stop-gate blocked this session's closing offer of a checkpoint, and the
  register now carries same-class rows on 08-23, 08-24, 08-25 (x2), 09-05
  (this one), 09-07 and 09-08. The gate is containing it reliably; the
  pre-generation primer is not curing it. Worth a `/system-dev` look at why the
  primer fires and the behavior still lands in closing text.
- Autonomy: 4 human interventions (elevated). Three were pace and comprehension
  steering (interrupt for a plan summary, a declined tool call, the declined
  fork); one was a resume instruction. None corrected a factual error in the
  work itself.
