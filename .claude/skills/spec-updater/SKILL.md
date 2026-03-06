---
name: spec-updater
description: Updates existing automation specifications with new features or changes. Use when adding features to an existing automation, modifying behavior, fixing spec bugs, or extending functionality. Maintains version history and updates Mermaid diagrams.
---

# Spec Updater

Updates existing automation specifications while maintaining version history and consistency.

## Quick Start

1. Load existing spec from `workspace/clients/{client}/specs/automations/{id}.md`
2. Understand change using `prompts/describe-change.md`
3. Classify change type per `modules/VERSION-CONTROL.md`
4. Update affected sections
5. Increment version and update timestamp

## Process

### Step 1: Locate Existing Spec

Find the spec file:
```
workspace/clients/{client}/specs/automations/{id}.md
```

If using old format (single file), locate section in:
```
workspace/clients/{client}/specs/automation-workflows.md
```

Read the full spec to understand current state.

### Step 2: Understand the Change

Load and follow `prompts/describe-change.md` to ask:
- What change are you making?
- Which steps are affected?
- Are new systems/APIs involved?
- Any new edge cases?

### Step 3: Classify Change Type

Per `modules/VERSION-CONTROL.md`:

| Type | Version Bump | Examples |
|------|--------------|----------|
| Patch (0.0.x) | Bug fix, typo, clarification | Fix edge case handling |
| Minor (0.x.0) | New feature, backward compatible | Add notification step |
| Major (x.0.0) | Breaking change, restructure | Change trigger type |

### Step 4: Update Spec Sections

Based on change type, update relevant sections:

**For new features:**
- Update Flow Diagram (Mermaid)
- Add new Step Details
- Add Edge Cases for new functionality
- Add Acceptance Criteria
- Add Unit/Integration Tests

**For behavior changes:**
- Update affected Step Details
- Update Edge Cases
- Update Acceptance Criteria
- Note breaking changes if any

**For bug fixes:**
- Update Edge Cases section
- Add regression test to Testing section

### Step 5: Update Frontmatter

```yaml
version: {new_version}
updated: {today's date YYYY-MM-DD}
```

### Step 6: Add Changelog Entry

Add to bottom of Changelog table:

```markdown
| {version} | {date} | {brief description of changes} |
```

### Step 7: Generate Implementation Notes

Output for developer:
- Which code files need changes
- New tests to write
- Configuration changes needed

## Output

Updated spec file with:
- Incremented version
- Updated timestamp
- Modified sections
- Changelog entry

Report to user:
- Summary of changes made
- Implementation notes
- Affected code files

## Modules

| Module | Purpose |
|--------|---------|
| [VERSION-CONTROL.md](modules/VERSION-CONTROL.md) | Semantic versioning rules |

## Notes

- Always read the full spec before making changes
- Preserve existing content that isn't changing
- Keep Mermaid diagrams in sync with step details
- Ensure acceptance criteria remain testable
