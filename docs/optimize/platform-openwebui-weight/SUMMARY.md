# platform-openwebui-weight - run summary

**219,045 B -> 198,371 B (-20,674 B, -9.4%)** across the 8-page
`platform/public/clients/openwebui-email-compliance/` prospect site. 5 keeps,
1 discard, 6 rounds. Rendered text byte-identical to the pre-run baseline
throughout.

The number is not the point of this run. Two harness properties are.

## What this run was for

**The scorer is now demonstrably generic.** `page-weight.py` and both guards
ran unchanged against a structurally different page set (different builder
output, a different roster carrying `gdpr.html`). Not one line of scorer or
guard code was touched between runs. Before 2026-07-22 the scoreboard read
`scorer reuse: none reused across runs`; a metric that has only ever measured
one asset is not demonstrably reusable, and now it is.

**Cross-run recall worked, and it cost a round rather than earning one.**
This manifest was written from `platform-alpha-research-weight/SUMMARY.md`,
and two of its decisions came from that journal rather than from
rediscovery. That is the first time knowledge moved between runs through the
artifact instead of through an operator's memory.

## Kept changes (the journal)

| r | delta | change |
|---|---|---|
| 1 | -1,541 | HTML comments outside script/style |
| 2 | -1,603 | CSS rules naming a class/id present nowhere in the file |
| 3 | -4,666 | indentation + blank lines inside `<style>`, readable form kept |
| 4 | -2,024 | indentation, blank lines, `//` lines inside inline `<script>` |
| 5 | -10,840 | markup indentation, only between `>` and `<` |

Run 1 predicted r5 would be the biggest lever despite CSS looking like the
larger target, and it was, by 2.4x over the next-largest round. The prediction
transferred across two differently-built sites, which is weak evidence that it
is a property of this page generator rather than of one site.

## Dead ends

- **Shared-stylesheet extraction was never attempted, on purpose.** Inherited
  from run 1: `page-weight.py` calls `measure()` per file and sums subtotals,
  and `measure()` counts every local `<link rel=stylesheet>`, so a shared file
  is counted once per page exactly like an inline copy. Score-neutral by
  construction. It remains the largest-looking target on the page and is not
  reachable through this metric. Two runs have now declined it for the same
  documented reason; a third should not need to rediscover it.
- **Re-running the CSS reachability pruner after rounds 3-5 yields 0 B**, same
  as run 1. The pruner is idempotent and exhausted at r2.

## Sensitivities

- **The headline is smaller than run 1's (-9.4% vs -14.0%) by choice.** Run 1
  took 9,516 B from collapsing all whitespace around `{ ; : ,` inside
  `<style>`, and flagged it as a maintainability decision that should not be
  inherited by other client sites without the owner's call. This run stopped
  at the readable half. The gap between the two headline numbers is almost
  entirely that one declined round, not a difference in the sites. Reading the
  smaller number as underperformance would invert the intent of run 1's
  sensitivity note.
- **Same appearance blind spot as run 1.** The guard pair pins rendered text
  and structure, not appearance; a CSS change altering a colour, margin or
  breakpoint passes both. Both runs stayed inside provably-unreachable rules
  and whitespace for that reason.
- **A guard proven on one page set is not proven on another**, which is why r6
  repeated run 1's deletion probe here. It fired: `guard-text-preserved`
  failed a whole-`<section>` deletion from `gdpr.html` while `validate-html`
  passed the smaller page. Any future weight run on a new site should repeat
  this probe rather than assume the floor holds.

## What a human should review

Nothing in this diff is a judgment call; every round is mechanical and the
one judgment-bearing lever from run 1 was deliberately not applied. If you
disagree with declining it, applying it here is a single scripted round worth
roughly 9 kB, and that decision belongs to whoever owns the client-page
maintenance burden.
