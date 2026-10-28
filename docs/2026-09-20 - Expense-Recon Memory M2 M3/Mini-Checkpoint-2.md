# Mini-Checkpoint: Expense-Recon Memory M2 M3

**Date:** 2026-09-20
**Status:** M2 shipped and live (Fly v189); M3 read done and derived, write parked by the owner; M4 not started
**Type:** mini

---

## Summary

The MEMORY session's second iteration shipped note item M2 (a merchant's card,
learned from exclusive spend) and completed note item M3's owner-authorised
read of two years of Zoho Books. The owner reviewed the derived seed row by row
and parked the write; the reason is a measurement, not a preference, and it is
recorded as backlog item 156.

## What Was Done

**M2, backlog item 154, PR #1110, merge `90dc5c3b`, Fly v189.**

- Measured first on the live months: 128 rows, 60 display vendors, **34 on
  exactly one card, 5 on several, 21 on none**. The five are the AI vendors and
  the spellings around them, the same exceptions M1 found for categories.
- Registry gains `card_key`, `card_key_learned`, `cards_seen` (parallel, absent
  until set). `card_source: "merchant"` is the last link of the item-87 chain,
  under the same guard as `learned`; `can_mark_private` stays true on it.
- Sign-off learns it: `cards_seen` accumulates the month's resolved cards per
  merchant, a key is written only while exactly one card has been seen, a second
  card drops a LEARNED key, an editor-typed key is never touched, and a row
  carried by `merchant` teaches nothing so a lent card cannot harden into a fact.
- Wired on every surface holding live settings (grid, CSV, month PDF listing +
  card pass + card sections, cost-center roll-up, refresh preview). Deliberately
  not `rematch_month`, and `merchant` is kept out of `CARD_SCOPE_SOURCES`, so no
  pair moves and the accuracy gate is untouched.
- 10 route-level tests; three wires proven red under mutation. Suite 2575 ->
  2601 passed / 2 skipped after merging two siblings.
- Verified live: card resolution on July, August and September is byte-identical
  pre and post deploy (no live row moves, as designed, since no live registry
  merchant carries a card), plus a cold scripted Playwright drive of July's
  Expenses page (57 rows, cards rendering, no fallback, no writes but the login).
- Also recorded M1 (PR #1094, Fly v184) in the backlog heading and Shipped row
  100, which its own PR had left pending.

**M3, backlog item 156, PR #1118, merge `a1854310`.** One read-only pass over
Zoho Books, 2024-09 to 2026-09, seven real orgs: 2,355 expenses + 1,179 bills,
174 distinct vendors. Derived 91 registry candidates, 32 genuinely new (company,
vendor) rules and a per-merchant card observation. Nothing applied.

## What Did NOT Work (and why)

- **`regress_check.py` on the CSV export wire:** returned the doubtful
  `RED (no pytest summary line)` even though the mutation did bite. Re-done by
  hand with a `cp` backup, which showed the real failure (the CSV falls back to
  `(paid-through - assign)` / `(entity - assign)`, 1 failed / 9 passed) and
  restored cleanly. The tool's verdict was right; only its parse of the output
  was not.
- **The first M3 dedup count (95 new rules) was wrong.** It compared the WRITE
  endpoint's field name `legal_entity_id` against read rows, and `GET
  /api/memory` names that same value `entity` on `categories[]`. The write name
  reads None on all 103 live rows, so every existing rule counted as new. Caught
  by printing one row's keys instead of trusting the field name; the real number
  is 32. Instrument-validity, exactly the shape rule_behaviors B2 names.
- **Backlog numbering raced twice.** 152 was claimed by TRACEABILITY's T3 and
  then 153 by T1 while the M2 branch was in flight, so the item and its two
  Shipped rows were renumbered twice (ending at item 154, rows 100 and 101). The
  merge itself stayed clean because both sides were appends.

## Current Status

M2 is live on Fly v189 and changes no live row today: the 28 registry merchants
carry no card, so the new chain link is silent until an entry gains one, either
by hand in Settings or by a month publishing with a registry merchant on a
single card. Its Lovable half (`docs/lovable-merchant-card-prompt.md`) is
written and NOT applied.

M3's raw pull and derived candidates sit in the gitignored
`workspace/clients/brisken/context/expense-reconciliation/`
(`zoho-books-24mo.json`, `zoho-seed-candidates.json`) with the dry-run/apply
script beside them in the session scratchpad. The owner's decision is "nothing
yet", and backlog item 156 carries the three findings that drove it, including
the blocking one: the 24 months use **52 distinct Zoho expense accounts** and
the account -> category map inferred from the 103 seeded rows covers only 20,
leaving 30% of rows (all ad spend, all travel) unruled.

brisken platform: unknown plan, ~?/? ops/mo, last assessed ?. The comms log is
12 days stale. Two p2 status files are stale (p2-product-decks 59d,
p2-targeting 60d); they belong to the lead-gen workstream, not this session.

## Next Steps

1. **M4** (the queue's last item): a free-text `profile` on each registry entry,
   read by the categorizer as nonce-fenced untrusted context, shown on the
   Memory page, edited in Settings; then judge backlog item 118 (a cost-center
   pick teaches nothing) and either close it as a one-line addition to
   `registry_upserts_from_expense_run` or leave it open with the reason.
2. Hand the owner the M2 Lovable prompt to paste, so the Settings editor can
   carry `card_key` / `card_key_learned` / `cards_seen` (a save that omits them
   erases accumulated observation).
3. Waiting on the owner, unchanged: the OpenAI / Anthropic / Lovable registry
   write (do NOT re-ask), Dirk's 3x3 account table, and now the M3 seed.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 118, 154, 156
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`,
  the M2 section "A merchant's spend is often on ONE card"
- `.../src/expense_recon/merchant_registry.py` and `web/service.py`
  `resolve_batch_row_cards` + `registry_card_upserts_from_expense_run`
- `.../docs/lovable-merchant-card-prompt.md` (not applied)

---

## Continuation Prompt (next session, verbatim)

/comd_resume brisken

Owner directive 2026-09-18, still standing: the items in this prompt have priority and are to be built now; the covered-vs-quote licence question does not gate them. You are the MEMORY session (third iteration). Sibling sessions (TRACEABILITY in `agentic-ops1-trace`, MATCHING in `agentic-ops1-match`) run at the same time on the same repo and the same Fly app: follow the parallel-safety rules in "How to work" exactly.

Read first: `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`, then in that module `docs/api-contract.md` sections "Merchant-to-category is the default" (note item M1) and "A merchant's spend is often on ONE card" (note item M2), `src/expense_recon/merchant_registry.py` (docstring + `normalize_merchants_setting` + `MerchantMatch`), `src/expense_recon/categorize.py` (`categorize_receipts_with_registry`, `_classify_lines_via_llm`, `_classify_vendor_via_llm`), `src/expense_recon/untrusted.py` (the nonce-fencing shape), `src/expense_recon/web/service.py` `registry_upserts_from_expense_run` and `registry_card_upserts_from_expense_run` (adjacent, near `commit_to_memory`), backlog items 47, 116, 118, 149, 154, 156 in `workspace/clients/brisken/status/p1-improvement-backlog.md`, and the memories `project_brisken_expense_recon_merchant_registry`, `project_brisken_expense_recon_usability_loop`, `feedback_recon_no_live_writes_criss_acts`, `feedback_no_invasive_action_without_ask`, `feedback_continuation_prompt_carries_loop`, `rule_untrusted_inbound`.

## Where it stands

**M1 shipped 2026-09-18** (backlog 149, PR #1094, merge `d1c8e733`, Fly v184; Shipped row 100). The registry default is the CATEGORY on every receipt of its merchant; the (company, vendor) rule decides the ACCOUNT; `GET /api/memory` carries `by_vendor[]` + `categories[].seeded`.

**M2 shipped 2026-09-18/19** (note item M2, backlog **154**, PR #1110, merge `90dc5c3b`, **Fly v189**; Shipped row 101). Suite 2575 -> 2601 passed / 2 skipped. What is live:

- Registry entries carry `card_key`, `card_key_learned`, `cards_seen` (parallel, absent until set, capped 64 chars / 32 entries). `card_key` is NOT validated against the card registry, so the edit order of cards and merchants does not matter.
- `card_source: "merchant"` is the LAST link of the item-87 chain (`resolve_batch_row_cards`, `merchants=` kwarg), after `override` > `hint` > `settled_charge` > `learned`, under the same guard: only when the receipt prints no card number, names no assigned hint, and is not confirmed private. `can_mark_private` stays **true** on it, as on `learned`.
- Sign-off learns it: `registry_card_upserts_from_expense_run` accumulates `cards_seen` from the month's resolved cards per merchant, writes `card_key` only while exactly one card has been seen (marked `card_key_learned`), DROPS a learned key when a second card appears, and never touches an editor-typed key. A row carried by `merchant` teaches nothing, so a lent card cannot harden into a fact. `memory.learned.registry` gained `cards_seen` / `card_keys_learned` / `card_keys_dropped`.
- Wired on every surface holding live settings: grid, CSV export, month PDF (listing via `_expense_export_inputs`, card pass, card sections via `report_receipt_cards`), cost-center roll-up, refresh-master-data preview. Deliberately NOT `rematch_month`, and `merchant` is not in `matching.deterministic.CARD_SCOPE_SOURCES`, so it never scopes matching (that surface is MATCHING's).
- Live verification: card resolution on July/August/September is byte-identical pre and post deploy (no live row moves — the 28 registry merchants carry no card), plus a cold scripted Playwright drive of July's Expenses page (57 rows, cards rendering, no fallback, zero writes but the login).
- SPA half `docs/lovable-merchant-card-prompt.md`, **NOT pasted** (PROMPT-STATUS Not-applied row). The Settings editor replaces the whole merchant map on save, so it must carry all three new fields or they are erased.

**M3 read done, write PARKED by the owner 2026-09-19** (backlog **156**, PR #1118, merge `a1854310`). One owner-authorised read-only pass over Zoho Books, 2024-09 to 2026-09, seven real orgs: 2,355 expenses + 1,179 bills, 174 distinct vendors. Raw pull and derived candidates are in the gitignored `workspace/clients/brisken/context/expense-reconciliation/` (`zoho-books-24mo.json`, `zoho-seed-candidates.json`). Derived: 91 registry candidates, 32 genuinely new (company, vendor) rules, 90 vendors on exactly one Zoho paid-through account. **Nothing applied.** The owner's three reasons are in item 156 and the blocking one is a measurement: the 24 months use **52 distinct Zoho expense accounts** and the account -> category map inferred from the 103 seeded rows covers only **20**, leaving 30% of rows (all ad spend, all travel) unruled. Do NOT re-run the write without the owner raising it; when he does, re-derive first (the pull is point-in-time), re-run the resolver safety check, and exclude the 11 (five duplicate spelling pairs + `N Neumann`, which measurably claims `M Neumann` at score 100) plus `Google Ads` (it renames `Google LLC` receipts), and drop Eleven Labs' card_key (live months contradict it).

**Waits on the owner (do not re-ask unprompted):**
- The live registry write for OpenAI / Anthropic / Lovable. Asked once at the end of the M1 session; he answered "not yet, and dont re ask, i will bring this up again when the time is right." When he raises it: rebuild the script (28 live entries carried verbatim + `Anthropic` {aliases `Anthropic, PBC`, `Anthropic, PBC @anthropic`, `Anthropic, PBC (@anthropic)`}, `Lovable` {aliases `Lovable Labs`, `Lovable Labs Incorporated`, `Lovable Labs Incorporated (@lovable)`}, `OpenAI` {aliases `OpenAI`}, each category "Software & Subscriptions", `zoho_account` null, no `multi_category`; PUT `/api/settings {"merchants": <31>}`, then GET and diff), dry-run, show the diff, PUT on his yes, GET and verify.
- Dirk's 3x3 account table (OpenAI / Anthropic / Lovable x Cloud Services / Corporate Services / Consulting). **The M3 read answers 7 of the 9 cells from real posting history**, which is worth handing him when he asks: Anthropic -> Corporate Services "COGS - Other Infra and IT Costs for Cloud Business" (n=44, spelled "Antropic") and Cloud Services "COGS - DEV Infrastructure (SAP Apps & others)" (n=5); OpenAI -> Corporate Services "COGS - Other Infra and IT Costs for Cloud Business" (n=19) + "IT: Cloud Subscriptions-Others" (n=5) and Cloud Services "COGS - DEV Infrastructure (SAP Apps & others)" (n=10); Lovable -> Corporate Services "CorpServ | IT Expenses" (n=37) + "Marketing Expenses - others" (n=15) and Consulting "IT: Cloud Subscriptions-Others" (n=1). History is what was done, not necessarily what should be; his ruling governs. When the answers arrive: `PUT /api/memory/categories` per cell (`legal_entity_id` is the SHORT label — "Cloud Services", "Corporate Services", "Consulting" — which the READ payload names `entity`; `vendor` = the vendor_norm the receipts key on: `anthropic pbc`, `anthropic pbc anthropic`, `openai`, `lovable labs incorporated`, `lovable labs`, plus the bank descriptions `anthropic`, `openai`, `lovable` for the charges), category "Software & Subscriptions", then `POST /api/memory/categories/validate`. One `AskUserQuestion` for the batch with the rows shown.
- Lovable paste of `docs/lovable-memory-by-company-prompt.md` (M1) and `docs/lovable-merchant-card-prompt.md` (M2).
- The parked M3 seed, and the 52-row Zoho account -> tool category table that gates its category half.

**Incidental, recorded not changed:** `settings["entities"]["Brisken Corp Services, LLC"].org_id` reads `8227416528` (ten digits); the real Corporate Services org is `822741658` (nine). Nothing in M1-M3 depended on it; the COA provisioning that does read it was out of scope.

## Queue, in order (note item M4 is the last one; M1, M2 done, M3 parked)

Append to the backlog as its own item when you first push, next free number at that moment (156 was the highest on main at the M3 push), "(note item M4)" kept in the heading.

1. **M4 A profile of unstructured knowledge beside the registry.** Add `profile` (free text, parallel, absent until set, capped like `receipt_portal`'s 200 chars — pick a larger cap, this is prose) to each registry entry in `normalize_merchants_setting`: what the business buys from this merchant, on which card and for which company, anything Criss or Dirk would tell a new bookkeeper. The categorizer reads it as context for that merchant's receipts (prompt-level, in `_classify_lines_via_llm` / `_classify_vendor_via_llm` via the LLM client's classify calls), **marked as untrusted data per `rule_untrusted_inbound` and nonce-fenced exactly the way `expense_recon/untrusted.py` already does it: it informs the category, never instructs.** The Memory page shows it (`by_vendor[].profile`), the Settings editor edits it (whole-map replace: the Lovable prompt must carry the field on every save or it is erased), and the learning path may append observations to it only as clearly marked machine lines (`[tool 2026-09-20] ...`). Then read backlog item 118 (a cost-center pick teaches nothing) and **close it if** the same registry-upsert path makes it a one-line addition — `registry_upserts_from_expense_run` already carries the whole entry per item 116, and `registry_card_upserts_from_expense_run` (M2) is the worked example of folding a second fact into the same pass, so folding a row's cost-center pick into the merchant entry's `cost_center` at sign-off with the same conflict-skip rule categories use should be small. Note that item 118's own "reviewer corrections" paragraph claims sign-off ERASES merchant `cost_center` entries; that was true before item 116 and is not true now, so verify against the current code before repeating it. Otherwise leave 118 open and say why.

When the queue is empty, follow SESSION LOOP step 9.

## How to work

- Your worktree, cut fresh: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 fetch origin` then `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add -b client/brisken/p1-memory-m4 C:\Users\neuma_p1qrsic\Repo\agentic-ops1-memory origin/main` (remove a leftover `agentic-ops1-memory` worktree first if one is listed). Never edit, commit or stash in the main checkout; never `git stash` anywhere. A hook refuses `cd X && ...`; use `git -C`, `uv run --directory`, absolute paths. The main checkout is hundreds of commits behind: read source from YOUR worktree, never from it.
- Siblings edit `web/service.py`, `web/app.py`, `tests/test_view_contract.py`, `docs/api-contract.md`, `docs/PROMPT-STATUS.md`, the backlog and the status file all day. Append at the END of the relevant block; never renumber, re-sort or reflow. Before the first push `git rebase origin/main` is fine (commit first); after any push only `git merge origin/main`, never rebase, never force-push. Re-run the module suite after every merge from main. On a conflict in a shared file keep both sides. **Claim a backlog number and a Shipped row number only after a fresh `git merge origin/main`, immediately before the push — both were taken out from under this session twice in one afternoon.** `learning/` and `merchant_registry.py` are yours alone; `matching/` is MATCHING's, `intake_mail.py` is TRACEABILITY's: do not edit them, add a local helper instead.
- Live reads only. API `https://brisken-expense-recon.fly.dev` (also `api.expenses.brisken.com`): `POST /api/login {"code": ...}` with `EXPENSE_RECON_OPERATOR_CODE` from `workspace/clients/brisken/context/.env` (never print it). Months: July `50622baec444`, August `074a7b8905d7`, September `51a22ad72864`; list `GET /api/expense-batches` (key `batch_id`). Never fetch `GET /runs/{id}/expense-report.pdf` live. No writes to Criss's months; any live write goes through `AskUserQuestion` as a decision with a recommendation and the diff shown, never "say the word". Windows Python cannot open `/c/...` paths: pass `C:\...`.
- **Read a payload's field names before trusting one.** `GET /api/memory` `categories[]` names the company `entity`; the write endpoint calls the same value `legal_entity_id`, and reading the write name off a read row returns None on all 103 rows. Print one row's keys rather than assuming.
- Build: route-level tests through the FastAPI app, at least one through the CALLER the fix changed; one `uv run tools/regress_check.py --test "<cmd>" --cwd <module dir> --file <src> --replace "<wired>" --with "<disabled>"` per fix, watched going red. On a doubtful "RED (no pytest summary line)" mutate by hand with a `cp` backup and read the real pytest output; restore with `cp`, never `git checkout --`. Suite: `uv run --directory workspace/clients/brisken/automations/expense-reconciliation --extra web --extra dev pytest -q` (about 5-6 minutes, 2,601 tests at the M2 merge; run it in the background with `tools/bg_watch.py` registered). Ruff: `uv run --no-project --with ruff ruff check src tests` from the module dir (clean today). Heredocs with triple quotes are blocked: write scripts with the Write tool. Document every new field in `docs/api-contract.md` and pin every new list field in `tests/test_view_contract.py` in the same PR. The accuracy gate must stay green.
- Ship: commit with explicit pathspecs, push, `gh pr create --repo 011matthias/agentic-ops1.01` (suite count before and after plus the regress line in the body), wait for CI (`gh pr checks <n> --json name,bucket` in a background loop), `gh pr merge --squash --delete-branch` on green. Backlog move to Shipped and the status file in the same PR.
- Deploy (pre-authorized, one Fly app shared with the siblings): after the merge, probe the live API for YOUR field first; a sibling's deploy may already carry your commit (`flyctl releases -a brisken-expense-recon`). If absent and no release is in progress: `git -C C:\Users\neuma_p1qrsic\Repo\agentic-ops1 worktree add --detach C:\Users\neuma_p1qrsic\Repo\agentic-ops1-deploy-memory origin/main`, confirm your merge is in `git log -1` there, `flyctl deploy . -a brisken-expense-recon --remote-only` from the module directory, remove that worktree. Then a live API probe and a cold browser read-back. **When your field is absent by design until data exists, the honest verification is a before/after diff of the live behaviour it could have changed** — that is what M2 did (card resolution on three months byte-identical pre and post deploy).
- Cold browser drives: headless Playwright with `channel="chrome"` (`uv run --no-project --with playwright python <script>`). Sign-in: `input#code`, **wait ~4s after the selector appears before filling** (the handler attaches late; filling immediately makes Enter a no-op and the drive times out), then Enter, then wait for localStorage `erc-token`. The month route is `/expenses/{batch_id}`, NOT `/month/{batch_id}` (that renders 0 rows). Record every non-GET request and assert only the login. Or `agent-browser --session recon-memory` (never the default session). The deploy-consumer gate recognizes Playwright MCP and agent-browser only; a scripted drive must be named as such in the closing text.
- SPA work (M4's `profile` editor and display): write `docs/lovable-<slug>-prompt.md` (background, exact JSON shapes, render rule, EN + PT-BR strings, the whole-map-replace warning, do-not-change list, checks), add a Not-applied row to `docs/PROMPT-STATUS.md`, and hand the whole prompt in the reply inside a FOUR-backtick fence under the label **"Paste into Lovable:"**. Label every fence: "Paste into Lovable:" or "Continuation prompt for Claude Code:".
- Checkpoint branches: `docs/checkpoint-memory-<n>` in `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-memory`, cut off origin/main at checkpoint time; `checkpoint_scaffold.py` takes `--root` BEFORE the subcommand (`... --root <wt> finalize --payload ...`), and it numbers the prose file itself, so write the file only after `finalize` names it. Run `uv run tools/repair-session-log.py docs/sessions/<date>.md --check` before pushing (three sessions write the same log). Remove only the worktrees and branches YOU created; print `git worktree list` and `gh pr list --state open --search memory` at every stop.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-19 `--status` read a sibling's 212k while this session sat at 366k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); M2 (backend + learner + 10 tests + three regress proofs + deploy + cold drive) cost about 196k on 2026-09-19; a matcher item with before/after measurement cost about 225k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `--root <that worktree>` before the `finalize` subcommand; write the checkpoint prose after `finalize` names the file; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
