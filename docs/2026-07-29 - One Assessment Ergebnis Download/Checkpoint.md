# Checkpoint: One Assessment Ergebnis Download

**Date:** 2026-07-29
**Status:** Shipped + live-verified (quick tier); notification to Jochen pending user's WhatsApp send

---

## Summary
Built and deployed the downloadable "Ergebnis" for Jochen's One Assessment: a classic-DE PPTX Ergebnispräsentation plus the TCF XLSX Arbeitsmappe, generated natively from the contract (no golden-deck copying), served through a gated portal download card. Live-verified 27/27 on both Nagarro-ES portal copies. Fixed a pre-existing solution-library text corruption first, since it would otherwise bake into every export.

---

## What Was Done This Session

### Format decision (owner, via AskUserQuestion)
1. Second format = **XLSX TCF-Arbeitsmappe** (Jochen's "Abstimmversion" pivot — the non-pptx path to build his own deck). Deck variant = **classic DE encoding** (border/fill = Reifegrad, dot = Priorität inverted), the one he confirmed correct in NR4. PDF rejected (he fine-tunes the artifact; needs editable native formats).

### Solution-library corruption fix (data + miner)
1. Root cause: `_sanitize` matched golden-client names without word boundaries; `"AR "` (case-insensitive) ate the tail of ordinary German words ("klar "→`klstrukturierten`, "zwar "→`zwdie`), and stripped possessives left dangling `von ,` fragments. Shipped into the committed library and thus into rendered results.
2. Fix: word-boundary matching; `AR` case-sensitive standalone only; three grammatical `von <NAME>` cases (hyphen-attributive / attributive-before-capital via `(?-i:)` lookahead / possessive-drop-whole-phrase); line-by-line processing with a dangling-von rule; `_GOLDEN_TYPO_FIXES` for the one glued token (`LiLizenzierung`). 26 field repairs across the library, each cross-checked against the golden originals.
3. New `tests/test_solution_library.py` — includes an artifact-gate test that scans the committed JSON directly.

### Native exporters (contract-driven, zero source-client residue)
1. `export_common.py` (contract loader, Referenzkunde anonymization, mechanical Kernbefunde selector, brand colors from render._TOKENS, AST-sliced contract gate), `export_workbook.py` (contract-exact "Gaps by function" + empty OM roster + hidden Tabelle1 + Agent Review + Offene Fragen), `export_deck.py` (12 slides: Titel/Summary/Heat-Map/Anhang-Tabellen/Nächste Schritte, ENTWURF on every slide), `export_verify.py` (per-tile/cell color asserts, leak scan incl. raw XML, dash scan).
2. `cli export <run_dir>` runs both gates; `publish --artifacts` flag built (unused — PUTs ran raw). The unmodified `validate_contract.py` still PASSes all three goldens.
3. Rescued the deleted 2026-07-13 generators (`render_deck.py`/`render_workbook.py`/`verify_deck.py`) from the session scratchpad into `tools/` as reference before Temp GC.

### Portal download surface
1. `store.py` artifact paths + allowlist; `PUT /api/op/submissions/{id}/result-artifact/{name}` (Bearer, PK-magic, 30 MB, atomic, event); `GET /portal/result/{id}/download/{name}` (same gating as result_view incl. fertig-409, friendly filename); serve-time "Ergebnis zum Mitnehmen" card (never on /demo or showcases). `tests/test_result_artifacts.py` (8 tests).

### Nagarro ES regeneration + deploy
1. `result.json` deterministically re-enriched from the fixed library (11/20 cells, scores/as-is/quotes byte-identical). Artifacts exported through `Nagarro SE/render_result.py` (carries the page's PII scrub; `cli export` on the run dir would regenerate UNSCRUBBED — documented in the script).
2. Deployed site-host to Fly; re-PUT result HTML + both artifacts for both copies (Jochen + Matthias-Ansicht); 6/6 PUTs OK, `mail_skipped` structural (no recipient field). Owner-login e2e: 27/27 live checks (login→card→byte-identical downloads, attachment+nosniff, anon→login, /demo+showcase no card).

---

## Key Decisions Made

### Native generation over template-copy
- **Choice:** Build the deck/workbook from the contract, not by cloning a golden file.
- **Rationale:** Zero source-client residue by construction (the 2026-07-13 approach copied CITTI's actual deck). Reference-client tags render as "Referenzkunde A/B/C".

### Fix the library before exporting
- **Choice:** Repair the sanitizer + committed JSON as step 1, then re-enrich the saved result.
- **Rationale:** The corruption (`klstrukturierten`, `von ,`) lives in the recommendation columns the export renders; exporting first would have shipped it into the client PPTX/XLSX.

### Artifacts come from the run-specific render script, not `cli export`
- **Choice:** For Nagarro ES, generate via `Nagarro SE/render_result.py`.
- **Rationale:** That script applies the PII scrub (employee names in the answers); `cli export` on the raw run dir would produce unscrubbed artifacts. Flagged in-code so the next operator does not bypass it.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `src/treasury_assessment/solution_library.py` | Edit | Word-boundary sanitizer + von-phrase grammar + typo-fix |
| `data/solution-library.json` | Edit | 26 field repairs (corruption removed) |
| `tests/test_solution_library.py` | New | Sanitizer regression + committed-artifact gate |
| `src/treasury_assessment/export_common.py` | New | Contract loader, anonymizer, gate |
| `src/treasury_assessment/export_workbook.py` | New | TCF XLSX generator |
| `src/treasury_assessment/export_deck.py` | New | Classic-DE PPTX generator |
| `src/treasury_assessment/export_verify.py` | New | Behavioral verifier (colors + leaks) |
| `src/treasury_assessment/cli.py` | Edit | `export` command + `publish --artifacts` |
| `tests/test_export.py` | New | Exporter tests (14) |
| `site-host/store.py` | Edit | Result-artifact paths + allowlist |
| `site-host/operator_api.py` | Edit | PUT result-artifact endpoint |
| `site-host/portal.py` | Edit | Gated GET download + card injection |
| `site-host/templates.py` | Edit | `download_card` |
| `tests/test_result_artifacts.py` | New | Portal download tests (8) |
| `Nagarro SE/render_result.py` | Edit | Wire scrubbed export into render |
| `out/2026-07-28-nagarro-es/*` | Regen | result.json re-enriched; pptx/xlsx/html rebuilt |
| `tools/{render_deck,render_workbook,verify_deck}.py` | New | Rescued 2026-07-13 reference generators |
| `DESIGN.md` / `PIPELINE-NOTES.md` (§Y) | Edit | Roadmap rows BUILT + build notes |

*All of Jochen Projekt is gitignored — no commit/PR applies to the above.*

---

## Current Status
Quick-tier Ergebnis download is live on https://one-assessment-demo.fly.dev for both Nagarro-ES submissions (Jochen `20260728-150318-113e4f`, Matthias-Ansicht `20260728-215157-b6e7f9`). 198/198 pytest, `cli verify` green, validate_contract PASS unchanged. No infrastructure.yaml / comms-log for Jochen Projekt (project runs on DESIGN.md + PIPELINE-NOTES.md, not the standard status/ convention). **Jochen has NOT been notified** — notification is a separate per-send-gated step; a du-form WhatsApp draft was handed to the user to send manually.

---

## Next Steps
1. User sends the WhatsApp message to Jochen (drafted in-conversation; du-form, link + "Ergebnis zum Mitnehmen").
2. On Jochen's feedback: iterate deck/workbook; watch for the Reifegrad-Adjudikation return (gates the EN-template 25/50/75/100 variant).
3. Full-tier export: per-Bereich grain (quick tier assesses at Funktion level only).
4. Move the PII scrub from `render_result.py` into pipeline config so `cli export` is safe on real-client run dirs.
5. Register archive deferred: friction-register.md is 415 KB (>200 KB advisory). Run `archive-register` in a dedicated docs PR — NOT on this shared feature branch with live siblings.

---

## Context for Next Session

### Files to Read First
- `memory/project_jochen_treasury_assessment.md` (2026-07-29 Runde 2 entry + comms convention)
- `workspace/clients/Jochen Projekt/automations/treasury-assessment/PIPELINE-NOTES.md` §Y
- `workspace/clients/Jochen Projekt/automations/treasury-assessment/src/treasury_assessment/export_*.py`

### Open Questions
- Nagarro ES formal scope: entity vs group treasury view (ask Jochen).
- Reifegrad band mapping pending REIFEGRAD-ADJUDIKATION (gates EN-template percentage deck).
- Follow-up 23 questions: send as file or hold for workshop?

### Working Notes
- The exporters were built by two parallel subagents (exporters vs portal-surface) against a fixed integration contract (`result-artifact/{name}` PUT + `/download/{name}` GET). It held — no rework at the seam.
- `cli export` regenerates UNSCRUBBED; Nagarro ES artifacts must come from `Nagarro SE/render_result.py`. This is the one footgun.
- Deck is 12 slides (heatmap fits all 20 tiles on one slide; 7 detail slides). ENTWURF not in the XLSX C1 title (locked contract gate checks C1 verbatim) — draft marking lives in the A2 note cell + every deck slide.

### Reference Materials
- Live: https://one-assessment-demo.fly.dev/portal/result/20260728-150318-113e4f
- Contract: `workspace/clients/Jochen Projekt/Reference/tcf-output-contract.json`

---

## How to Continue
The feature is done and live. Next real work is reactive: Jochen's feedback on the two files, then either deck iteration or the Full-tier/EN-template branches (both gated on the adjudication). If regenerating Nagarro artifacts, use `render_result.py`, never `cli export` on the run dir.

---

## Strategic Feedback

### What Worked Well This Session
- Surveying the pipeline via a 3-reader workflow before deciding formats grounded the recommendation in the actual contract + owner statements, not assumptions — the "pptx + working-xlsx" split fell straight out of the evidence.
- Fixing the library corruption before exporting (rather than after a client saw it) — the survey surfaced it as a pending data bug and it was the correct ordering.
- Parallel subagents against a pre-agreed integration contract met cleanly at the seam.

### Suggestions
- The PII-scrub-lives-in-a-run-script pattern is fragile; folding it into pipeline config would remove the `cli export` footgun for good.

### System Health
- Autonomy: 2 human interventions (format-decision ask + comms channel/register correction) — not elevated. B1 stop-gate fired once (end-of-turn deferral on the comms draft) and I corrected same-turn by drafting; the structural gate worked as designed.
