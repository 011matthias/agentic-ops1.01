# Mini-Checkpoint: Recon Card Scope Applied

**Date:** 2026-09-24
**Status:** Brisken p1 recon, item 190 applied; queue empty
**Type:** mini

---

## Summary
Item 190 (the card filter leaves the month and the selection carries in) is closed. The Lovable prompt had been pasted into the editor but not published; after the owner published it, the bundle was re-audited and the prompt's §7 table driven cold on both tabs, and all eleven rows matched.

## What Was Done
- Bundle audit before any claim about the screen (scratch wrapper over `tools/lovable-bundle-audit.py`'s crawl and controls): controls all found; every item 190 signature ABSENT, `cardTabs.` at 88. A shallow clone of `011matthias/brisken-expense-review` showed `main` `c27c7fd` (13:14Z) already carrying `CardScope.tsx`, `card-scope.ts`, `receipt_months` / `no_card` on `/months` and zero `cardTabs.`: pasted, not published. The backlog said "NOT pasted", the third time this week the tracking lagged the app.
- Static review of the pasted code against the prompt. The one risk (TanStack's default search serializer JSON-quotes a numeric key like `3876`) is handled by a `URLSearchParams` serializer in `src/router.tsx`; every route's `validateSearch` reads strings, so the app-wide swap is safe.
- PR #1300 (`f20fc84a`): recorded "pasted, NOT published" in the backlog heading, PROMPT-STATUS, the status file and the prompt header.
- After the owner published: the bundle re-read clean (all six signatures present, `cardTabs.` 0, `wb.filter.card.empty` 0). A cold real-Chrome drive then covered 1176 in August on both tabs, refresh plus back twice, Show all cards, 4700 as `digits%3A4700`, No card as `none`, the pasted July link, 9693 behind the disclosure, 3876 through January, and 0113 empty, and every row matched. The old `brisken.month.cardTab.v1:` key was proven deleted by seeding it for August and July and loading August (only August's entry went), because a fresh session having no key proves nothing.
- PR #1307 (`300eda6e`): item 190 APPLIED. The PROMPT-STATUS row moved to Applied with the drive evidence.
- `/feedback.jsonl` read: 86 notes, none new.

## What Did NOT Work (and why)
- **Driving the unpublished build locally** (npm install + `vite dev` in a scratch clone against the live API, which admits localhost via CORS): denied by the auto-mode classifier as executing external code. The pre-publish check stayed static; the drive waited for Publish.
- **`agent-browser click 'a[href^="/expenses/..."]'` from Git Bash:** reported Done and did not navigate (a leading-slash argument shape MSYS rewrites). Click by a fresh `snapshot -i` ref instead; refs go stale after any navigation.

## Current Status
Recon queue empty. Fly still at `93c69551` (no code this session). One cosmetic residual, recorded and not re-prompted: the "Nothing on card {card} in {month}" state still shows the tabs and an all-zero Reconciliation line above its one line. Context ~240k at close.

## Next Steps
1. Read `/feedback.jsonl` first; a new note becomes the next item.
2. Only if the owner reports `/months` or `/cards` loading slowly: a per-run cache in `build_card_status` keyed on the month's `updated_at`.
3. Waiting on others: Dirk (statements for 9693, 0113, 6013, 8311); Criss or the owner (card 3645 `zoho_account`, item 172; August `0008__Invoice-HMVWDWIL-0029.pdf` and `0027__Invoice-HMVWDWIL-0028.pdf` picked 2838 where the charge posted on 3645); the owner (commercial framing for directive-driven surfaces under the October licence).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 190 section)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Applied, first row)
