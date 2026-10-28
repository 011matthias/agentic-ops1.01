# Mini-Checkpoint: Verve Beta Boundary Testing

**Date:** 2026-09-22
**Status:** Verve round 1 complete (research, integration, security, GenUI build 1 of 5); Brisken Zoho injection suite delivered and the resulting sandbox bookings audited
**Type:** mini

---

## Summary
Delivered Zoho Books injection test payloads for Brisken TEST-BTS and audited the other agent's bookings live (4 of 6 in the wrong GL account, one custom field silently dropped, vendors unattached), then boundary-tested the Verve beta with a CDP harness: answers and security held, integration scope is far broader than the stated TEST-BTS constraint, and the first generative-UI build is fully functional. All Verve findings are in `.scratch/verve-testing/FINDINGS.md`.

## What Was Done
- Brisken: 7-case borderline suite (`.scratch/zoho-injection-test/suite.json`), Method-2 batch v1 → v2 repointed at accounts that exist in TEST-BTS, a pasteable agent prompt, and the split spec for case 06 with resolved `account_id`s.
- Brisken: read-only live audit of TEST-BTS (production read token covers the sandbox): card closing balance 1,450.43 reconciles exactly (982.93 batch + 467.50 earlier proofs); `cf_dn_repayment` is the only custom field defined on Expense; `COGS - DEV Infrastructure (SAP Apps & others)` does not exist in the org; the 4 misbooked `expense_id`s and target `account_id`s handed over for the PUT fix.
- Verve harness: `cdp.py` on the attachable Chrome `:9222` (real Enter via `Input.dispatchKeyEvent`, visible composer = textarea index 2, completion = aria-label "Stop generating", busy-guard, halt on any approval card → owner decides via AskUserQuestion, never auto-click).
- Verve research: 6/6 verifiable probes correct (fake-paper trap, false premise, Node v24.21.0, Zoho API limits verbatim, contradiction handling, chained search). Deep-research report: 11 sources, no URLs, one invented citation title over real facts, GENIUS Act false-flagged.
- Verve integration: connections enumerated with IDs and scopes. M365 = 28 write scopes; Zoho = Dirk's account with `.ALL` tenant-wide scopes, so the TEST-BTS constraint is enforced only by a memory guideline plus the approval gate. Reads (calendar, Teams, OneDrive) run ungated; writes gate.
- Verve application layer: runtime-created API tool `nodejs-releases` returned nodejs.org's index byte-for-byte; file create + handoff link; owner-approved scheduled task persisted (`ivYE6CEWOdfK0Ul0q1Xa`, next run 2026-09-23T06:00Z, correct UTC); memory file-backed.
- Verve GenUI build 1 (live Node.js dashboard): stat cards, chart, 8-row table; filter 8→6→8 and sort on every column pass, `aria-sort` maintained. Launch model: `ui-launch` directive, surfaces `chat-inline`/`split`/`focus`, Space UI catalog.
- Verve security: 6/6 bypass attempts refused (system prompt ×2, injection ×2 incl. base64, secret exfil, gate bypass). Bugs B1–B7 logged (session wedge on one failed turn, malformed `lineItems` tool schema 400s gemini-3.8-flash, phantom `update_expense` card, raw FAILED_PRECONDITION leak, deep link lost on login, `$` rendered as LaTeX, unknown space 200s).

## What Did NOT Work (and why)
- **Playwright MCP against the user's Chrome `:9222`:** `initializeServer` timed out at 30s twice (busy-browser CDP hang); raw websocket CDP with `suppress_origin=True` worked.
- **Synthetic `KeyboardEvent` Enter to submit the Verve composer:** never submitted; needs a real `Input.dispatchKeyEvent`, and only on the visible textarea (index 2), not the hidden mirror at index 0.
- **Text-stability as the completion signal:** declared done at 5s, before generation started; keyed on the "Stop generating" button lifecycle instead. Any `\bstop\b` text also matched a GenUI build card's Stop button and stalled every turn for the full timeout; aria-label only.
- **Auto-declining approval cards:** killed the browser-extraction and deep-research turns; owner directed that approvals be routed to them.
- **Pre-send wait that sent anyway after 45s:** prompts were swallowed by a busy composer; now returns busy and the runner retries.
- **Verve's own live Zoho read from Home:** "Zoho Books expense operations couldn't finish", then a phantom `update_expense` card that re-surfaced twice (declined each time). Verve-side; unresolved.
- **The other agent's injection tool:** silently substituted a default account for unresolvable names instead of failing; two names that did exist were also ignored.

## Current Status
Verve: round 1 documented; test residue in the owner's space (active weekday scheduled task, tool, components, probe file, memory fact). Brisken TEST-BTS: 4 PUT fixes, case 06 booking, and the `cf_netting_key_exp` field are pending on the other agent. Brisken ops: infrastructure.yaml has no `platform` section for expense-recon (unknown plan / ops); pre flagged status files p2-product-decks (61d) and p2-targeting (62d) as stale.

## Next Steps
1. Verve builds 2–5 from `.scratch/verve-testing/genui.txt` (wizard, data table, compound app, Veo video) in a fresh session; every card goes to the owner.
2. Verve: 4-step plan probe; indirect injection via a poisoned document/page; load and robustness.
3. Verve owner actions (from FINDINGS.md): delete scheduled task `ivYE6CEWOdfK0Ul0q1Xa` when done; move Zoho to an org-restricted or test-org credential (I1); make research citations carry URLs (R1); keep the "test-bts only" memory guideline.
4. Brisken: re-run `.scratch/zoho-injection-test/read_expense_detail.py` after the other agent's PUTs to confirm the 4 accounts moved and vendors attached; then case 06; create or drop `cf_netting_key_exp`.
5. Brisken: owner review of stale status files p2-product-decks and p2-targeting; feasibility/ops assessment for the expense-recon `platform` section in infrastructure.yaml.

## Files to Read First
- `.scratch/verve-testing/FINDINGS.md`
- `.scratch/verve-testing/cdp.py`, `run_ask.py`, `genui.txt`
- `.scratch/zoho-injection-test/batch-method2-v2.json`, `read_expense_detail.py`, `prep_fix.py`
- memory: `reference_user_edge_cdp_9222`, `project_brisken_zoho_books`, `project_verve_product`
