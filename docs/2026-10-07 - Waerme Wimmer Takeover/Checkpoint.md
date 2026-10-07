# Checkpoint: Waerme Wimmer Takeover

**Date:** 2026-10-07
**Status:** Handover ingested and access set up. The Raphael onboarding (announced 14:00 Berlin) and the Tobias/Sabine replacement demo (17:00 Berlin) had not happened yet when this was written, so their outcome is unrecorded.

---

## Summary
Nico handed the Wärme Wimmer (WW) client to Matthias on 2026-10-06: contract, operations and customer coordination. This session read the handover mails, pulled every handover package, set up the akkton/agentic-ops clone with its private context and credentials, briefed Matthias for both meetings, stored the shared n8n login, installed his own n8n API key, and wrote a prompt for rebuilding the Zapier "Messeformular" in n8n.

---

## What Was Done This Session

### Handover intake (read-only)
1. Searched iCloud IMAP and found:
   - Nico's handover mail (INBOX 2950) and the admin@ forward of it (2953)
   - four GitHub notifications on `akkton/unpauseai-web` issue #55 (2946-2949)
2. Found two draft releases on `akkton/unpauseai-web`:
   - `ww-private-handover-2026-10-06`: 5 assets, including the private context and credential archives
   - `ww-final-push-2026-10-07`: today's meeting runbook plus the evidence of the held R1 test
3. Downloaded all of it to `C:\Users\neuma_p1qrsic\WW-handover-2026-10-06\`. All four ZIPs passed CRC. Opened today's `final-push-2026-10-07\start.html` in Edge.

### Repo and access setup
1. With the owner's yes via AskUserQuestion, accepted GitHub invitation 336453532 (write on `akkton/agentic-ops`). Verified via `gh api` (push=true).
2. Cloned it to `C:\Users\neuma_p1qrsic\Repo\agentic-ops`. Placed the gitignored files following the archive README, never overwriting an existing file:
   - `workspace/clients/warme-wimmer/context/` (582 files)
   - `.env` (14 WW keys)
   - `.mcp.json` (server `n8n-warme-wimmer`)
   - incident `.scratch/`

   `git status` stayed clean. The archive's `infrastructure.yaml` was NOT copied because the tracked one (commit 087435f) is newer.
3. Read-only check of the n8n API: HTTP 200, 17 workflows (15 active).
4. Vault: added entry `n8n Wärme Wimmer` (shared UI user `n8n@waerme-wimmer.de`) under a new tab "Wärme Wimmer". The password was transcribed from Matthias's Keeper screenshot and verified by one `POST /rest/login` (200). No API key in the vault, by the owner's choice.
5. The owner then gave the agent its own n8n API key (same n8n user, issued 2026-10-07 12:41 UTC, no exp). Differential probe: new key 200/17, old key 200/17, tampered key 401. It replaced Nico's key in the clone's `.env` and `.mcp.json`.

### Briefing for Matthias (chat only)
- Plain-language explanation of WW, the systems (Hero, Outlook, n8n), the two workstreams (Sabine's mail/task operation, Tobias's new heat-pump sales process), yesterday's failed demo and the held R1 test.
- From the meeting history and access inventory: the trust arc since April, the third workstream (Osneo Slack/Sentry/Jira flows inherited from Irina), the missing human logins (Hero, n8n UI before the Keeper link, M365, Teams, WhatsApp, Linear), and the open contract/billing question.
- A pasteable prompt for another chat (with Zapier connected) to rebuild Zap "Messeformular" (W1-06) as a NEW, INACTIVE n8n workflow, with hard limits: no sends, no Zap or Jotform changes, no PUT on existing workflows.

---

## Key Decisions Made

### Where WW work lives
- **Choice:** WW work runs in the `akkton/agentic-ops` clone, not in agentic-ops1. This repo has no warme-wimmer client folder.
- **Rationale:** Nico's specs, tools, automations and `infrastructure.yaml` all live there. Recorded in memory `project_warme_wimmer_takeover.md`.

### Agent n8n key replaces Nico's locally only
- **Choice:** Matthias's key replaced Nico's in `.env` and `.mcp.json`. The n8n credential `WW Watchdog n8n API` was not touched.
- **Rationale:** Changing a credential in the live tenant is a production write that needs an explicit go. Nico's key keeps the Watchdog running until it expires on 2026-12-13.

---

## What Did NOT Work (and why)
- **`grep -rli --no-ignore "messe"`:** `--no-ignore` is a ripgrep flag. GNU grep failed, and `2>/dev/null` hid the error, so the first search returned nothing (a false negative). The rerun without the flag found 30+ files, including the Make blueprint `s6-v4-native.json`.
- **n8n API call to `$N8N_API_URL_WARME_WIMMER/api/v1/workflows`:** 404, because the env URL already ends in `/api/v1`. Use `$N8N_API_URL_WARME_WIMMER/workflows`.
- **IMAP `SEARCH TEXT/FROM` with umlauts ("Wärme"):** raised an ascii codec error in imaplib. The ASCII terms (wimmer, Nico) were enough.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `~/.claude/projects/.../memory/project_warme_wimmer_takeover.md` | Created, then updated | Where WW lives, access state, held R1 case |
| `~/.claude/projects/.../memory/MEMORY.md` | Edited | Index line for the above |
| `C:\Users\neuma_p1qrsic\Repo\agentic-ops\` (clone) | Created | Repo plus gitignored `.env`, `.mcp.json`, `context/`, `.scratch/` |
| `C:\Users\neuma_p1qrsic\WW-handover-2026-10-06\` | Created | All handover downloads, extracted |
| `~/.passwords.json`, `~/.passwords.tabs.json` | Edited | Vault entry plus "Wärme Wimmer" tab |
| `docs/2026-10-07 - Waerme Wimmer Takeover/Checkpoint.md` | Created | This file |

---

## Current Status
- **Access:**
  - Matthias has write on `akkton/agentic-ops` and `akkton/unpauseai-web`.
  - Local working clone, the WW n8n API key (his own) and the shared n8n UI login (vault) are all in place.
  - Still missing: a Hero UI login, M365/Teams, the WhatsApp group and Linear.
- **WW live state (read 2026-10-07):**
  - 17 n8n workflows. W2-14 (sales rules) is active but still bound to old Hero type 13293 in test mode, with mail going to Nico.
  - New Hero test type 72627 has test projects HUK-106488 (Max) and HUK-106489 (Sabine).
  - The R1 welcome test (04:58 UTC) has unknown SMTP delivery and zero Hero writes. It is HELD and must not be retried or reset.
- **Ops status:** agentic-ops1 has no infrastructure.yaml or comms-log for WW. Both live in the clone.
- **Messeformular rebuild:** a prompt was handed to a separate chat. Its outcome is unknown here.

---

## Next Steps
1. Record the outcome of the Raphael onboarding and the Tobias/Sabine demo in the clone's `workspace/clients/warme-wimmer/context/comms-log.md`: decisions, owners, the released test scope.
2. Get Matthias his own Hero UI login (Raphael), plus M365/Teams identity, WhatsApp group membership and Linear access.
3. R1 held case: confirm with Raphael and Nico whether the TEST mail arrived. Only then plan a new, explicitly approved test. Never reset the reservation.
4. Decide with Raphael on the 7 unreconciled mails from the W2-04 incident (3x Pia, Ceraflex, Katrin Hutterer, Herr Falke, Frau Speckner).
5. Switch the Error Handler and Watchdog alert recipients from Nico to Matthias, and the `WW Watchdog n8n API` credential to Matthias's key. Both are production writes that need an explicit go.
6. Osneo: replace Nico's personal Jira credential `NDumz8u4GNZ9ZvsT` with a service identity. Confirm the Slack, Sentry and Anthropic owners.
7. Contract and billing transfer from Nico to Matthias (Upwork terms).
8. Review the report and PR from the Messeformular (W1-06) n8n rebuild chat. Activation, the Jotform webhook switch and turning off the Zap all need Raphael.
9. System: compact `MEMORY.md` (21.3 KB, near the 24.4 KB read limit).

---

## Context for Next Session

### Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\docs\handoff\2026-10-06-warme-wimmer-matthias\README.md`
- `C:\Users\neuma_p1qrsic\WW-handover-2026-10-06\final-push-2026-10-07\WW-Tobias-Sabine-review-private\Meeting-runbook.md`
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\workspace\clients\warme-wimmer\infrastructure.yaml`
- memory `project_warme_wimmer_takeover.md`

### Open Questions
- Were 14:00 and 17:00 Berlin the actual meeting times? Nico's "07:00" carried no time zone and no calendar invite was found.
- What exactly is Osneo? From the sources it looks like WW's in-house software development (it is inferred, not confirmed).
- Contract and billing route for Matthias.

### Working Notes
- n8n access in the clone:
  - URL var `N8N_API_URL_WARME_WIMMER=https://n8n.osneo.de/api/v1`
  - key var `N8N_API_KEY_WARME_WIMMER` (Matthias's key, no exp)
  - Osneo/PM instance vars `N8N_API_URL_IRINA` / `N8N_API_KEY_IRINA`
- Hero reads only through `tools/ww-hero-lesen.mjs`, one process at a time, at least 6 s spacing, skipping the first 90 s of each quarter hour, stopping on 429.
- The `ww-graph-*` "read" tools create temporary production workflows, so they are not side-effect-free.
- W1 Zapier automations were rebuilt in Make in April (scenarios 5316508-5316512) but never connected or live. The Messeformular blueprint is `context/blueprints/s6-v4-native.json`, sender sabine.wimmer@, 5 PDFs, 9 heizreport.de POSTs, and a suspicious `<script src='/NPMH/...'>` tag in the Zapier HTML.

### Reference Materials
- https://github.com/akkton/unpauseai-web/issues/55
- Portal: https://unpauseai.com/docs/warme-wimmer/ (code `WIMMER_ACCESS_CODE` in the clone's `.env`)
- Customer recording 2026-10-06: https://notes.wisprflow.ai/shared/BX2ffiaMU4ejEql5zP2bnHk2o-ORd3sP67TNUAq_DMs

---

## How to Continue
Open the session in `C:\Users\neuma_p1qrsic\Repo\agentic-ops` (not agentic-ops1). Ask Matthias how both meetings went, log that first, then work Next Steps 2-8. Every Hero, n8n or mail write in the WW tenant needs a per-action yes.

---

## Strategic Feedback

### What Worked Well This Session
- Taking the read-only half first. Mail, releases and archives were read and placed before anything was asked, so the one real decision (accepting the invite and cloning) went to the owner as a single AskUserQuestion with a recommendation.
- Verifying a transcribed secret by its behaviour: the n8n password was checked with one login before saving, and the new key with a differential probe against a deliberately broken key.

### Suggestions
- `pattern-rule warn-grep-no-ignore`: warn when `grep` is called with `--no-ignore`. It is a ripgrep-only flag, and combined with `2>/dev/null` it produces a silent false negative.

### System Health
- **Ripgrep gotcha:** the memory `feedback_ripgrep_skips_gitignored_context.md` says "use `--no-ignore`". Applying it to GNU grep is the trap. The memory should say the flag is ripgrep-only.
- **Autonomy:** 2 human interventions (invite decision, API-key redirect). Both were owner decisions, not agent deferrals.
