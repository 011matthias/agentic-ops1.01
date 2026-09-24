# Checkpoint: Brisken P2 Dormant Workstreams Brought To Live State

**Date:** 2026-09-24
**Status:** Open items worked; two need people outside this session (Zoho UI rename, Dirk's Overview answer)

---

## Summary
The two stale p2 status files (product decks at 63 days, targeting at 64) were rebuilt from live SharePoint and mailbox reads, and both workstreams are now marked dormant. Dirk's 07-22 request to file the Nestle StratiFy list was carried out with an owner yes. The Zoho rename he asked for in the same reply is blocked, because the CRM token is read-only.

---

## What Was Done This Session
### Product decks (PR #1301)
1. Graph listing of `MARKETING/.../2026_PPTX`:
   - Dirk owns the Overview now: `Dirk - ...2026-07-27.pptx` (07-29), `...Overview-Classic_2026.pptx` (08-27), `...Overview GOLDEN COPY.pptx` (08-31). He marked our 07-21 NEW deck "(Outdated)" and archived `...Overview 2026.pptx` on 08-01.
   - Product Assets unchanged since 07-14: no NEW product deck was ever swapped in.
   - Nothing of ours in Asset Testing touched since 07-27.
2. Status file rewritten as current state only; July history stays in `deliverables/*/CHANGELOG.md` and git. The memory `project_brisken_product_decks_restructured` is updated, along with its index line.

### Targeting (PRs #1301, #1303)
3. Dirk's 07-22 reply, found in Matthias's inbox: "maybe not a high value activity right now". He asked for the list to be filed under the SharePoint lists, for "Ortega" to become "Dorta" in Zoho, and to move on.
4. **Filed** (owner yes, per-action): `MARKETING/60_Campaigns/05 - Lists/NESTLE STRATIFY LIST 2026-07/` holds the exact xlsx from the 07-22 Sent Items attachment, plus a README. Readiness was checked first (parent readable with 31 children, target folder absent). Downloaded back and cell-identical on all 3 tabs (59/216/20 rows); SharePoint's metadata explains 37,747 vs 28,571 bytes.
5. **Zoho rename blocked:** the contact is still "Daniel Ortega", id 1343217000029348091, with no account linked, and there is no "Dorta". The token scope is `contacts.READ accounts.READ` only.

### Duplicates follow-up
6. September read via the API: 19 copies set aside (USD 1,882.21), 38 marked rows. Criss has not acted yet.

### System
7. Pattern rule `warn-merge-chained-after-checks-watch`, tested: it matches the chained command and not a bare merge.

---

## Key Decisions Made
### Both p2 files marked dormant, not deleted
- **Choice:** `state: dormant`, rows kept, with the live facts on top.
- **Rationale:** Both still hold live questions for Dirk (canonical Overview, per-deck pick), and W1 §4 deletion is for shipped or abandoned work, which neither is.

---

## What Did NOT Work (and why)
- **`gh pr checks --watch` and `gh pr merge` chained in one Bash call (3x):** no-auto-commit-gate evaluates CI at PreToolUse, before the watch runs, sees pending, and forces a permission prompt. Now a pattern rule.
- **Zoho rename via API:** the Self-Client token has READ scopes only (`ZohoCRM.modules.contacts.READ`).

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/status/p2-product-decks.md` | rewrite | Live state, dormant |
| `workspace/clients/brisken/status/p2-targeting.md` | edit | Dormant, Nestle row resolved |
| `.claude/patterns/warn-merge-chained-after-checks-watch.md` | create | Avoid pending-CI merge prompts |
| memory `project_brisken_product_decks_restructured.md` + `MEMORY.md` | edit | Current deck state |

---

## Current Status
Every Brisken status file is fresh (`project_status.py --check` OK). SharePoint now holds the Nestle list folder. brisken ops: unknown plan, not assessed.

---

## Next Steps
1. Matthias: rename the Zoho contact Ortega to Dorta in the UI and link it to the Nestlé account (the API token is read-only; Dirk also flagged Matthias's CRM access as needing a fix).
2. Ask Dirk whether `...Overview GOLDEN COPY.pptx` is the canonical Overview, before any deck work restarts.
3. When Criss starts deleting September copies, read the month back.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p2-product-decks.md`, `p2-targeting.md`

### Open Questions
- Is GOLDEN COPY canonical, and should the four product decks follow it?

### Working Notes
Graph search on the MARKETING drive works for locating folders, but results carry no path; resolve it with `GET /drives/{d}/items/{id}?$select=parentReference`. Dirk's lists home is `60_Campaigns/05 - Lists`.

### Reference Materials
- PRs #1301, #1303

---

## How to Continue
Items 1 and 2 above sit with people; nothing is queued for an agent.

---

## Strategic Feedback

### What Worked Well This Session
- Treating "stale status file" as a question about the live systems rather than the file. Reading SharePoint and the mailbox turned up Dirk's GOLDEN COPY and his forgotten 07-22 instruction, neither of which any file recorded.

### Suggestions
- The Brisken Zoho CRM token is read-only. If CRM hygiene tasks keep arriving from Dirk, a scoped `contacts.UPDATE` grant (owner decision) would let them run through the existing invasive-action gate instead of routing to the UI.

### System Health
- Autonomy: 1 intervention, the owner's yes on the two writes, which is the correct gate. The 3 merge prompts were self-inflicted and are now covered by a pattern rule.
