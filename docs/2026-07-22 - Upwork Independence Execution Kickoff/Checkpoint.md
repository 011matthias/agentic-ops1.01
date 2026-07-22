# Checkpoint: Upwork Independence Execution Kickoff

**Date:** 2026-07-22
**Status:** Program scaffolded + sprint zero shipped; execution running

---

## Summary

Re-ran the GTM optimization on the hardened harness (gtm-v2-confirm: v2 was NOT
converged, +35.63 kEUR on the byte-identical scorer), backfilled the
`--prior-art` heading contract across all 5 project runs, then planned and
kicked off the physical execution program: `workspace/projects/
upwork-independence/` scaffold (u1-u7 workstreams), AEO sprint zero on the
platform, and the ICP. Seven PRs merged, all CI-green.

---

## What Was Done This Session

### Optimize run (gtm-v2-confirm)

1. PR #356: backfilled `## Dead ends` / `## Sensitivities` into gtm-v1 + gtm-v2
   SUMMARYs; first proof the contract is retrofittable.
2. PR #359: the run — baseline (a) = v2's winner as-is (2123.84, bit-identical
   re-score), same pinned scorer, zero drift. **Verdict: v2 was not converged.**
   `b2b_lead_gen.acquisition` cold_email → referral = +35.62 (99.97% of gain) on
   a field no prior run ever moved; build 1200 → 1225 (+0.01) kills "floor is
   optimal". 6/6 boundary probes discarded as predicted (rate discounted in the
   SUMMARY: catalog was ordered by a disclosed offline sweep). First run to
   populate the `timestamp` column: 0.35 min/round.
3. PR #364: fixed `test_guard_pins.py` false positive (regex-scanned RUN.md
   prose; now reads frontmatter `guards:`/`guard_files:` only — the manifest
   citing the MANDATED `--prior-art` command was failing CI).
4. PR #365: finished the backfill (leadgen-portfolio + pricing-tiers); all 5
   project runs now machine-readable, NOTE line gone.

### Execution program (approved plan, 6-agent recon wf_fe3b27c9-aa5)

5. PR #375: program scaffold — README, infrastructure.yaml accounts roster,
   status/ with uwi-general + u1-u7; `project_status.py` second root
   (workspace/projects) so the staleness sweep covers projects; scope code
   `uwi`; W2 home-map row; rule/skill scope text.
6. PR #376: AEO sprint zero — sitemap.ts re-sync (+ dynamic blog slugs),
   llms.txt key pages, blog renderer GFM tables, validator scope over
   `content/blog/**` (proposal-heading check scoped to proposals),
   `platform/public/pricing.md` (mirrors LIVE page only; retainer menu stays
   gated behind u6 tier mapping).
7. PR #377: `context/icp.md` from a 5-agent extraction (won engagements + 34
   proposals + model segments); unblocked u2 backlog + u3 recipes rows.

---

## Key Decisions Made

### Baseline (a) for the confirm run

- **Choice:** v2's winner as-is, not v2's pre-run baseline.
- **Rationale:** Tests "was v2 converged?" (uncovered) not loop
  reproducibility (already covered by test suites). Any keep falsifies v2's
  claim; zero keeps would still publish as confirmation.

### Referral finding is NOT a channel pivot

- **Choice:** Operative acquisition plan = leadgen-portfolio mix (cold 0.378).
- **Rationale:** The +35.62 is avoided opportunity cost on 1,080 freed hours;
  the GTM model has no referral-supply constraint and the freed hours are
  stranded by locked `acq_fraction`. u4's ledger is the validation instrument.

### Owner decisions (via AskUserQuestion, recorded in uwi-general.md)

- **Purchases: plan-only** — u1 delivers a ready-to-purchase checklist; every
  purchase needs its own explicit approval.
- **Capacity: ~14 h/wk from day one** — hours ledger in uwi-general measures
  actuals; owner decides which client load gives way.
- **Referral: ledger + offer definition only** — no outbound drafts without a
  separate go.

### pricing.md mirrors the live page, not the new menu

- **Choice:** Machine-readable twin of the CURRENT /pricing only.
- **Rationale:** Publishing the 650/1850/6300 menu before u5's
  scope-to-deliverables mapping exists would sell undefined tiers (u6 gate).

---

## Files Modified

| File | Action | Purpose |
|---|---|---|
| docs/optimize/upwork-independence-{gtm-v1,gtm-v2,leadgen-portfolio,pricing-tiers}/SUMMARY.md | Modified | prior-art contract backfill (#356, #365) |
| docs/optimize/upwork-independence-gtm-v2-confirm/ | Created | RUN.md + results.tsv + SUMMARY.md (#359) |
| tools/tests/test_guard_pins.py | Modified | frontmatter-only guard detection + 4 tests (#364) |
| workspace/projects/upwork-independence/{README.md,infrastructure.yaml,status/*.md} | Created | program scaffold, 8 status files (#375) |
| tools/project_status.py (+tests) | Modified | second root workspace/projects; 5 new tests (#375) |
| .claude/commands/comd_resume.md, .claude/rules/{rule_file_placement,rule_project_status}.md, .claude/skills/skil_project-status/SKILL.md | Modified | uwi scope code, W2 row, projects-root scope text (#375) |
| platform/src/app/sitemap.ts, platform/public/llms.txt, platform/src/app/(public)/blog/[slug]/page.tsx, platform/public/pricing.md | Modified/Created | AEO sprint zero (#376) |
| tools/validate-platform-content.py (+tests) | Modified | content/blog scope + proposal-scoped headings (#376) |
| workspace/projects/upwork-independence/context/icp.md | Created | the shared ICP (#377) |
| workspace/projects/upwork-independence/status/{u2,u3}*.md | Modified | unblocked rows post-ICP (#377) |

---

## Current Status

All seven PRs merged to main (#356, #359, #364, #365, #375, #376, #377).
Program state is self-describing: `status/uwi-general.md` is the entry point,
`--client upwork-independence --check` exits 0, sweep silent, pins clean, no
worktrees left. **#376's platform changes are merged but NOT live** — Vercel
force-deploy is a Band-3 floor action awaiting the owner's order.

---

## Next Steps

1. **u2:** derive the editorial backlog (~25-40 pieces) from icp.md's demand
   taxonomy + write the first corpus pieces (biggest slice of the ~14 h/wk).
2. **u4:** build the partner ledger (`context/referral-ledger.md`) + offer
   definition (no drafts).
3. **u1:** write `context/cold-email-purchase-checklist.md` (registrar, domain
   candidates, mailbox plan, account tiers with EUR/mo, day-1-after-go
   sequence).
4. **u5:** extract the meji pipeline into `workspace/templates/leadgen-delivery/`
   + Instantly API client template + tier scope-to-deliverables mapping.
5. **Owner orders pending:** Vercel force-deploy (#376 live); any u1/u3
   purchase go; u4 drafts go.
6. u2 probe loop: schedule the monthly `ai_visibility_probe.py` re-run
   (needs PERPLEXITY_API_KEY provisioning decision).

---

## Context for Next Session

### Files to Read First

- workspace/projects/upwork-independence/status/uwi-general.md (decisions,
  reconciliation, hours ledger)
- workspace/projects/upwork-independence/context/icp.md (personas, filters,
  demand taxonomy, open validation questions)
- workspace/projects/upwork-independence/status/u2-aeo-content.md (the next
  workstream to execute)
- docs/optimize/upwork-independence-gtm-v2-confirm/SUMMARY.md (why referral
  is not a pivot)

### Open Questions

- Author/entity for corpus pieces: blog Article JSON-LD hardcodes "Nicolas
  Neumann" as sole author (u2 element, owner decision).
- Referral offer economics (commission vs reciprocity) — owner call after the
  ledger exists.
- u6: extend /pricing vs dedicated lead-gen service page (decide at build).

### Working Notes

- The EUR6300 scale tier has ZERO won-deal evidence (meji $1-1.5k/mo + wimmer
  ~$2.4k/mo bracket only the EUR1850 core tier). Highest-risk tier assumption;
  encoded in icp.md.
- 11/12 of one proposal batch died at status:draft, never sent — the Upwork
  bottleneck was OUR send cadence, not rejection.
- Channel pools all ASSUMED (cold 50 / LinkedIn 30 / referral 15 / content
  25); falsified pools flow back via SCORER_LOCK_ALLOW re-pin + portfolio
  re-run.
- Recon full returns: tasks dir run wf_fe3b27c9-aa5 (execution recon) and
  wf_7981a3ef-8ed (ICP extraction) — journals in the session subagents dir if
  detail is ever needed; the durable conclusions are all in the status files
  and icp.md.
- LinkedIn doctrine: human-in-seat for sends; agent does targeting, lists,
  drafts, tracking (Brisken precedent, encoded in u3).

### Reference Materials

- Plan file: C:\Users\neuma_p1qrsic\.claude\plans\strategize-the-physical-structure-tranquil-wall.md
- PRs: #356 #359 #364 #365 #375 #376 #377

---

## How to Continue

`/comd_resume upwork-independence` — the status/ folder auto-loads. Start with
u2 (editorial backlog derivation from icp.md), which is unblocked, free, and
the longest-ramp channel.

---

## Strategic Feedback

### What Worked Well This Session

- The three AskUserQuestion decisions (purchases / capacity / referral drafts)
  were answered in one round and reshaped sprint sequencing cleanly — asking
  exactly the forks that change the plan, nothing else, kept planning tight.

### Suggestions

- The ~14 h/wk decision has no enforcement surface yet: the hours ledger in
  uwi-general.md only works if it gets filled. Consider wiring the weekly
  acquisition review as a scheduled task NOW (the meji Mon-06:17 pattern)
  rather than after the first week slips — the morning-briefing precedent
  shows unscheduled cadences die here.

### System Health

- The prior-art heading contract proved retrofittable but exposed that a
  machine-readable dead end can mislead worse than no entry (three flagged
  cases: superseded v1 allocation, v1's wrong "ceiling" label, pricing-tiers'
  `user stop` vs "converged" headline). The contract may want a `superseded:`
  marker convention before more runs inherit stale verdicts.
- Autonomy score: 0 human interventions this session (2 self-detected friction
  events, both hook/audit-caught).
