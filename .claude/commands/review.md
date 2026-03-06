---
description: Surface patterns from session logs, build logs, and friction register. Data-driven system improvement.
argument-hint: [--save]
---

# Review

Analyze accumulated log data to identify recurring friction, error patterns, and automation opportunities.

## Context

- Working directory: !`pwd`
- Arguments: $ARGUMENTS

## Parse Arguments

- **`--save`** (optional): Write the review to `docs/reviews/YYYY-MM-DD.md` in addition to terminal output.

## Step 1: Read Log Sources

Read all available sources. If any source is missing or empty, note it and continue with available data.

### Session Logs
Read all files in `docs/sessions/`:
- Extract `friction_events` count from each file's frontmatter
- Collect all `**Friction:**` lines from session entries (skip "None")
- Note `clients_touched` and `sessions` counts per day

### Build Logs
Read `workspace/clients/*/context/build-log.md` for each client that has one:
- Extract `total_builds` from frontmatter
- Collect error categories from `**Errors:**` fields
- Collect FIX-PATTERN IDs from `**Fixes applied:**` fields
- Note iteration counts per build

### Friction Register
Read `docs/friction-register.md`:
- Count occurrences of each (Type, Description) pair to compute frequency
- Separate resolved vs unresolved rows

## Step 2: Detect Patterns

### Friction Patterns (from friction register + session logs)
- Group friction events by Type
- Identify events with frequency >= 3 that are not resolved
- Flag any `MANUAL_INTERVENTION` or `TOOL_LIMITATION` that repeats across 2+ clients

### Error Patterns (from build logs)
- Compute error category distribution across all builds
- Flag categories exceeding 30% of total build iterations
- Identify error categories not covered in FIX-PATTERNS.md (check `.claude/skills/build-test-fix/modules/FIX-PATTERNS.md`)

### Efficiency Patterns (from build logs)
- Compute average iterations per build (overall and per client)
- Identify clients with above-average iteration counts
- Flag builds with 3+ iterations (hit escalation threshold)

## Step 3: Score by ROI

For each identified pattern, estimate:

```
ROI = (frequency × estimated_minutes_per_occurrence) / estimated_hours_to_fix
```

Present as table:

| # | Pattern | Source | Freq | Est. Effort/Occurrence | Est. Fix Hours | ROI | Suggested Fix |
|---|---------|--------|------|----------------------|----------------|-----|---------------|

Sort by ROI descending. Top 5 are candidates for `/system-dev` implementation.

## Step 4: Generate Summary

```markdown
## Review: {DATE}

### Data Coverage
- Session logs: {N} days, {M} sessions
- Build logs: {N} clients, {M} builds
- Friction register: {N} events ({U} unresolved)

### Top Friction Patterns
{ROI table from Step 3}

### Error Distribution
| Category | Count | % of Total | In FIX-PATTERNS? |
|----------|-------|------------|-------------------|

### Recommendations
1. {Highest-ROI pattern} — suggest /system-dev to implement
2. {Second pattern}
3. {Third pattern}

### Since Last Review
{If previous review exists in docs/reviews/, diff against it: new patterns, resolved patterns, trend direction}
```

## Step 5: Deliver

- **Always:** Print summary to terminal
- **If `--save`:** Create `docs/reviews/` directory if needed, write to `docs/reviews/YYYY-MM-DD.md`

## Notes

- This command is READ-ONLY by default — it analyzes but makes no changes
- Use `/system-dev` to act on the patterns identified here
- Run periodically (weekly recommended) or after high-friction sessions
