# Checkpoint: Brisken P1 Item 3 Follow-ups

**Date:** 2026-09-24
**Status:** Item 3 and its three owner decisions shipped (code merged, master data live); items 4-6 queued; nothing deployed

---

## Summary
Acted on the owner's three decisions after item 3: fixed the live Corp Services org id, gave `Consulting` its org id on the Fly volume, and merged re-categorization on company assignment (PR #1286).

---

## What Was Done This Session
### Code
1. PR #1281 (`267588dc`): the engine calls `resolve_posting_account` (item 3, detail in Mini-Checkpoint-1 of `2026-09-24 - Brisken P1 Item 3 GL Engine Swap`).
2. PR #1286 (`f6f11dcc`): `web.service.recategorize_after_entity_change`. It runs from both explicit company routes and only when the value changed, off the event loop, before the re-match. It writes the tool's answer into both `receipts` and `extracted_receipts` under the batch lock and leaves reviewer overrides alone. Suite 3260/2; regress_check bites at both route wirings and the snapshot write.
### Live master data (owner-ordered)
1. Settings `Brisken Corp Services, LLC` org_id `8227416528` -> `822741658` via the operator API. Pre-edit snapshot at `.scratch/settings-pre-corp-fix.json`. The re-read diff showed only that entity plus the derived `gl_accounts` changed.
2. `/data/coa-provision.json` gained `"Consulting": {"org_id": "808232536"}` (backup `/data/coa-provision.json.bak-20260924`). Verified with the deployed `coa_validation_from_settings`: all three short names resolve. The local `context/` copy was synced to the live bytes.
### Read-only census
1. Blank-company receipts per live month (snapshot): Jan 1, Apr 11, May 10, Jun 11, Jul 38, Aug 7, Sep 51. All 7 months lack `gl_entity_orgs`.
### Structural fixes (this checkpoint)
1. Pattern rules `warn-chained-checks-watch-and-merge` and `warn-flyctl-console-large-payload`, each tested against the incident command and a benign one.

---

## Key Decisions Made
### Consulting goes in the /data file, not settings
- **Choice:** add the short label `Consulting` to `/data/coa-provision.json`.
- **Rationale:** live receipts carry the short labels the file already uses. A settings entity would add a duplicate company to the picker next to `Brisken Consulting, LLC`.
### Old months are not migrated to GL
- **Choice:** the 7 bucket-era months keep buckets; the first GL month is the first batch created after deploy.
- **Rationale:** standing ruling, no agent writes on Criss's months (`feedback_recon_no_live_writes_criss_acts`). Migrating would also swap the vocabulary under decisions she already made.

---

## What Did NOT Work (and why)
- **Python one-liner with a base64 payload via `flyctl ssh console -C`:** returned nothing and wrote nothing (payload ~2.3 KB).
- **`flyctl ssh sftp put` to `/data/...`:** wrote a 0-byte file on this Windows flyctl.
- **Piping the file into `flyctl ssh console -C "sh -c 'cat > ...'"`:** 0-byte file; stdin bytes are not forwarded.
- **`echo <1964-char base64> | base64 -d` inside `-C`:** silently dropped, no output.
- **What worked:** a short in-place Python edit on the machine to `<file>.new`, verified, then `mv`.
- **First remote write attempt:** blocked by the auto-mode classifier (Remote Shell Writes) until the owner said "you can push it to fly".

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../web/service.py`, `.../web/app.py`, `tests/test_gl_engine.py` | Modified (PR #1286) | re-categorize on company assignment |
| `workspace/clients/brisken/context/coa-provision.json` | Modified (gitignored) | Consulting org id, synced to live |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Modified | owner decisions recorded |
| `.claude/patterns/warn-chained-checks-watch-and-merge.md` | Created | recurrence kill for chained watch+merge |
| `.claude/patterns/warn-flyctl-console-large-payload.md` | Created | recurrence kill for silent flyctl upload failures |

---

## Current Status
Merged on main, not deployed: #1277, #1281, #1286. Live master data is fixed now and doesn't depend on a deploy. The deploy waits on the owner publishing an SPA that reads leaf codes and localizes `category_refused`. Ops status: platform unknown plan (no `platform` assessment in infrastructure.yaml).

---

## Next Steps
1. Item 4: delete `category_accounts.py`, lift `NON_LEAF`/`OUT_OF_SCOPE` into `resolve_account_id`, and rewrite `tests/test_zoho_category_accounts.py`, all in one change.
2. Item 5: kill the three category-leak copies (`posting_common.py:137`, `sheet_writeback.py:143`, `:186`).
3. Item 6: relabel `categorization_gate.py`; validate item 184.
4. The deferred comms-log sweep once items 3-6 are on main.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-gl-categorization-architecture.md` (Status block)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (top two paragraphs)
- The continuation prompt handed at the end of this session (items 4-6)

### Open Questions
- Corp Services settings `scope_groups` are Cloud Services' groups, not `CorpServ | OpeEx`. Undecided; not touched.
- A company that changes through a later card assignment does not re-categorize.

### Working Notes
- Live receipt labels: `Corporate Services` 146, `Cloud Services` 17, `Consulting` 9, blank 129, plus single rows on the long `Brisken ... LLC` names.
- Settings entity keys are the long legal names. `Brisken GmbH` and `Brisken Holding, LLC` both map to 696750461, which is not curated.

### Reference Materials
- PRs #1281, #1283, #1286 on `011matthias/agentic-ops1.01`

---

## How to Continue
Paste the item 4-6 continuation prompt into a fresh chat; it carries the ESTABLISHED facts above and the SESSION LOOP.

---

## Strategic Feedback

### What Worked Well This Session
- Guarding each remote write with a read-back check. The JSON validity check refused to `mv` an empty upload, so four failed upload mechanisms never touched the live file.

### Suggestions
- `flyctl` file transfer to `/data` is broken on this machine in three different ways. A small `tools/fly_put_json.py` that does the in-place edit would retire the whole class.

### System Health
- The stop-b1-gate caught an offer (migrate old months) that contradicted a loaded memory; the fix belonged at write time, not after.
- Autonomy: 1 human intervention (permission to write to the Fly volume after the classifier denial).
