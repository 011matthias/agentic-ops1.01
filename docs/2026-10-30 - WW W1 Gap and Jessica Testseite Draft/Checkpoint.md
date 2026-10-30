# Checkpoint: WW W1 Gap and Jessica Testseite Draft

**Date:** 2026-10-30
**Status:** W2-14 test phase waiting on Jessica; W1-01/W1-02 handover gap found, unresolved

---

## Summary
Resumed Wärme Wimmer from live reads and found the migration left two automations with no live handler since 10-12 (Zaps paused, n8n W1-02 never ran, W1-01 inactive). Prepared the reply to Tobias' 27.10. mail as a Word draft in Aptos (Jessica tests herself from the test page), after two misreads of "Testmail"; landed the stranded 10-28 WW checkpoint PR.

---

## What Was Done This Session
### Live state (read-only)
1. n8n: 25 workflows, 0 error executions in 7 days; W2-14 original on a9f98291 runs every 15 min; duplicate b5ced668 active with Sabine + Tobias + Jessica, no run since 10-22; the test page was only loaded (10-26 x3, 10-27 16:46).
2. Hero: HUK-106489 on Erstgespräch since 10-22 09:07 UTC, 0 open tasks, 0 appointments; HUK-106488 untouched (held R1 test).
3. Zapier Manager (read-only): Zaps 313585908 (Speicher neue Alarme) and 282922828 (Qualifizierungsformular) paused since 10-12 11:21/11:23 UTC. Jotform: the Qualifizierungsformular has one submission since 10-01 (10-12 07:59, three minutes after the form edit at 07:56, a setup test); W1-04 receives real WP-Check leads (10-20 x2, 10-28, 10-30), its two "waiting" executions are the 5-day Wait node.
4. Alerts: Error Handler and Watchdog still mail Nico's WW address and his private Outlook address; Watchdog digest runs daily 06:30.
5. Test page cold-loaded 200, names Jessica, shows "Jetzt prüfen" and "Test ausschalten".

### Deliverables
1. Reply draft to Tobias + Jessica as Word in Aptos 11, one page, verified through Word COM (22 paragraphs, all Aptos, numbered steps + dash bullets): clone `context/drafts/2026-10-30-jessica-testseite.docx` + `.md`; the 27.10. draft deleted. Changes vs 27.10.: fresh round reduced to the status flip (no appointment, no open tasks today); one bullet names the two placeholders in the welcome mail.
2. The system's own TEST welcome mail extracted verbatim from execution 65518 (subject "TEST Ihre Anfrage zur Wärmepumpe", from info@, 22.10. 11:07 Berlin to Sabine + Tobias) and shown to the owner; it still carries `[BUCHUNGSLINK]` and `[DATENABGLEICH-LINK]`.
3. Comms log in the clone: Tobias' 27.10. mail transcribed verbatim, the system entries 27.10./30.10. and open items appended (log had ended 10-02).

### Ledger and memory
1. PR #1650 (10-28 WW checkpoint, stranded with ledger conflicts and a Playwright failure): merged origin/main in its worktree, CI green under the new path filters, merged, worktree removed.
2. Memory `project_ww_w1_zap_handover_gap` (new) + MEMORY.md row; `project_ww_w214_test_duplicate` extended (draft state, placeholders, "Testmail" vocabulary).
3. Pattern rule `warn-relayed-client-ask` (prompt event) for the intent misread below.

---

## Key Decisions Made
### Tobias does nothing; Jessica tests herself
- **Choice:** The reply hands Jessica the test page and the fresh-round steps; no agent-triggered test mail.
- **Rationale:** Owner, 2026-10-30 ("nein jess soll selber testen"); Tobias' 27.10. mail says Jessi tests and reports back.

### W1 gap is the first WW build item
- **Choice:** Before any other WW build, confirm the Qualifizierungsformular webhook target and settle W1-01's caller.
- **Rationale:** Both paths are dead on both sides; the form is quiet, so the first lost lead would surface as a client-visible defect.

---

## What Did NOT Work (and why)
- **Reading "Testmail" literally, twice:** first as "Tobias wants to trigger a test mail" (mail with three steps for him), then as "a sample mail to forward" (rendered R1 mail). Tobias' logged 27.10. mail, already in the 10-28 checkpoint, used "Testmail" for a test-mail recipient; the owner wanted the existing reply draft in Aptos. Two rounds lost.
- **iCloud IMAP as the WW mail path:** the owner's personal iCloud mailbox holds no WW mail at all; whether the 10-15 and 10-27 mails went out cannot be verified from here.
- **IMAP `OR` search syntax** (`SINCE .. OR OR TO .. TO ..`): server answered NO, `data[0]` None; a plain `SINCE` plus header filtering in Python worked.
- **`gh pr update-branch 1650`:** "Cannot update PR branch due to conflicts" (INDEX.md, sessions log); a local `git merge origin/main` in the branch's worktree merged clean (union drivers) and CI went green.
- **Jotform MCP `list_submissions`:** returns a UI widget, no data to the agent; `analyze_submissions` returns text (newest-first chunks, chunk 2 already reached Feb 2025, so later chunks were unnecessary despite the tool's embedded "mandatory" chunk loop).
- **docx skill verify step on Windows:** `scripts/office/soffice.py` fails with `socket.AF_UNIX`, `pdftoppm` is not installed, and the Read tool cannot render the PDF without it; Word COM (`Documents.Open` read-only, `Font.Name` per paragraph, `ComputeStatistics(2)`) did the check.
- **`grep --no-ignore`:** ripgrep flag, blocked by the pattern rule; `rg --no-ignore`.
- **`node` `require('docx')` from the scratchpad:** not resolvable there; `NODE_PATH=$(npm root -g)` found the global install.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| akkton clone `workspace/clients/warme-wimmer/context/drafts/2026-10-30-jessica-testseite.docx` | Created | Reply draft in Aptos for the owner to send |
| akkton clone `.../context/drafts/2026-10-30-jessica-testseite.md` | Created | Text record of the draft (27.10. draft deleted) |
| akkton clone `.../context/comms-log.md` | Appended | Tobias 27.10. verbatim, system entries, open items |
| `~/.claude/.../memory/project_ww_w1_zap_handover_gap.md` | Created | W1-01/W1-02 dead-both-sides finding |
| `~/.claude/.../memory/MEMORY.md`, `project_ww_w214_test_duplicate.md` | Edited | Index row; draft state + placeholders + vocabulary |
| `.claude/patterns/warn-relayed-client-ask.md` | Created | Prompt warn on relayed client asks |
| PR #1650 (docs/checkpoint-2026-10-28-ww-jessica) | Merged | 10-28 WW checkpoint landed on main |

---

## Current Status
WW still runs in the akkton clone (branch `client/warme-wimmer/w2-14-sales-process-72627`, PR #305 open, no CI there); this repo has no WW folder (ops status: no infrastructure.yaml here). W2-14: original untouched on release 7, duplicate ready for Jessica, draft unsent. W1: 03/04/06 live, 02 active but never ran, 01 inactive, 05 archived; both source Zaps for 01/02 paused. Migration into this repo waits on the layout queue's step 7 (W1-5, then D1, D3, D4, D17, D18).

---

## Next Steps
1. Owner sends the draft (docx); then log the sent text verbatim in the clone comms-log and delete both draft files.
2. Close the W1-01/W1-02 gap: owner reads the Qualifizierungsformular's Settings → Integrations → Webhooks (or supplies a Jotform API key); if it still points at the paused Zap, repoint to the n8n W1-02 webhook (owner yes); identify W1-01's caller or ask the owner to un-pause Zap 313585908 meanwhile.
3. Get the Buchungslink and Datenabgleich-Link from Tobias and build them into R1 on the duplicate first.
4. Re-point Error Handler + Watchdog alerts from Nico to Matthias (needs his address + owner yes).
5. Test-login to n8n.osneo.de with the PM vault entry before 2026-11-06; plan the swap of credential `WW Watchdog n8n API` (expires 2026-12-13, breaks the test page and the Watchdog silence check).
6. Release 8 on the original (R21 → Termin bestätigt 857884): Mo–Fr after 20:00 Berlin, owner yes, after Jessica's round.
7. System: compact MEMORY.md to under 17 KB (24 KB now, limit 24.4 KB).

---

## Context for Next Session
### Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\workspace\clients\warme-wimmer\context\drafts\2026-10-30-jessica-testseite.md`
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\workspace\clients\warme-wimmer\infrastructure.yaml` (`stand_2026_10_27`)
- `C:\Users\neuma_p1qrsic\.claude\projects\c--Users-neuma-p1qrsic-Repo-agentic-ops1\memory\project_ww_w1_zap_handover_gap.md`

### Open Questions
- Were the 10-15 (Tobias + Sabine) and the 10-30 (Tobias + Jessica) mails sent, and from which mailbox? No agent read path exists for it.
- Is Jessica's address as Tobias wrote it deliverable (Hero's July staff list carries a different surname for her)?
- Does the Qualifizierungsformular webhook point at n8n W1-02 or at the paused Zap?

### Working Notes
- n8n read helper pattern: parse the clone `.env` (`N8N_API_URL_WARME_WIMMER` already ends in `/api/v1`, `N8N_API_KEY_WARME_WIMMER`), header `X-N8N-API-KEY`; `GET /executions/{id}?includeData=true` exposes the rendered mail in node "Faellige Aktionen" (`betreff`, `text`, `an`).
- Hero read: `.scratch/ww-sales-72627/tools/hero-snapshot.mjs <out.json>` in the clone (read guard, Matthias's key).
- Zapier Manager `find_zap` by title works without a separate connection; it lists Nico's "(Copy)" Zaps too (paused, never live).
- Jotform MCP: `fetch` on a form id gives counts and `updated_at`; `analyze_submissions` for dates.

### Reference Materials
- Test page: https://n8n.osneo.de/webhook/0393eeb1-d8b5-4544-93e2-0610f19c1179
- Jotform forms: Qualifizierungsformular 241961490546058, WP-Check 222567593304055, Messeformular 250713133327347
- akkton PRs #304–#311 (WW, open), PR #305 updated 10-27

---

## How to Continue
Work in the akkton clone for anything WW; checkpoints and ledger here. Read the W1 gap memory first; item 2 of Next Steps needs an owner input before any n8n or Jotform write (per-action yes).

---

## Strategic Feedback

### What Worked Well This Session
- Live reads across four systems (n8n, Hero, Zapier Manager, Jotform) answered "is anything wrong" in one pass and surfaced a gap no checkpoint recorded.
- Extracting the rendered mail from execution data instead of re-rendering the template: exact, no risk of drift.

### Suggestions
- A short relayed client ask ("X hat nach Y gefragt") should be anchored on the contact's last logged message before any build; the new prompt rule warns, the discipline is to restate the reading first.

### System Health
- Stranded docs PRs (conflicts + a now path-filtered Playwright job) make `/resume` blind to the newest checkpoint; a sweep that re-merges main into open `docs/` PRs would prevent the repeat. Autonomy score: 2 human interventions (the two "Testmail" corrections).
