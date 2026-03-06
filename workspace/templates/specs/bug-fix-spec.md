---
id: fix{N}                         # Increment from highest existing fix{N} across all stage folders
name: {Fix Description}
type: bug-fix
stage: spec                        # spec | build | test | live
needs_fixes: false
version: 1.0.0
created: {YYYY-MM-DD}
updated: {YYYY-MM-DD}
orchestrator: trigger-dev          # Match the parent automation's orchestrator
parent: a{N}                       # REQUIRED: ID of the automation being fixed (e.g., a2, a6.3)
systems:
  - system1
owner: owner@client.com
last_changes: []
next_steps: []
stage_history:
  - stage: spec
    date: {YYYY-MM-DD}
---

# Fix{N}: {Fix Description} (in {Parent Automation Name})

**Parent Automation:** [a{N} — {Parent Name}](../{stage}/a{N}-{parent-filename}.md)

> Also set `needs_fixes: true` in the parent spec's frontmatter. Clear it when this fix reaches `live`.

## Problem

**Symptom:** {What is failing, broken, or incorrect — observable behavior}

**Impact:** {Who/what is affected — which runs fail, which data is wrong, etc.}

**First Observed:** {YYYY-MM-DD or "reported by client"}

## Root Cause

{Describe the root cause once identified. Update this field after investigation. Start with "TBD — investigation needed" if unknown.}

## Fix Plan

**Files to Change:**

| File | Lines | Change |
|------|-------|--------|
| `{file path}` | {L42-L55} | {What to change} |

**Steps:**

1. {Describe change 1}
2. {Describe change 2}

## Testing

### Verification Steps

- [ ] {Reproduce the bug (confirm it exists before fixing)}
- [ ] {Apply fix}
- [ ] {Confirm the symptom no longer occurs}
- [ ] {Run existing tests to check for regressions}

### Acceptance Criteria

- [ ] {Bug no longer occurs under original conditions}
- [ ] {No regression in surrounding behavior}
- [ ] {Parent automation runs cleanly end-to-end}

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | {YYYY-MM-DD} | Initial fix spec |
