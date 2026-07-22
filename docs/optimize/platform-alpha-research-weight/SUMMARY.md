# platform-alpha-research-weight - run summary

**262,197 B -> 225,422 B (-36,775 B, -14.0%)** across the 8-page
`platform/public/clients/alpha-research/` prospect site. 6 keeps, 1 discard,
7 rounds. Every byte removed is representation: the rendered text of all 8
pages is byte-identical to the pre-run baseline, enforced per round.

This is the harness's **first run against a production asset**, and the first
execution of `page-weight.py` in any run. The scoreboard metric that mattered
(`asset kind: 0/4 production`) moves off zero here.

## Kept changes (the journal)

| r | delta | change |
|---|---|---|
| 1 | -1,897 | HTML comments outside script/style |
| 2 | -3,951 | CSS rules naming a class/id present nowhere in the file |
| 3 | -4,842 | indentation + blank lines inside `<style>` (readable form kept) |
| 4 | -9,516 | all whitespace around `{ ; : ,` inside `<style>` (full minification) |
| 5 | -1,684 | indentation, blank lines, `//` lines inside inline `<script>` |
| 6 | -14,885 | markup indentation, only in whitespace runs sitting between `>` and `<` |

The largest win was the last-considered lever, not the first. Markup
indentation (r6) beat every CSS lever, because the CSS bytes had already been
squeezed three times while 128 kB of markup had not been touched at all.

## The probe that matters

**r7 deleted an entire `<section>` from `faq.html` and was correctly
discarded.** `validate-html.py --dir` passed it: a page missing a section is
still valid HTML with consistent cross-page nav. `guard-text-preserved.py`
failed it, naming `faq.html DRIFT`.

That is the run's most important single result. Deleting content is the
dominant cheat of any byte-minimizing metric, and this run demonstrates the
floor firing inside a live run rather than only in unit tests. Without that
guard, every keep above would be unaudited.

## Dead ends

- **Extracting the shared stylesheet to a linked `styles.css` is
  score-neutral by construction, not an unexplored lever.**
  `page-weight.py` calls `measure()` per file and sums the subtotals, and
  `measure()` adds the size of every local `<link rel=stylesheet>`. A shared
  file is therefore counted once per page, exactly like the inline copy. The
  80 kB of remaining CSS mass looks like the biggest target on the page and
  is not reachable through this metric at all. Any future weight run against
  a multi-page site should read this before spending a round on extraction.
- **Re-running the CSS reachability pruner after rounds 3-6 yields 0 B.**
  Whitespace changes do not expose new unreachable rules; the pruner is
  idempotent and was exhausted at r2.
- **No dead local asset references exist in this page set** (`page-weight.py`
  reports `MISSING` refs and found none), so action-catalog item 6 was empty.

## Sensitivities

- **r4 (full CSS minification, -9,516 B) is a maintainability decision, not a
  measurement result, and it is the one thing a reviewer should overrule if
  they disagree.** It leaves each page's CSS as a single unbroken line. That
  is defensible here (a never-sent draft page, mechanically maintained by
  `normalize-client-pages.py`, whose regex edits are unaffected), but the same
  change applied to the 30 other live client sites is a different decision
  and should not be inherited from this run. Reverting it is one commit and
  costs 9,516 B of the 36,775.
- **The guard pair does not cover appearance, only text.**
  `guard-text-preserved.py` pins rendered text; `validate-html.py` pins
  structure. A CSS change that alters a colour, a margin or a breakpoint
  passes both. This run stayed inside provably-unreachable rules and
  whitespace for that reason. A future run that touches CSS *values* needs a
  third guard (rendered-screenshot diff or a computed-style assertion) before
  it is honest.
- **`--probe` conflates two different predictions.** The flag means "expect a
  DISCARD". r4 predicted "the score will improve and I will reject it anyway"
  and the engine fired `PROBE UNEXPECTEDLY IMPROVED`, which was correct on
  score and wrong about the intent. There is no way to journal "expect a
  better score that should still be rejected on the simplicity criterion";
  Step 5's judgment has no flag, so it can only be recorded in prose. Worth a
  doctrine fix if a second run hits it.

## What a human should review

1. The r4 minification decision above; everything else is mechanical.
2. Spot-check one page in a browser against the pre-run version. The guards
   prove the text and structure are intact but cannot prove the CSS still
   *looks* the same, and that residual is stated rather than hidden.
3. `logs/r7-guard1.log` if you want the evidence that the content floor is
   real.
