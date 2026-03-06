# Answer Integration

How to write discovered answers back to project files after running a discovery script.

## Step 1: Update open-questions.md

If `workspace/clients/{client}/docs/open-questions.md` exists, add the answer to the **Answers Log** table.

```markdown
## Answers Log

| Date | Question | Answer |
|------|----------|--------|
| 2026-02-18 | What is the Upsales filter param for updatedAt? | `modDate=gt:{iso}` — "modifiedSince" and "updatedAt" return 0 results |
| 2026-02-18 | Does Fortnox order have a Upsales reference? | NO — reference goes the other way: Fortnox DocumentNumber stored in Upsales deal.description |
```

If the file doesn't exist, create it:

```markdown
# Open Questions — {Client Name}

## Unanswered Questions

*(none)*

## Answers Log

| Date | Question | Answer |
|------|----------|--------|
| {date} | {question} | {answer} |
```

## Step 2: Update Spec next_steps

If the answered question came from a spec's `next_steps:` frontmatter, remove the resolved item.

```yaml
# Before
next_steps:
  - "Confirm exact Airtable field name for delivery type"
  - "Check if TeamLeader invoice API supports attention-to field"

# After (first item answered)
next_steps:
  - "Check if TeamLeader invoice API supports attention-to field"
```

If ALL items are answered: set `next_steps: []`

## Step 3: Flag Contradicted Assumptions

If a discovered answer contradicts something in the spec body, surface it visibly — do NOT silently update.

```
⚠️  SPEC ASSUMPTION INCORRECT

Spec says:  "Filter Upsales orders using `modifiedSince` parameter"
Reality:    Upsales API uses `modDate=gt:{iso}` — `modifiedSince` returns 0 results

→ Spec step [2.1] needs updating before proceeding to build.
  Confirm update?
```

Wait for user confirmation before editing the spec.

## What NOT to Update Automatically

| Action | Rule |
|--------|------|
| Spec steps with wrong field names | Flag + ask, don't auto-edit |
| Field mapping tables in the spec | Flag + ask, don't auto-edit |
| Assumptions needing architectural rethink | Flag only — solution needs discussion |

## Large Answers (Field Listings, Tables)

For large outputs like full Airtable field listings, don't squeeze them into the Answers Log cell. Instead:

1. Add a brief summary row to the Answers Log:
   ```
   | 2026-02-18 | Airtable fields for contracten of locaties? | 23 fields confirmed — see field map in spec §Data Model |
   ```
2. Add the full field map markdown table to the spec (Data Model or Field Mappings section)
3. Or save a standalone reference: `workspace/clients/{client}/context/discovery/airtable-{table}-fields.md`
