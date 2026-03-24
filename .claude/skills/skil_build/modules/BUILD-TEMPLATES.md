# BUILD-TEMPLATES — Report Templates for Build Orchestrator

Load this module when generating phase reports, session summaries, progress updates, or build log entries.

---

## Session Summary Template

Create `.claude/handoffs/{session}/session-summary.md`:

```markdown
# Build Session Summary

**Client:** {client}
**Automation:** {id}
**Session ID:** {session_id}
**Duration:** {start} → {end}

## Phase Results

| Phase | Status | Duration |
|-------|--------|----------|
| Plan | ✓/✗ | Xm |
| Implement | ✓/✗ | Xm |
| Test (Local) | ✓/✗ | Xm |
| Test (Dev) | ✓/✗ | Xm |
| Docs | ✓/✗ | Xm |
| Deploy | ✓/✗ | Xm |
| Verify | ✓/✗ | Xm |

## Artifacts Created

**Spec:** `workspace/clients/{client}/specs/{stage}/{id}-*.md`
**Code:** `{code_path}` ({N} lines)
**Tests:** `{test_path}` ({N} tests)
**Docs:** `docs/technical/{id}.md`, `docs/client/{id}.md`
**Deployment:** {url}

## Test Results

**Unit Tests:** {passed}/{total} | **Coverage:** {pct}% | **Acceptance Criteria:** {verified}/{total}

## Issues & Fixes

1. {Phase}: {issue} → {fix}

## Next Steps

- Monitor first automated run
- Check dashboard for execution logs

## Session Files

All phase reports saved to: `.claude/handoffs/{session_id}/`
```

---

## Phase Report Template

```markdown
# Phase Report: {Phase Name}

**Agent:** {agent-name}
**Status:** success|failure|partial
**Timestamp:** {ISO}

## Artifacts
- [ ] {artifact}: {path}

## Context for Next Phase
**Key Information:**
- {bullet points}

**Warnings:**
- {issues}

**Recommendations:**
- {suggestions}
```

---

## Progress Update Template

```markdown
## Build Progress: Phase {N}/7 - {Phase Name}

**Current:** {agent_name} working...
**Elapsed:** {duration}

{phase-specific_details}

---
**Next:** {next_phase_name}
```

---

## Build Log Entry

Append to `workspace/clients/{client}/context/build-log.md` after session completion:

1. If file doesn't exist, create with frontmatter:
   ```yaml
   ---
   client: {client}
   total_builds: 0
   ---
   ```

2. Increment `total_builds` in frontmatter
3. Append:
   ```markdown
   ### {DATE} — {AUTOMATION_ID} ({AUTOMATION_NAME}) — {STAGE}
   **Iterations:** {N} | **Errors:** [{error categories}]
   **Fixes applied:** [{FIX-PATTERN IDs}] | **Outcome:** {success/partial/escalated}
   ```

---

## Completion Output

```markdown
# Build Complete: {Automation Name}

**Client:** {client} | **Automation:** {id} | **Status:** Production Ready

## What Was Built
{summary}

## Where to Find Everything
{paths_and_urls}

## Next Steps
{immediate_actions}
```
