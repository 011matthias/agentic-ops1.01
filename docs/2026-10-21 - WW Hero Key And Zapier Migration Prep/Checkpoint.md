# Checkpoint: WW Hero Key And Zapier Migration Prep

**Date:** 2026-10-21 (work done 2026-10-07 to 2026-10-09)
**Status:** Read-only catch-up done; no WW build started. Zapier migration waits on JSON exports and the owner's Zap list.

---

## Summary
Caught Matthias up on Tobias and Sabine's last ask (Nico's Oct 6 handover, issue #55, the final-push docs), stored his own Hero key and the shared PM n8n login, and answered how to hand over Wärme Wimmer's Zapier for the next migrations.

---

## What Was Done This Session

### Catch-up on the Tobias/Sabine ask
1. Read Nico's handover mail (iCloud INBOX 2950), the four issue #55 notifications, and the agentic-ops handover docs plus `docs/2026-10-06 - WW Tobias Sabine Final Push/`.
2. The ask: a real walkthrough on a Hero test project next to Tobias's drawing (`Projekte Automatisierung.pdf`), then self-testing. The HTML demos do not count. The 2026-10-07 17:00 Berlin replacement call happened and Matthias had to say he could not deliver it (owner statement).
3. Verified read-only: both fixtures unchanged (Max HUK-106488 / 12189064, Biene HUK-106489 / 12189161, type 72627, step 847254); type 72627 still has Hero's 13 default steps; W2-14 filters only type 13293 and fixture 11313747; W2-02/05/06/09 carry no type filter (a step change on a test project can trigger them).
4. Mapped Tobias's drawing against what exists: R1-R3 (Erstgespräch) and R4 (Angebot follow-up) exist in W2-14 for the old type in test mode (mails go to Nico); the rest of the drawing is unbuilt.

### Access and secrets
1. Owner's Hero key stored in the gitignored `agentic-ops/.env` as `HERO_API_KEY_MATTHIAS_WARME_WIMMER`; read-verified HTTP 200 through `tools/ww-hero-read-guard.mjs`. It differs from `HERO_API_TOKEN_ASSISTENT_WARME_WIMMER` (the production writer token).
2. Shared PM login (pm@waerme-wimmer.de, https://n8n.osneo.de/) added to the local vault as "n8n PM Wärme Wimmer", tab Wärme Wimmer. Password was transcribed from a screenshot; not yet test-logged-in. Proton Pass link valid until 2026-11-06.
3. Memory `project_warme_wimmer_takeover` updated with the Hero key location.

### Zapier migration prep
Told the owner the route: export each Zap as JSON (owner-only, or copy the Zap and export the copy), name the Zaps, then one n8n workflow per Zap, created inactive. Switching the Zap off and repointing triggers stays with owner and Raphael.

---

## Key Decisions Made

### No W2-15 build yet
- **Choice:** Owner declined the proposed test-only workflow ("i need to understand it first"). Nothing built or changed.
- **Rationale:** The owner wants the process understood before committing to a design.

---

## What Did NOT Work (and why)
- **Reading the Zaps through the Zapier connector:** it exposes app actions only and is bound to Raphael's account; Find Zap returns metadata, not definitions (see `reference_zapier_mcp_no_zap_definitions`).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| agentic-ops `.env` (gitignored) | Edited | Added `HERO_API_KEY_MATTHIAS_WARME_WIMMER` |
| `C:\Users\neuma_p1qrsic\.passwords.json`, `.passwords.tabs.json` | Edited | Vault entry "n8n PM Wärme Wimmer" |
| memory `project_warme_wimmer_takeover.md` | Edited | Hero key location |

---

## Current Status
No WW workflow touched. W1-06 stays live from the 2026-10-07 session. Ops status: warme-wimmer has no infrastructure.yaml in this repo (its home is the agentic-ops clone).

---

## Next Steps
1. Owner sends the Zap list and JSON exports; migrate one Zap at a time (own branch, PR, infra entry, test), per `feedback_one_automation_one_unit`.
2. Test-log-in to n8n.osneo.de with the vault entry; fix the password from Proton Pass if a character was misread, before 2026-11-06.
3. Before any Hero test: confirm with Tobias which default step matches which stage, and check W2-02/05/06/09 against the test projects.
4. Open from the 2026-10-07 session: merge akkton/agentic-ops PR #304 on owner order, Jotform entries 13:18-14:02 UTC gap, error alerts still go to Nico.

---

## Context for Next Session

### Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\workspace\clients\warme-wimmer\specs\1-spec\a5-vertriebsprozess.md`
- `C:\Users\neuma_p1qrsic\WW-handover-2026-10-06\private\originals\23-Projekte Automatisierung.pdf`

### Open Questions
- Which Zaps does the owner want migrated, and are they still firing (run history needs Zapier login in Chrome)?

### Working Notes
- Hero read helper: `tools/ww-hero-read-guard.mjs` (6 s spacing, skip first 90 s of each quarter hour, stop on 429); `ww-hero-lesen.mjs` still uses the assistant token only.
- Step-list query: `project_types { id name project_status_steps { id name status_code sort_order is_active is_archiving } }`.

### Reference Materials
- iCloud INBOX 2950 (Nico handover), https://github.com/akkton/unpauseai-web/issues/55

---

## How to Continue
Work in the agentic-ops clone, not agentic-ops1. Read `project_warme_wimmer_takeover` and the Zapier memory first.

---

## Strategic Feedback

### What Worked Well This Session
- Answering the "what did they ask for" question from three independent sources (mail, issue, live Hero/n8n reads) before proposing a build; the owner then chose to understand first.

### Suggestions
- Add a small `tools/ww-hero-steps.mjs` wrapper so the step-list read is not rebuilt from a scratch script each session.

### System Health
- Autonomy score: 3 human interventions (Hero key, vault request, Zapier question), none a blocker.
