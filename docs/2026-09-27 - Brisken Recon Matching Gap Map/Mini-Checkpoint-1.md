# Mini-Checkpoint: Brisken Recon Matching Gap Map

**Date:** 2026-09-27
**Status:** Map delivered; five-front parallel build round handed to fresh sessions (fronts 1 and 2 already shipped per sibling updates)
**Type:** mini

---

## Summary
Answered the owner's two questions on the Brisken expense-recon tool with measurement, not argument: (1) the category chain and the card/company chain already meet on the company and the only reverse cross-fill is about six private-card receipts a quarter, suggestion-grade (owner: leave it); (2) a 23-agent workflow read every matching front, a skeptic per front recounted each claim against `origin/main` and the live July-September payloads, a critic named the fronts nobody covered, and the result went to the owner in plain language, then as five continuation prompts for a simultaneous build round.

## What Was Done
- Measured category x company/card on the live months (`.scratch/recon-score-2026-09-25/` payloads + `context/expense-reconciliation/account-map-260925.json`): the 55 refused receipts and 164 charge guesses all HAVE a company; charges never lack one (258 card / 50 batch); Criss books 621 of 650 merchants in one company, so vendor history could name the company on 17 of 33 no-company receipts, but 24 of those wait for a statement that names it anyway. Recorded in `project_brisken_recon_categorization_analysis.md`.
- Workflow `wf_435f1d98-ae0` (23 agents, 0 errors, 6.0M subagent tokens, 29 min): 11 fronts read, 11 verified, 1 critic. Condensed, verified map saved to `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\.scratch\recon-matching-gaps-2026-09-25.md` (1,298 lines; per gap: plain text, file:line, live count, status, verifier note). Roughly a third of the reader claims were corrected by the verifier (counts, line numbers, a refuted "mojibake" claim, several by_design claims that were unbuilt recommendations), so the map, not the raw workflow result, is the reference.
- Plain-language summary delivered (three structural facts: missing statements, nothing learns, stamped-once-never-re-read; per front 3-6 lines; four missing fronts; five gaps ranked by volume).
- Five prompts (one per ranked front) written under `docs/PARALLEL-ROUND-PROTOCOL.md`, each with the verified counts, a bounded build list, the instrument, the do-not-build list, the owner decisions as `AskUserQuestion` items, and the SESSION LOOP verbatim. Condensed copy in `Front-Prompts.md` beside this file.
- Memory `project_brisken_recon_gap_map_2026_09_25.md` created and indexed; sibling sessions have since appended front 1 / front 2 results to it (item 220 #1466, item 221 #1468 Fly `f92a2f87`, 22 already-booked verdicts written on an owner yes).

## What Did NOT Work (and why)
- **Crude alias matcher for "company contradicts vendor history":** last-writer-wins over registry aliases and raw label compare flagged 14 rows, all artefacts (`Brisken Corp Services, LLC` vs `Corporate Services`, `Brisken GmbH` absent from the map, `amazon` catching AWS). Real contradictions after cleanup: ~0. Resolve labels through the module's own identity + entity alias map before counting.
- **Parsing the workflow output by slicing from `{"fronts"`:** the task output file is a wrapper `{summary, agentCount, logs, result}`; the slice hit a `"fronts"` inside a nested string. `json.load` the whole file and take `["result"]`.
- **Reading the 273 KB condensed map with one `Read`:** exceeds the 25k-token cap (58k); 220-line chunks (about 18k tokens each) worked.

## Current Status
Brisken platform: unknown plan (no `platform` section for p1; FastAPI on Fly). Map and payloads sit in the main clone's gitignored `.scratch/`; the five fronts run in their own worktrees (`agentic-ops1-front{1..5}`, branches `client/brisken/p1-front{N}-{slug}`), each ending in its own PR, deploy and mini-checkpoint. Nothing from this session touched the module, the backlog or the status file; the register archive (3 resolved rows older than 2026-09-13) ships in this docs PR.

## Next Steps
1. When all five fronts have merged: re-run `tools/recon-categorization-score.py --fetch --pull-zoho` and `tools/recon-match-attribution.py` on July + August, and re-read the map's per-front counts against fresh payloads; mark each gap closed / moved / unchanged in a follow-up map rather than re-deriving it.
2. Fronts the round does not cover, in the order the map ranks them: the FX daily-rate backfill that recorded itself done at 48 days (`web/fx_daily_rates.py:272-274`, July 14 of 31 pairs on the monthly average); refunds paired to the purchase they reverse (0 live, advisory); trips / cost centres (owner data); the company printed on the invoice never read.
3. Owner-held and out of every prompt: the September 2838-family and 0113 statements (one upload moves seven fronts); Dirk's accounts for Lovable and Consulting and the split vendors; the Lovable registry write ("do not re-ask"); holder addresses + the first chase send (item 107); Criss deletes the Redis reminder (D3); the unpasted Lovable prompts on `PROMPT-STATUS.md` plus the five the fronts will add.

## Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\.scratch\recon-matching-gaps-2026-09-25.md` (the map; CRITIC block at the end)
- `docs/2026-09-27 - Brisken Recon Matching Gap Map/Front-Prompts.md` (what each front was told to build and to ask)
- memory `project_brisken_recon_gap_map_2026_09_25.md` (sibling updates land there)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 220+ (the fronts' own records)
