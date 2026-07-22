---
tag: platform-alpha-research-weight
project: platform
goal: >
  Cut the first-visit byte weight of the 8-page alpha-research prospect site
  without changing one word the reader sees. Hard floors: validate-html clean
  in directory mode (structure + cross-page consistency), and the rendered
  text of every page byte-identical to the locked baseline digest.
scorer: tools/scorers/page-weight.py
scorer_args:
  - platform/public/clients/alpha-research/brief.html
  - platform/public/clients/alpha-research/faq.html
  - platform/public/clients/alpha-research/index.html
  - platform/public/clients/alpha-research/investment.html
  - platform/public/clients/alpha-research/onboarding.html
  - platform/public/clients/alpha-research/solution.html
  - platform/public/clients/alpha-research/timeline.html
  - platform/public/clients/alpha-research/workflow.html
direction: minimize
assets:
  - platform/public/clients/alpha-research/*.html
guards:
  - uv run tools/validate-html.py --dir platform/public/clients/alpha-research
  - uv run tools/guard-text-preserved.py docs/optimize/platform-alpha-research-weight/baseline-text.json
guard_files:
  - docs/optimize/platform-alpha-research-weight/baseline-text.json
budgets:
  rounds: 10
  wall_clock_minutes: 120
  score_timeout_seconds: 120
  max_rework_attempts: 2
mode: converge
stop:
  consecutive_reverts: 5
---

# alpha-research page weight

## Why this run

This is the harness's first run against a **production asset**. The four runs
before it all optimized a planning-model JSON the agent had authored in the
same PR chain, so the loop was advising itself; the scoreboard read
`asset kind: 0/4 production`. It is also the first execution of
`page-weight.py`, the only reusable scorer in `tools/scorers/`, pinned since
2026-07-17 and never once run. Everything the generic path depends on -
multi-file asset globs, a directory-mode validator guard, a scorer taking
eight argv paths - was unproven until this run turned a round.

Target: `platform/public/clients/alpha-research/` (8 pages, 262,197 B). The
prospect proposal is `status: draft`, `sent: null`, untouched since March, so
a visual regression that slipped both guards would reach nobody. That is
deliberate for a first run on a live tree.

## What a reviewer should look at

The diff must be **pure representation**. Every kept round should be
mechanically explicable as "same bytes rendered, fewer bytes stored". If a
reviewer sees a word change, a section vanish, or a rule whose removal is not
provably unreachable, the guard has a hole and the run is void.

`guard-text-preserved.py` is what makes that claim checkable rather than
asserted: it pins the rendered text of all 8 pages to a digest snapshotted
before lock-on. `validate-html.py --dir` on its own would not catch a deleted
section, because a smaller page is still valid HTML. Note what the pair does
NOT cover: CSS that changes appearance without changing text (a colour, a
margin). That is the residual risk and it is why the run confines itself to
provably-unreachable rules rather than "looks unused".

## Action catalog

Measured composition of the 257 kB of markup: **CSS 96.8 kB (37.6%)**, JS
18.2 kB, comments 1.8 kB, indent slack ~14 kB. Ranked by expected bytes:

1. **Unused CSS rules** (biggest lever, ~37.6% of the payload is CSS). Each
   page carries a full copy of the site stylesheet while using a subset.
   Remove only rules whose selectors are provably unmatched on the page that
   carries them; static class/tag/id extraction, not judgement.
2. **Cross-page CSS duplication.** The same rule blocks repeat across all 8
   pages. Note the scorer counts a `<link>`ed local stylesheet once per page,
   so extraction to a shared file is score-neutral by construction; the win
   has to come from deleting rules, not moving them.
3. **Comment stripping** (~1.8 kB). Small, safe, mechanical.
4. **Indent slack inside `<style>`/`<script>`** (~14 kB available). Weigh
   against the simplicity criterion: a minified blob is worse to maintain
   than the bytes are worth. Expect this to be contested, and possibly a
   discard on complexity grounds even if it scores.
5. **The 2,039 B boot/nav script duplicated verbatim on 7 of 8 pages.**
   Same per-page-counting caveat as (2).
6. **Dead local asset references.** `page-weight.py` reports a missing ref as
   `MISSING (0 B counted)`, so these are score-neutral but worth fixing while
   here; a broken ref cannot masquerade as a win.

## Boundary probes planned

Before claiming convergence, spend `--probe` rounds on: pushing unused-CSS
removal into rules that are matched only by a sibling page (expect DISCARD
via the text guard or validator if the rule is live), and full minification
(expect a KEEP on score that should be judged a DISCARD on the simplicity
criterion). A probe that improves unexpectedly is the most useful round here.
