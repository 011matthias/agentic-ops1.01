# Version Control

Automation specs use semantic versioning (MAJOR.MINOR.PATCH) to track changes.

## Version Format

```
{MAJOR}.{MINOR}.{PATCH}
```

- **MAJOR:** Breaking changes, incompatible modifications
- **MINOR:** New features, backward compatible additions
- **PATCH:** Bug fixes, clarifications, documentation

## When to Bump

### Patch Version (0.0.X)

Increment for:
- Bug fixes in edge case handling
- Typo corrections
- Documentation clarifications
- Test additions (no behavior change)
- Logging improvements

**Examples:**
- Fix: Handle null values in transform
- Docs: Clarify rate limit behavior
- Test: Add test for empty input

### Minor Version (0.X.0)

Increment for:
- New features (backward compatible)
- New optional steps
- Additional notifications
- New edge case handling
- Performance improvements
- New acceptance criteria

**Examples:**
- Feature: Add Slack notification on completion
- Feature: Support batch processing
- Feature: Add retry logic for API errors

### Major Version (X.0.0)

Increment for:
- Breaking changes to inputs/outputs
- Trigger type changes
- System additions/removals that change flow
- Restructuring of steps
- Changes requiring code migration

**Examples:**
- Breaking: Change from CRON to webhook trigger
- Breaking: Remove Google Sheets sync step
- Breaking: Change output format

## Version History

Always maintain changelog in spec:

```markdown
## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-15 | Initial specification |
| 1.1.0 | 2024-02-01 | Add Slack notifications |
| 1.1.1 | 2024-02-05 | Fix duplicate detection |
| 2.0.0 | 2024-03-01 | Switch to webhook trigger |
```

## Pre-Release Versions

For specs not yet implemented:
- Start at `1.0.0` for initial spec
- Use `0.x.x` only for draft/experimental specs

## Frontmatter Updates

When bumping version, always update:

```yaml
version: 1.2.0        # New version
updated: 2024-02-15   # Today's date
```

Keep `created` date unchanged.

## Status Field

Update status as spec progresses:

| Status | Meaning |
|--------|---------|
| `planned` | Spec written, not implemented |
| `in_progress` | Implementation underway |
| `deployed` | Live in production |
| `deprecated` | Being phased out |

## Migration Notes

For major version bumps, add migration notes:

```markdown
## Migration Notes (v2.0.0)

### Breaking Changes
- Trigger changed from CRON to webhook
- Remove `FORTNOX_SYNC_HOUR` env variable

### Migration Steps
1. Update webhook URL in Upsales
2. Remove CRON job from Railway
3. Deploy new version
```
