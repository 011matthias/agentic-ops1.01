# Make.com Spec Sections

Templates for Make.com-specific sections in automation specs. Use these instead of the code-based sections when `orchestrator: make`.

---

## Make.com Scenario Section

Include after the Flow Diagram. Replace the code-based "API References" section.

```markdown
## Make.com Scenario

**Scenario Information:**
- **Status:** New scenario / Updating scenario {name}
- **Make.com Organization:** {org name}
- **Scenario URL:** {direct link to scenario in Make.com}

**Connections Required:**
| Connection Name | App | Type | Description |
|----------------|-----|------|-------------|
| {System} - OAuth2 | {App} | OAuth2 | {Purpose} |
| {System} - API Key | {App} | API Key | {Purpose} |

**Key Configuration:**
- **Trigger:** Instant webhook / Scheduled ({interval}) / Watch module ({resource})
- **Error Handling:** Error handlers on HTTP and write modules (Break for fatal, Resume for non-fatal)
- **Rate Limiting:** Sleep modules between iterations ({N}ms)
- **Data Volume:** Iterator for array processing, {batch size} items per run

**Module Types Used:**
| Module | App | Purpose | Count |
|--------|-----|---------|-------|
| Watch {resource} | {System} | Trigger: detect new items | 1 |
| HTTP Make a request | Generic | Fetch/create data in {system} | {N} |
| Router | Flow control | Branch scenario logic | {N} |
| Iterator | Flow control | Process arrays | {N} |
| Filter | Flow control | Conditional pass | {N} |
| Set variable | Tools | Store intermediate data | {N} |
```

---

## API References (Make.com variant)

Make.com specs list API endpoints and note whether native Make.com app modules exist.

**IMPORTANT:** All endpoint paths must be verified from fetched API docs (`workspace/api-docs/{system}/full-documentation.md`).
Never guess or invent paths -- wrong paths cause runtime failures in HTTP modules.
If docs were not fetched, mark the row with `⚠️ VERIFY` in the Notes column.

```markdown
## API References

> Source: `workspace/api-docs/{system}/full-documentation.md` (fetched {date})

| System | Endpoint | Method | Auth | Notes |
|--------|----------|--------|------|-------|
| Fortnox | `/3/orders` | GET | OAuth2 Bearer | HTTP module -- no native Make.com app |
| Slack | N/A | N/A | Bot Token | Native Slack app module available |
| Google Sheets | N/A | N/A | OAuth2 | Native Google Sheets app module available |
| SomeAPI | `/v1/items` | POST | API Key | HTTP module -- ⚠️ VERIFY docs not fetched |
```

---

## Testing Section (Make.com)

Replace the pytest-based testing section with this:

```markdown
## Testing

### Manual Testing in Make.com

**Setup:**
1. Ensure scenario scheduling is OFF (toggle in bottom-left)
2. Prepare test data in source system (or use test webhook payload)
3. Open scenario in Make.com editor

**Test Execution (Run once):**
1. Click "Run once" in Make.com editor
2. Watch execution flow -- inspect each module's input/output bubbles
3. Verify data mappings produce expected format
4. Check filters pass/block expected items
5. Confirm output modules send correct data

**Single Write Test:**
1. Run once with limited input (1-2 items)
2. Verify in {target system} UI:
   - {What to check}
   - {Another check}

**Production Run:**
1. Toggle scheduling ON
2. Monitor first 2-3 scheduled executions in execution history
3. Verify all items processed correctly
4. Check for incomplete executions

### Visual Verification

**In {Target System} UI:**
1. Navigate to {location in UI}
2. Verify {field} is populated correctly
3. Check {field} matches expected value: {pattern}
4. Confirm no duplicate entries created

### Idempotency Test

1. Run scenario once (items created)
2. Run scenario again on same data
3. Verify NO duplicate items created
4. Check execution history shows items filtered/skipped

### Acceptance Criteria

**Scenario Execution:**
- [ ] Scenario completes all modules without errors
- [ ] All modules execute in correct order (check execution inspector)
- [ ] Execution time is reasonable

**Data Processing:**
- [ ] All {resource} fetched (check module output count)
- [ ] Only {condition} items processed (check filter output)
- [ ] {Transformation} produces correct output

**Target System:**
- [ ] {Resource} created/updated with correct fields
- [ ] Duplicate prevention works on re-run
- [ ] {Specific field} set to {expected value}

**Error Handling:**
- [ ] Error handlers catch failures gracefully
- [ ] Incomplete executions are manageable
```

---

## Implementation Notes (Make.com)

Replace the code-based implementation notes with this:

```markdown
## Implementation Notes

**Orchestrator:** Make.com (manual UI, spec-guided)

**Module Strategy:**
- **Native app modules:** {List systems with native Make.com apps}
- **HTTP modules:** {List systems using generic HTTP module}
- **Flow control modules:** {Router, Iterator, Aggregator, Filter, Set variable}

**Connections Setup:**
| Connection | App | Type | Notes |
|------------|-----|------|-------|
| {System} | {App} | OAuth2 | Configure in Make.com Connections, auto-refresh enabled |
| {System} | {App} | API Key | Header: `{header-name}` |

**Testing Approach:**
- Run once in Make.com editor with test data
- Visual verification in {target systems}
- Check execution history for errors
- Idempotency testing (re-run creates no duplicates)
```

---

## Usage

When generating a Make.com spec, swap these sections for the code-based equivalents:

| Code-Based Section | Make.com Section |
|-------------------|-----------------|
| API References (table only) | API References + Make.com Scenario section |
| Testing (pytest) | Manual Testing in Make.com + Visual Verification |
| Implementation Notes (Python) | Implementation Notes (Make.com) |
| Environment Variables | Connections Setup |
