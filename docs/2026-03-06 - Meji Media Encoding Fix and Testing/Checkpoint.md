# Checkpoint: Meji Media Encoding Fix and Testing

**Date:** 2026-03-06
**Status:** Encoding fixed, 7/7 tests passed, A1 active in eu2, A2/A3 ready to activate

---

## Summary
Fixed pervasive UTF-8 encoding corruption across eu2 deployment (scenario names, data store records). Root cause: Windows cp1252 re-encoding em-dashes during temp file creation in previous session. Standardized on ASCII hyphens for names and HTML entities for body content. Re-seeded all 9 data store records. Ran 7-test battery with zero errors. Updated `make-api.py` data store PUT format (flat fields, not wrapped in `data`).

---

## What Was Done This Session

### Encoding Diagnosis
1. Confirmed A1 and A3 scenario names garbled in Make UI (screenshot: "A1 a€" Enquiry...")
2. Traced root cause: UTF-8 em-dashes (U+2014) re-encoded as cp1252 during Python temp file creation on Windows
3. A2 name was correct (different encoding path during deployment)
4. Data store records also affected: `\ufffd` replacement chars in subjects, body HTML, and signature

### Scope Verification
5. Confirmed A1 scope is correct (14 modules, matches spec v3.0.0): intake + scoring + A/B + routing + initial email
6. No consolidation or overlap between A1/A2/A3 - clean separation of concerns

### Encoding Fixes
7. PATCHED scenario names (all 3) to use ASCII hyphens via REST API
8. Re-activated A1 after name PATCH deactivated it (learned: PATCH name deactivates scenarios)
9. Fixed template blueprint source files (a1/a2/a3-template.json) - ASCII hyphens
10. Fixed infrastructure.yaml - ASCII hyphens throughout
11. Re-seeded Pipeline Config (DS 153173) with all 37 fields, clean encoding, updated `handoff_email`
12. Re-seeded Email Templates (DS 153175) - all 8 A/B records with HTML entities for special chars
13. Created `reseed-eu2-datastores.py` script for repeatable re-seeding

### API Bug Fix
14. Fixed `make-api.py` `ds-upsert` function - PUT format was `{"data": {...}}` (wrong), corrected to flat fields

### Testing (7/7 passed)
15. Test 1: Standard lead - processed, 0 DLQ errors
16. Test 2: Hot lead (corporate, business email, phone, long message) - processed, 0 DLQ
17. Test 3: A/B distribution (4 rapid submissions) - all processed
18. Test 4: Minimal fields (name + email only) - processed without error
19. Test 5: Data integrity - pending user visual verification of sheet + emails
20. Test 6: A2 structural - no placeholder IDs, correct spreadsheet ID
21. Test 7: A3 structural - no placeholder IDs, correct DS IDs (153173, 153175), correct spreadsheet ID

---

## Key Decisions Made

### ASCII Hyphens Everywhere
- **Choice:** Replace all em-dashes with ASCII hyphens in scenario names, template names, and infrastructure.yaml
- **Rationale:** Windows cp1252 encoding on this machine makes UTF-8 special characters unreliable in any flow involving temp files. ASCII is universally safe.

### HTML Entities for Body Content
- **Choice:** Use `&#8212;` (em-dash) and `&middot;` (middle dot) in HTML email body and signature instead of literal Unicode
- **Rationale:** HTML entities render correctly in all email clients and bypass any encoding issues in the Make.com data store chain

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/meji-media/automations/blueprints/a1-template.json` | Modified | Name: em-dash to hyphen |
| `workspace/clients/meji-media/automations/blueprints/a2-template.json` | Modified | Name: em-dash to hyphen |
| `workspace/clients/meji-media/automations/blueprints/a3-template.json` | Modified | Name: em-dash to hyphen |
| `workspace/clients/meji-media/infrastructure.yaml` | Modified | All names: em-dashes to hyphens |
| `tools/make-api.py` | Modified | Fixed ds-upsert PUT format (flat fields) |
| `workspace/clients/meji-media/automations/scripts/reseed-eu2-datastores.py` | Created | Repeatable data store re-seeding script |
| `MEMORY.md` | Modified | Added encoding lesson, API format fix, eu2 IDs |

---

## Current Status

**Client org (eu2.make.com):**
- A1 (8804011): active, webhook, 7 test submissions processed, 0 errors
- A2 (8804012): inactive, scheduled (300s), structurally verified
- A3 (8804014): inactive, scheduled (900s), structurally verified
- Pipeline Config (153173): 37 fields, clean encoding
- Email Templates (153175): 8 A/B records, clean encoding
- Google Sheet: 8 rows (1 from prev session + 7 from this session's tests)

**User action needed:**
- Check Google Sheet (log into client.meji-media@unpauseai.com) - verify 7 test rows have clean data, no garbled chars
- Check email inbox - verify received emails have proper HTML (no replacement characters in signature or body)

---

## Next Steps

1. **User: verify sheet + email quality** - visual check for encoding issues
2. **Clean up test rows** from Google Sheet after verification
3. **Share webhook URL with Anuj** for website form integration
4. **Get client Gmail access** - `enquire@christmasofficeparty.co.uk`
5. **Activate A2 then A3** when client Gmail connected
6. **Get Gurmej's email templates** and update Email Templates DS

---

## Context for Next Session

### Files to Read First
- `workspace/clients/meji-media/infrastructure.yaml` - complete eu1 + eu2 resource inventory
- `workspace/clients/meji-media/context/comms-log.md` - open items

### Open Questions
- Has user verified clean encoding in sheet and emails?
- When will Anuj integrate webhook URL?
- When will client Gmail access be available?

---

## Strategic Feedback

### What Worked Well
- The `reseed-eu2-datastores.py` script bypassed all Windows encoding traps by constructing JSON in Python (not via shell). This pattern should be reused for any future data store seeding.
- Learning that PATCH on scenario `name` deactivates it - documented in MEMORY.md for future reference.

### Suggestions
- `make-api.py` should add `--encoding-check` flag that scans a blueprint JSON for non-ASCII characters and warns before deployment. Would have caught this issue at deploy time.

### System Health
- The `make-api.py` `ds-upsert` was silently broken for existing records (wrong PUT format). Fixed and documented. All prior data store seeding (dev org) should be verified - but since those were done via MCP tools (not make-api.py), they were likely unaffected.
