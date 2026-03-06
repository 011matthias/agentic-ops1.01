# Comms Log

Persistent per-client conversation record. Lives at `workspace/clients/{client}/context/comms-log.md`.

The comms-log bridges outbound drafting (`/draft`) and inbound processing (`/comms`). It gives every future message conversational memory and feeds into `/resume` for session continuity.

---

## File Format

The log is a YAML frontmatter block with summary stats, followed by a markdown body with chronological entries.

```yaml
---
client: meji-media
last_contact: 2026-03-04
total_entries: 5
unresolved_count: 2
---
```

### Entry Format

Each entry is an H3 header with a date, followed by structured fields.

**Outbound entry:**
```markdown
### 2026-03-02 — Outbound (status-update)
**To:** Gurmej, Jess, Anuj
**Summary:** Progress update. Asked Anuj about CRM integration, Gurmej for email templates, presented A/B analytics options.
**Open items:**
- How does CRM integration work? (Anuj)
- Email templates needed (Gurmej)
- A/B analytics: Option 1 or 2? (Gurmej)
```

**Inbound entry:**
```markdown
### 2026-03-04 — Inbound from Anuj
**Summary:** CRM uses Zapier webhook. Sends JSON payload with name, email, venue, date.
**Decisions:**
- Webhook format confirmed: JSON with 4 fields
**Implications:**
- A1 webhook parsing needs Zapier-format adapter
- No website changes needed (confirmed)
**Resolved:** How does CRM integration work?
```

**Decision-only entry** (for quick captures outside full inbound processing):
```markdown
### 2026-03-05 — Decision
**From:** Gurmej
**Decision:** Go with Option 1 (spreadsheet analytics tab)
**Implications:**
- Add analytics tab to enquiry tracking sheet
- Update spec a3 to include analytics
**Resolved:** A/B analytics: Option 1 or 2?
```

---

## Read Procedures

### For `/draft` (outbound context)
Load the comms-log and extract:
1. **Last 3-5 entries** — recent conversation thread for continuity
2. **All unresolved open items** — scan all entries, collect items not yet marked resolved by any later entry
3. **Recent decisions** (last 2 weeks) — for reference in messages
4. **Last contact date + direction** — who spoke last, and when (for temporal opener rules)

### For `/comms inbound` (deduplication)
Load the full log to:
1. Compare pasted content against existing entries for deduplication
2. Identify the last logged entry date for gap detection
3. Check open items for auto-resolution

### For `/resume` (session context)
Extract:
1. All unresolved open items — these are "things to address this session"
2. Last 3 entries — recent conversation state
3. Last contact date — how stale is the relationship?

---

## Write Procedures

### After `/draft` (outbound logging)

After the user approves a draft, ask: "Want me to log this in the comms history?"

If yes:
1. Auto-generate an outbound entry from the approved draft
2. Extract open items (questions asked, things requested from client)
3. Show the proposed entry to the user before writing
4. Append to `context/comms-log.md`
5. Update frontmatter (`last_contact`, `total_entries`, `unresolved_count`)

### After `/comms inbound` (inbound logging)

After processing a client response, ask: "Want me to log this?"

If yes:
1. Generate inbound entry from extracted content (only NEW messages, not duplicates)
2. Include: summary, decisions, implications, resolved items
3. Show the proposed entry to the user before writing
4. Append to `context/comms-log.md`
5. Auto-resolve matching open items from previous entries
6. Update frontmatter

### Quick Capture (batch catch-up)

Used when logging missed conversations during `/checkpoint` or `/resume` staleness prompts. Optimized for speed over analysis depth.

1. Ask: "Briefly describe what was discussed (who, when, key points, any decisions or open items)."
2. Accept natural-language input — no structured format required.
3. Generate a minimal entry:
   ```markdown
   ### {DATE} — {Inbound from X | Outbound | Call}
   **Summary:** {user's description, lightly cleaned up}
   **Decisions:** {extract if mentioned, omit if none}
   **Open items:** {extract if mentioned, omit if none}
   ```
4. Show the proposed entry. Ask: "Log this?" (yes/no/edit)
5. If yes: append to `comms-log.md`, update frontmatter.
6. Ask: "Any more to log?" — repeat for each missed conversation.
7. After all entries logged, update `unresolved_count` and `last_contact` in frontmatter.

Skip deduplication, feasibility checks, and spec-impact analysis. Those are for full `/comms inbound` processing. Quick capture is "get it in the log" — entries can be elaborated later.

### Resolution Tracking

An open item is considered resolved when:
- A later inbound entry has it in its `Resolved:` field
- The user manually marks it resolved via `/comms {client} status`

When resolving, don't delete the original open item. The history stays. The resolution is tracked by the `Resolved:` field in the resolving entry.

---

## Unresolved Items Collection

To build the current unresolved items list:

1. Scan all entries chronologically
2. Collect all items from `Open items:` fields
3. Remove any that appear in a later entry's `Resolved:` field
4. Return the remaining items with their dates and assigned contacts

This is the "what are we still waiting on?" view.

---

## Creating a New Log

When `/comms` or `/draft` is used for a client that has no comms-log yet:
1. Create from `templates/comms-log-template.md`
2. If there's a recent checkpoint with blockers/open questions, offer to seed those as the initial open items
3. Don't force it — the log starts whenever the user first logs something
