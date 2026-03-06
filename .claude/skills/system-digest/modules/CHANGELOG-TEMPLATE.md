# Changelog Template

Template for generating a "what changed" digest. Covers primitive changes, client progress, and system learnings.

## Data Collection

### Changed Primitives

```bash
# Git log for .claude/ changes since DATE
git log --since="{DATE}" --name-only --pretty=format:"%h %s (%ci)" -- .claude/

# Categorize changes:
# - New files (added) → "New"
# - Modified files → "Updated"
# - Deleted files → "Removed"
```

### Client Progress

```bash
# For each client, read automation-status.yaml
# Compare current status with:
# 1. Previous digest (if exists in docs/digests/)
# 2. Or infer from last_changes timestamps
```

### System Learnings

```bash
# Read MEMORY.md, extract entries with dates >= --since
# Read docs/checkpoints/ for checkpoint files newer than --since
# Extract: key decisions, new patterns, gotchas discovered
```

---

## Internal Template

```markdown
# Agentic Ops — Changes Since {SINCE_DATE}
Generated: {DATE}

## Summary

- **{NEW_COUNT}** new primitives added
- **{UPDATED_COUNT}** primitives updated
- **{CLIENT_CHANGES}** client automation status changes

## New Primitives

{For each new file in .claude/:}
- **{type}:** `{name}` — {description or first meaningful line}

## Updated Primitives

{For each modified file in .claude/:}
- **{type}:** `{name}` — {what changed (from git commit message or diff summary)}

## Client Progress

{For each client with changes:}
### {Client Name}
| Automation | Previous Status | Current Status | Notes |
|------------|----------------|----------------|-------|
{rows from automation-status.yaml diff}

## Key Learnings

{From MEMORY.md entries and checkpoint files:}
- {Learning 1 — date, context, what was learned}
- {Learning 2}

## System Health Changes

- Rules budget: {BEFORE} → {NOW} lines (of 250)
- Skills: {BEFORE} → {NOW} total
- Modules: {BEFORE} → {NOW} total

## Checkpoints

{List checkpoint files created since SINCE_DATE with their topic/summary}
```

---

## Client-Facing Template

```markdown
# Progress Update — Since {SINCE_DATE}
Generated: {DATE}

## What's New

{For each automation with status changes:}

### {Automation Name}
- **Previous:** {human-readable previous status}
- **Now:** {human-readable current status}
- **What happened:** {plain-language description of work done}

## Improvements Made

{List any changes that affect the client's experience:}
- {Improvement 1}
- {Improvement 2}

## Next Steps

{From automation-status.yaml next_steps fields:}
- {Next step 1}
- {Next step 2}

## Reliability Updates

{Any testing/monitoring improvements:}
- {e.g., "Added outcome verification for A1 email sending"}
```
