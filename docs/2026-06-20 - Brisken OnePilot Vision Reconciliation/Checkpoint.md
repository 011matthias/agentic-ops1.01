# Checkpoint: Brisken OnePilot Vision Reconciliation

**Date:** 2026-06-20
**Status:** Plan + deliverables committed; implementation gated on Dirk's sign-off

---

## Summary

Deployed the Brisken cube favicon to the Fly OnePilot prototype, cleaned the
live review-feedback log to 18 June onward, and built the strategy layer for the
OnePilot repositioning: a Dirk-facing feedback sign-off sheet, §8 of the revision
blueprint (platform-first repositioning), and a vision-vs-strategy fit memo that
critically reconciles Dirk's Universal-UI vision with the SAP-treasury marketing
wedge (land / expand / platform), re-grounded on the updated CONTINUOUS vision.

---

## What Was Done This Session

### Fly prototype favicon
1. Cause: prototype tab showed the browser globe (no `<link rel=icon>`; app served blank 204).
2. Added the Brisken cyan-cube SVG as an inline favicon in the canonical deliverable and made `/favicon.ico` serve it (gate + log pages too). Verified live origin. Deployed `brisken-onepilot-proto` (fra).

### Live feedback log cleanup
1. Backed up all 34 entries to `.scratch/`, filtered `/data/feedback.jsonl` on the Fly machine via `flyctl ssh console` to drop everything before 2026-06-18.
2. Result: 21 entries (earliest 2026-06-18). Verified the feedback POST/read cycle still works (local TestClient + live read-only).

### Dirk-facing review sign-off sheet
1. One-pager of the 18-19 June page-level feedback: tick-box batch of recommended fixes plus four explicit decisions. Excludes positioning (separate conversation per Dirk).

### Blueprint §8 + fit memo (the strategy layer)
1. §8 repositioning: OnePilot is the platform, TreasuryCentral one scoped edition; line-tagged prototype changes; AEO re-nesting; overclaim guardrail.
2. Fit memo (`brisken-onepilot-vision-strategy-fit.md`): land / expand / platform model; reverses §8's Universal-UI-first homepage call; OnePilot kept as ONE definition; the vision earns the second meeting, not the cold open.
3. Re-grounded both on the updated CONTINUOUS vision (five competitive slices, Gartner adoption stats, new ammunition); flagged the SAP-channel risk of the "your best practice, not the vendor's" line.

### Restructure plan (human terms)
Laid out, in plain language, how to restructure the website prototype (cold/AEO surface, stays SAP-data-sharp, OnePilot as platform, vision on its own page) and the Rome landing page (warm/in-person, treasury-led, surgical hierarchy fix given the 4-day conference clock).

---

## Key Decisions Made

### Land / expand / platform reconciliation
- **Choice:** Give each story a fixed funnel altitude instead of fighting for the homepage. Land = sharp SAP-data products (MDH); Expand = TreasuryCentral edition; Platform = OnePilot Universal UI on its own page + Cluster F.
- **Rationale:** The strategy wins because it is narrow; the broad vision as the cold headline drops Brisken into the crowded Glean/Copilot/Notion category and blunts the wedge. This is the user's explicit "no rigorous following Dirk, think critically" steer.

### Reverse §8's homepage call
- **Choice:** Homepage + AEO root stay SAP-data-wedge; Universal UI moves to a dedicated platform/vision page one click away (not the H1/title/crawlable body).
- **Rationale:** The homepage is both the outbound landing surface and the AEO root; breadth there violates the vision's own overclaim guardrail and poisons retrieval. §8 banner now points at the fit memo.

### OnePilot is ONE definition everywhere
- **Choice:** OnePilot = the platform at every altitude; apps (MDH, Trade, Bank Fee, Remittance) are products on it; TreasuryCentral is a scoped edition that bundles them.
- **Rationale:** Kills the "we keep pivoting" problem Dirk named without minting a second definition.

### SAP-channel caution on "your best practice, not the vendor's"
- **Choice:** Keep the "run the way best for you" idea; drop the anti-SAP-best-practice framing anywhere SAP can read it.
- **Rationale:** The whole motion runs on SAP goodwill (Store, co-sell, co-innovation). New decision for Dirk.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/onepilot-site/app.py` | Modified | `/favicon.ico` serves the cube SVG (commit 028087f) |
| `.../deliverables/brisken-onepilot-website-prototype.html` | Modified | Inline cube favicon link (028087f) |
| `.../deliverables/brisken-onepilot-revision-blueprint.md` | Created/Modified | §1-7 feedback plan + §8 repositioning + fit-memo banner |
| `.../deliverables/brisken-onepilot-review-signoff.md` | Created | Dirk-facing feedback sign-off one-pager |
| `.../deliverables/brisken-onepilot-vision-strategy-fit.md` | Created/Modified | Vision-vs-strategy reconciliation memo (+§6 CONTINUOUS update) |
| `context/lead-generation/OnePilot_UniversalUI_Positioning_Vision_CONTINUOUS.md` | Created | Canonical updated vision (gitignored) |
| Live: `brisken-onepilot-proto` Fly app | Deployed | Favicon live; feedback.jsonl filtered 34 -> 21 |

Commits (pushed, branch `client/brisken/lead-gen-onepilot`): 028087f, 6474dc3, 13aaa60, 8967a59, 30d752a, 58cefe9.

---

## Current Status

Brisken is a custom-SaaS platform (infrastructure.yaml tier "unknown", not a workflow-engine op count) so no ops-audit applies. All strategy deliverables are committed and pushed on the feature branch. Implementation of the restructure is NOT started: it is gated on Dirk's sign-off of the repositioning plus three open decisions. The Rome landing page is live for the conference on 24-25 June (4 days out) and carries the same inversion; leaving it as-is is the safe default unless Dirk wants the surgical hierarchy fix first.

---

## Next Steps

1. Get Dirk's call on the repositioning: accept platform-first hierarchy? + the three open decisions (homepage title/headline wording; EXPAND page label "TreasuryCentral" vs "OnePilot for Treasury"; how far to foreground FSI on the platform page).
2. Get Dirk's call on Rome: leave as-is for the 24th, or do the surgical hierarchy fix (rename OnePilot from "AI layer" to platform; stop listing TreasuryCentral as a peer app) before the booth.
3. On approval: website prototype is a clean rebuild per the restructure plan; Rome is a ~30-min surgical pass.
4. (This turn's other deliverable) the critical-review prompt to surface remaining edit points across the deliverables.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/deliverables/brisken-onepilot-vision-strategy-fit.md` (the reconciliation, the active strategy doc)
- `workspace/clients/brisken/deliverables/brisken-onepilot-revision-blueprint.md` (§1-7 feedback, §8 repositioning)
- `.scratch/onepilot-vision.md` (CONTINUOUS vision extract) and `.scratch/lead-gen-strategy.txt` (strategy extract)
- `workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html` and `.../lead-generation/rome-2026/brisken-rome-2026-landing.html` (the two surfaces to restructure)

### Open Questions
- Dirk's three positioning decisions (headline wording, EXPAND label, FSI prominence).
- Touch the Rome page before 24 June, or leave it?

### Working Notes
- **Working-tree wipe incident:** mid-session the entire `workspace/clients/brisken/deliverables/` showed as deleted in the working tree (all files, not just mine), while intact in git. Recovered with `git restore` from HEAD, no loss. Cause is almost certainly the concurrent-session-on-one-clone hazard (see memory `feedback_worktree_for_concurrent_sessions`). If parallel work continues on this clone, use a worktree.
- Live feedback now 21 entries (DIRK 12, Ricardo 6, Criss 2, Djalma 1); pre-18th backup at `.scratch/brisken-feedback-pre-cleanup-2026-06-20.jsonl`.
- The fit memo §4 lists exactly what stands vs reverses in blueprint §8; the §8 line-number citations point at the older V001 extract but its substance is unchanged in CONTINUOUS.

### Reference Materials
- Live prototype: https://brisken-onepilot-proto.fly.dev/ (name-gated)
- Vision source: `context/lead-generation/OnePilot_UniversalUI_Positioning_Vision_CONTINUOUS.md`

---

## How to Continue

The thinking is done and committed; the next move is Dirk's decision, not more analysis. When he signs off, execute the restructure plan (website rebuild + Rome surgical pass). If he is silent and the 24th nears, default to leaving Rome untouched for the conference.

---

## Strategic Feedback

### What Worked Well This Session
- The user's "no rigorous following Dirk, think critically" steer produced the single most valuable artifact (the fit memo). Treating Dirk's vision as an input to pressure-test, not a spec, is the right posture and the multi-agent red-team pass (protect-the-wedge / fair-to-vision / coherence) caught real issues (whole-page AEO ranking, the SAP-channel conflict).

### Suggestions
- The two repositioning workflows each re-read the same source docs. Persisting the extracts (`.scratch/onepilot-vision.md`, `lead-gen-strategy.txt`) up front, as done here, is the pattern to keep; consider promoting them to a durable `context/portable/` if the analysis continues across sessions.

### System Health
- A full `deliverables/` directory wipe in the working tree (recovered from git) is the second concurrent-session data scare on this clone. The structural fix is worktree discipline for parallel Brisken sessions; the soft fix (commit early, which held here) is what prevented loss. Worth a worktree before the next parallel run.
- Autonomy score: 2 human interventions this session (the strategic "think critically" redirect; the `flyctl auth login` the user ran, a genuine interactive-auth limitation).
