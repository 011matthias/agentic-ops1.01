---
tag: platform-openwebui-weight
project: platform
goal: >
  Cut the first-visit byte weight of the 8-page openwebui-email-compliance
  prospect site without changing one word the reader sees, reusing the
  page-weight scorer and the guard pair proven in
  platform-alpha-research-weight. Hard floors: validate-html clean in
  directory mode, and rendered text byte-identical to the locked baseline.
scorer: tools/scorers/page-weight.py
scorer_args:
  - platform/public/clients/openwebui-email-compliance/faq.html
  - platform/public/clients/openwebui-email-compliance/gdpr.html
  - platform/public/clients/openwebui-email-compliance/index.html
  - platform/public/clients/openwebui-email-compliance/investment.html
  - platform/public/clients/openwebui-email-compliance/onboarding.html
  - platform/public/clients/openwebui-email-compliance/solution.html
  - platform/public/clients/openwebui-email-compliance/timeline.html
  - platform/public/clients/openwebui-email-compliance/workflow.html
direction: minimize
assets:
  - platform/public/clients/openwebui-email-compliance/*.html
guards:
  - uv run tools/validate-html.py --dir platform/public/clients/openwebui-email-compliance
  - uv run tools/guard-text-preserved.py docs/optimize/platform-openwebui-weight/baseline-text.json
guard_files:
  - docs/optimize/platform-openwebui-weight/baseline-text.json
budgets:
  rounds: 8
  wall_clock_minutes: 90
  score_timeout_seconds: 120
  max_rework_attempts: 2
mode: converge
stop:
  consecutive_reverts: 5
---

# openwebui-email-compliance page weight

## Why this run

Two purposes, both about the harness rather than the page.

**Prove the scorer is genuinely reusable.** `page-weight.py` had zero runs
before 2026-07-22 and exactly one after; the scoreboard reported
`scorer reuse: none reused across runs`. A scorer that has only ever measured
one asset is not demonstrably generic. This run puts the identical scorer and
the identical guard pair on a structurally different page set (different
builder output, different roster - this one carries `gdpr.html`) with no
scorer or guard change of any kind.

**Exercise cross-run recall against a real prior journal.** The whole point of
shipping a dead-end section in SUMMARY.md is that the next run reads it. This
manifest was written from `docs/optimize/platform-alpha-research-weight/
SUMMARY.md`, and the two entries below are inherited from it rather than
rediscovered.

## Inherited from platform-alpha-research-weight

- **Do not spend a round extracting the shared stylesheet to a linked file.**
  `page-weight.py` calls `measure()` per file and sums subtotals, and
  `measure()` counts every local `<link rel=stylesheet>`, so a shared file is
  counted once per page exactly like the inline copy. Score-neutral by
  construction. This looks like the largest target on the page and is not
  reachable through this metric.
- **Deliberately declining the full-minification round.** Run 1 took 9,516 B
  by collapsing all whitespace around `{ ; : ,` inside `<style>`, and its
  SUMMARY flagged that as a maintainability decision that should NOT be
  inherited by other client sites without the owner's call. Declining it here
  is the honest reading of that sensitivity: this run stops at the readable
  half. The consequence is a smaller headline number than run 1, and that is
  the correct outcome, not an underperformance.
- **Expect markup indentation to be the biggest single lever**, not CSS. Run 1
  found 14,885 B there after three CSS rounds had already been squeezed.

## Action catalog

1. HTML comments outside script/style.
2. CSS rules whose selector names a class/id present nowhere else in the file
   (markup, attributes and script text all count as present, so JS-toggled
   classes survive).
3. Indentation and blank lines inside `<style>`, readable form retained.
4. Indentation, blank lines and whole-line `//` comments inside inline
   `<script>`, line-oriented only so there is no ASI hazard.
5. Markup indentation, only in whitespace runs sitting entirely between `>`
   and `<`; pre/textarea/style/script excluded.

## Boundary probe planned

Repeat run 1's decisive probe on this page set: delete a whole content block
and confirm `guard-text-preserved` fails it while `validate-html` passes it.
The guard is only trustworthy on a page set where it has been shown to fire,
and a guard proven on one site is not proven on another.
