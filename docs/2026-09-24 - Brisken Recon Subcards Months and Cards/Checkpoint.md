# Checkpoint: Brisken Recon Subcards Months and Cards

**Date:** 2026-09-24
**Status:** Item 191 applied and driven; item 194 prompt written, not pasted

---

## Summary
Dirk's 2838 account tree (3645, 3876, 0340 under 2838) is now data in the live card registry and drives the `/months` card strip, where the subcards open only behind 2838. The same logic for the `/cards` overview table is a Lovable prompt awaiting the owner's paste.

---

## What Was Done This Session

### Lookup
1. Answered "which cards sit under 2838": 3645 (Dirk, Corp Services), 3876 (Nicolas), 0340 (Criss), from backlog item 147's 2026-09-18 ruling "only 2838 has subcards". 1672 is 2838's plastic number, not a subcard.

### Item 191: months strip nests subcards (backend + SPA, APPLIED)
1. `GET /api/cards/status` gained `cards[].parent` and `cards[].subcards` from `card_parents` over the LIVE registry (a month keeps its snapshot). PR #1310, merge `fe8699ee`, deployed and stamped.
2. Tests `tests/test_card_status_subcards_item_191.py` (5, route-level); `regress_check` red on the route's `parents=` wiring and on the per-row stamp; full module suite 3299 passed.
3. Owner yes ("in books there is only 2838 registered"): set `parent = card-2838` on 3645, 3876, card-0340 via one read-modify-write `PUT /api/settings` after a read-only readiness check; stored group diffed after: exactly three field changes.
4. Prompt `docs/lovable-months-subcards-prompt.md`; owner pasted (`41dc0f4`) and published. Bundle carries every signature (controls found); all ten check-table rows driven cold in headless Chrome and matched.

### Item 194: Cards overview nests subcards (prompt only)
1. `docs/lovable-cards-overview-subcards-prompt.md`: subcard ROWS collapse under the account row (chevron + "3 cards on this account"), own figures, open-work order, fold never holds a subcard. No backend work. Check table figures read live.

### System
1. `warn-flyctl-deploy-git-commit` upgraded to `block-flyctl-deploy-git-commit`, narrowed to `brisken-expense-recon`; tested block / stamped-recipe no-match / other-app no-match; lint 0; pattern tests 49 passed.
2. Memory `project_brisken_expense_recon_fly_hosting.md`: the "recipe that works" line now carries the stamp, the `C:/` path and the no-sed rule.

---

## Key Decisions Made

### The tree is read from the registry, not hard-coded
- **Choice:** SPA nests on `parent` / `subcards` from the payload.
- **Rationale:** item 147 already modelled the tree; a hard-coded "2838 owns three" in the SPA would silently disagree the first time a card moved.

### Account figures stay the card's own
- **Choice:** neither the 2838 chip nor its `/cards` row sums its subcards.
- **Rationale:** owner said "maintain their filter function"; summing would change what the 2838 filter answers.

### Parents set by the agent on the owner's yes
- **Choice:** agent wrote the three parents (AskUserQuestion, recommended option).
- **Rationale:** live registry had `parent` empty on all nine cards, so nothing could nest; existing months do not read the live registry, so blast radius is the strip plus months created from now on.

---

## What Did NOT Work (and why)
- **`regress_check --with "parents={} or card_parents("`:** `{}` is falsy, so `or` still called `card_parents`; the tool correctly reported TEST DOES NOT BITE. `parents=None and card_parents(` disabled it.
- **Deploy piped through `sed "s/$TOK/[redacted]/g"`:** the Fly token contains `/`, sed died with "unknown option to s", and flyctl kept running and shipped v216 with an empty `/healthz` commit.
- **`MSYS_NO_PATHCONV=1 flyctl deploy /c/Users/...`:** flyctl tried to chdir to `C:\c\Users\...`; a `C:/Users/...` path works.
- **Claiming a backlog number by checking `origin/main` once:** the check ran well before the merge, a sibling merged its own "item 193" (#1320) minutes after this session's #1319, and both carried 193. Renumbered this session's (docs only) to 194 in the checkpoint PR; the sibling's is baked into a test filename.
- **Python Playwright cold drive to close deploy-consumer-gate:** the gate recognises only agent-browser / Playwright MCP read-backs, so the drive was repeated through agent-browser.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` | edit | `build_card_status(parents=)` stamps `parent` / `subcards` |
| `.../web/app.py` | edit | route passes `card_parents(effective_cards(...))` |
| `.../tests/test_card_status_subcards_item_191.py` | new | 5 route-level tests |
| `.../docs/lovable-months-subcards-prompt.md` | new | item 191 SPA prompt (APPLIED) |
| `.../docs/lovable-cards-overview-subcards-prompt.md` | new | item 194 SPA prompt (not pasted) |
| `.../docs/PROMPT-STATUS.md` | edit | 191 → Applied with evidence; 194 Not applied |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | items 191 (applied), 194 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | item 191/194 entry |
| `.claude/patterns/block-flyctl-deploy-git-commit.md` | rename + edit | warn → block, narrowed |
| live registry `settings.cards` (brisken-expense-recon) | write | three `parent` fields (owner yes) |

---

## Current Status
Backend live at `fe8699ee` and carried in the sibling's later `45d4c494`. `/months` nests 2838's subcards on the published SPA. `/cards` still lists all four as flat rows until the item 194 prompt is published. Ops status for brisken: platform section unknown in `infrastructure.yaml` (FastAPI on Fly, not an orchestrator plan). PRs #1310, #1311, #1315, #1319 merged.

---

## Next Steps
1. Owner pastes and publishes `docs/lovable-cards-overview-subcards-prompt.md` (item 194).
2. Then bundle-audit `cardsPage.subcards.count` (present) with the five controls, and drive its check table cold; move its PROMPT-STATUS row to Applied.
3. Card 3645's `zoho_account` still reads `Credit Card - 2838` instead of `CHASE VISA - 2838 - TRAVEL` (item 172): Criss's or the owner's call, untouched.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-cards-overview-subcards-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 191, 192, 194 (193 is a sibling session's strip-count item)

### Open Questions
- None open. If the owner later wants the 2838 row on `/cards` to show account totals, that is a new decision: both prompts deliberately keep own figures.

### Working Notes
- Drive helpers in this session's scratchpad: `drive_191_table.py` (cold Playwright, prints tablists + month rows per pick) and `audit191.py` (imports `tools/lovable-bundle-audit.py` with custom signatures, no edit to the tracked tool). Reuse the pattern for item 194.
- Live numbers 2026-09-24: 2838 open work 96, 3645 83, 3876 77, 0340 24, 9693 16, 1176 9, 4700 2; fold 0113, 6013, 8311.

### Reference Materials
- Lovable repo `011matthias/brisken-expense-review` (`41dc0f4` = item 191 paste)
- `https://brisken-expense-recon.fly.dev/healthz` (`server.commit`)

---

## How to Continue
`/resume brisken`, then wait for the owner's publish of item 194 and verify it (bundle + cold drive). Nothing else in this thread is open.

---

## Strategic Feedback

### What Worked Well This Session
- Reading the live registry before building found `parent` empty on every card, which turned a would-be dead feature into an explicit owner decision with its read-only half done first.
- Every negative was proven against a control: the bundle audit carried item 194's key as an expected ABSENT, and `regress_check` refused a mutation that did not disable anything.

### Suggestions
- Hooks read `.claude/patterns` from the session's primary checkout. This one started 17 commits behind, so `warn-chained-checks-watch-and-merge` (created today on main) never loaded and the chained merge on PR #1315 recurred for a fourth session. SessionStart could fast-forward `.claude/patterns` from `origin/main` (or the gate could read them via `git show origin/main:`) when the checkout is behind.

### System Health
- deploy-consumer-gate closes only on agent-browser / Playwright MCP read-backs, while the repo's established cold-drive method (sibling sessions too) is a `uv run` Playwright script, so a real drive has to be repeated to satisfy it.
- Autonomy: 1 human intervention (the invasive-write decision on the three parents, by design).
