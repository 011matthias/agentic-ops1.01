# Mini-Checkpoint: Brisken Recon Card Attribution Case Map

**Date:** 2026-09-24
**Status:** Analysis + prompt-writing session; no code shipped from here. One of its prompts (card type) already shipped via a sibling as item 198 (#1334).
**Type:** mini

---

## Summary
Mapped every way a receipt's payment text leads (or fails to lead) to a card, company and person in the recon tool, measured each case on all 265 live receipts, and wrote six fresh-chat prompts that close the gaps in an owner-approved order. The central remaining piece is case 9 ("no payment info"), handed to a planning session.

## What Was Done
- **Case map** (read-only census, 7 live months, 265 receipts): printed Brisken number 153; statement charge 30; Criss's pick 10; registry card 2; confirmed private 2; nothing printed 34 open; generic card word 12; non-Brisken card type 4; cash 2; unrecognised phrase 7; non-Brisken number 7; two-digit ending with no card 1; bank transfer 1. Explained the unknown-cards panel row by row (September).
- **Owner rulings captured (2026-09-24)**, each recorded inside its prompt:
  1. A Brisken card TYPE (Visa / Mastercard, credit, derived from the registry labels + Zoho accounts) is case 1: no private label, wait for the statement / vendor memory. Supersedes item 41's "Cartao de Credito" example. **Shipped by a sibling as item 198, PR #1334.**
  2. Private-card list (separate `private_cards` settings key, last-4 only, auto-applied private with person, explicit entry via Settings or the strip's Remember switch; per-row confirmation never teaches). Supersedes the 2026-08-22 "personal tenders never learned" ruling for card NUMBERS only.
  3. Two-digit ending wordings: explicit lead phrases in EN/PT/DE/FR/ES plus an amount guard (`final 38,00` is not an ending).
  4. Vendor history: a vendor's card derived (not memorized) from its own receipts, >=2 hard-evidence receipts on one card and none elsewhere, measured-first gate; also removes `learned` from `_CARD_OBSERVATION_SOURCES` (circularity). **ON HOLD** until the case-9 plan returns.
  5. Flip the private default: suggest private ONLY on positive non-Brisken evidence; every other text (incl. unseen phrases) waits; tokenizer for glued words (`girocardOLV` stays private, `CreditCard` waits); non-Brisken issuer list, acquirers neutral. Supersedes item 41's trigger.
  6. Case 9 planning prompt (planning only; plain-language relay to the owner, technical appendix as one backlog item).
- Live findings worth keeping: GoDaddy "ending with the last two digits: 38" misses the note-#60 regex (only live miss); June Fenix `3976` is probably an OCR slip of 3876; Namecheap's June "CreditCard" would land on 3876 via vendor history (four May receipts print `...3876`).

## What Did NOT Work (and why)
- **Collapsing the "why no chip" question into one AskUserQuestion:** the owner rejected it; the question spans eleven cases, not one threshold. The case map was the right answer.
- **First card-coverage probe:** read `coverage[].n_tx` / `statements` under wrong keys and reported no card coverage in ANY month, including July and August which have it. Probe was blind; the direct read of `coverage[].card_key` / `statements` / `period_*` is the valid one.
- **"28 of 34 open receipts sit in months with no statement":** wrong. Only May + June (8) have none; September gained a 9693 statement (5 Aug-4 Sep, 32 charges, 5 matched) at 21:22 UTC via a sibling session (#1332). September's 20 stay open because their dates (6-22 Sep) fall in the NEXT 9693 cycle. Corrected in the re-issued planning prompt.
- **Heredoc with a Python triple-quoted block:** blocked by the heredoc gate; scripts go through the Write tool.
- **`Set-Location` into the module dir to import its code:** refused by cd-guard; `uv run --project <module> python <script>` from the repo root works and keeps relative `.env` reads intact.

## Current Status
- Shipped (sibling): card-type rule, item 198 (#1334).
- Prompts written, not yet run: private-card list; two-digit wordings; positive-evidence flip; case-9 planning (the corrected re-issue is the one to use, reproduced below).
- Held: vendor history (waits for the case-9 plan).
- Owner-side: loading the earlier 9693 cycles and the other missing cards' statements remains the owner's call; September's 9693 cycle is now loaded.
- Status files not touched (no workstream element changed state from this session).

## Next Steps
1. Run the positive-evidence prompt and the private-card-list prompt (both build on item 198, now merged); the two-digit wording prompt can run any time.
2. Run the case-9 planning prompt below in a fresh chat; its plain-language result decides the held vendor-history prompt.
3. After the plan: build prompts per approved step.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 41, 108, 111, 154, 169-173, 198)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/cards.py` (`GENERIC_TENDER_WORDS`, `is_generic_tender`, `_SHORT_ENDING`, the item-198 classifier)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` (`resolve_batch_row_cards`, `fill_remembered_cards`, `registry_card_upserts_from_expense_run`, `_CARD_OBSERVATION_SOURCES`)
- The full text of all six prompts is in this session's transcript: `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/3cf8ea47-51eb-4a36-b73a-ddc79ed98f39.jsonl` (search for "Continuation prompt for Claude Code").

## Case-9 planning prompt (corrected re-issue, the version to paste)

Paste into a fresh Claude Code chat. It opens with `/comd_resume brisken` and carries the SESSION LOOP. Its facts section was corrected at ~22:00 UTC on 2026-09-24: statements loaded in April, July, August and (since 21:22 UTC) September's 9693 cycle 5 Aug-4 Sep; open no-payment receipts May 5, June 3, July 5, August 1, September 20 (34 of 51 no-payment receipts; 17 already resolved: statement 10, pick 5, registry 2); card cycles do not align with calendar months, which is the central question for lever A. The planning session evaluates levers A (charge data that reaches the right receipts in time: cycle vs month, mid-cycle activity export, missing cards), B (pairing a no-card receipt against every card's charges), C (vendor history, held), D (evidence inside the invoice or mail: bill-to, account e-mail, forwarder; company-without-card is an owner decision under item 40), E (recurring charges), F (bulk assign by vendor + an honest "waits for the 9693 statement closing 4 Oct" status); relays the plan in plain language (no code terms, cards named as Criss knows them, 3-6 steps with receipts handled and risk, decisions with recommendations); records the technical appendix as ONE backlog item; writes build prompts only after the owner approves. The exact text is in the transcript above (the second "PLAN the no payment info backbone" prompt).
