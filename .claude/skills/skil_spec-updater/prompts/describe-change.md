# Describe Change

Ask the user about the change they want to make:

> "Tell me about the change you want to make to this automation:
>
> 1. **Change type:** Is this a new feature, behavior change, or bug fix?
> 2. **Description:** What specifically are you changing?
> 3. **Affected steps:** Which steps are impacted? (Initialize, Fetch, Transform, Execute, Finalize)
> 4. **New systems:** Are any new APIs or integrations involved?
> 5. **Edge cases:** Are there new error scenarios to handle?
> 6. **Breaking:** Does this change how the automation is triggered or its outputs?"

## Parsing Responses

From the user's answers, determine:

| Answer | Determines |
|--------|------------|
| Change type | Version bump type (patch/minor/major) |
| Description | Changelog entry text |
| Affected steps | Which spec sections to update |
| New systems | API References to add |
| Edge cases | Edge Cases section updates |
| Breaking | Major version bump required? |

## Follow-up Questions

**For new features:**
> "How should this feature behave when:
> - The feature fails?
> - Data is missing?
> - The external service is unavailable?"

**For behavior changes:**
> "Is this backward compatible? Will existing data/configs still work?"

**For bug fixes:**
> "Can you describe the bug scenario and expected behavior?"

**For unclear scope:**
> "Can you walk me through an example of this change in action?"

## Change Classification Matrix

| User Says | Change Type | Version |
|-----------|-------------|---------|
| "add notification" | New feature | Minor |
| "fix handling of..." | Bug fix | Patch |
| "change trigger to..." | Breaking change | Major |
| "improve performance" | Enhancement | Minor |
| "add retry logic" | New feature | Minor |
| "clarify documentation" | Documentation | Patch |
| "remove step" | Breaking change | Major |
| "add optional field" | New feature | Minor |
