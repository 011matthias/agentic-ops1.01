# n8n Spec Sections

Templates for n8n-specific sections in automation specs. Use these instead of the code-based sections when `orchestrator: n8n`.

---

## N8N Workflow Section

Include after the Flow Diagram. Replace the code-based "API References" section.

```markdown
## N8N Workflow

**Workflow Information:**
- **Status:** New workflow / Updating workflow {name} (ID: {id})
- **n8n Instance:** {client instance name from .mcp.json}
- **Workflow File:** `context/{automation_id}-n8n-workflow.json` (optional export)

**Credentials Required:**
| Credential Name | Type | Description |
|----------------|------|-------------|
| {System} - OAuth2 | OAuth2 API | {Purpose} |
| {System} - API Key | API Key Header | {Purpose} |

**Key Configuration:**
- **Trigger:** Schedule Trigger (daily at 08:00 CET) / Webhook (POST /path)
- **Error Handling:** All HTTP nodes → Continue on Fail / Retry On Fail (3 attempts)
- **Pagination:** {How handled, if applicable}
- **Rate Limiting:** {How handled}

**Node Types Used:**
| Node | Purpose | Count |
|------|---------|-------|
| Schedule Trigger | Daily execution | 1 |
| HTTP Request | Fetch/create data in {system} | {N} |
| Code | Transform data | {N} |
| IF | Filter logic | {N} |
```

---

## API References (n8n variant)

n8n specs list API endpoints and note whether native n8n nodes exist.

**IMPORTANT:** All endpoint paths must be verified from fetched API docs (`workspace/api-docs/{system}/full-documentation.md`).
Never guess or invent paths — wrong paths cause runtime failures in HTTP Request nodes.
If docs were not fetched, mark the row with `⚠️ VERIFY` in the Notes column.

```markdown
## API References

> Source: `workspace/api-docs/{system}/full-documentation.md` (fetched {date})

| System | Endpoint | Method | Auth | Notes |
|--------|----------|--------|------|-------|
| Fortnox | `/3/orders` | GET | OAuth2 Bearer | HTTP Request node — verified from docs |
| Fortnox | `/3/orders/{DocumentNumber}` | PUT | OAuth2 Bearer | HTTP Request node — verified from docs |
| Slack | N/A | N/A | Bot Token | Native Slack node available |
| SomeAPI | `/unknown/path` | POST | API Key | ⚠️ VERIFY — docs not yet fetched |
```

---

## Testing Section (n8n)

Replace the pytest-based testing section with this:

```markdown
## Testing

### Manual Testing in N8N

**Setup:**
1. Add Limit node (set to 2) after {fetch node} to process only 2 items
2. Disable write nodes: {list POST/PUT/DELETE node names}
3. Disable notification nodes: {list notification node names}

**Test Execution:**
1. Run manually via N8N UI
2. Inspect outputs at each node:
   - {Node name}: Check {what to verify}
   - {Node name}: Verify {expected output}
3. Verify data transformations produce expected format

**Single Write Test:**
1. Enable {write node name} with Limit = 1
2. Execute manually
3. Verify in {target system} UI:
   - {What to check}
   - {Another check}

**Production Run:**
1. Remove Limit node
2. Enable all nodes
3. Monitor first full execution
4. Verify {expected outcome}

### Visual Verification

**In {Target System} UI:**
1. Navigate to {location in UI}
2. Verify {field} is populated correctly
3. Check {field} matches expected value: {pattern}
4. Confirm no duplicate entries created

### Idempotency Test

1. Run workflow manually (creates items)
2. Run workflow again on same data
3. Verify NO duplicate items created
4. Check workflow logs show items skipped

### Acceptance Criteria

**Workflow Execution:**
- [ ] Workflow completes without errors
- [ ] All nodes execute in correct order
- [ ] Execution time is reasonable

**Data Processing:**
- [ ] All {resource} fetched (check node output count)
- [ ] Only {condition} items processed
- [ ] {Transformation} produces correct output

**Target System:**
- [ ] {Resource} created/updated with correct fields
- [ ] Duplicate prevention works on re-run
- [ ] {Specific field} set to {expected value}

**Visual Verification:**
- [ ] {System} UI shows expected results
- [ ] All required fields populated
- [ ] No unexpected side effects
```

---

## Implementation Notes (n8n)

Replace the code-based implementation notes with this:

```markdown
## Implementation Notes

**Orchestrator:** n8n ({node strategy description})

**Node Strategy:**
- **Native nodes:** {List systems with native n8n nodes}
- **HTTP Request nodes:** {List systems using HTTP Request}
- **Code nodes:** {List transformations needing JavaScript}

**Credentials Setup:**
| Credential | Type | Notes |
|------------|------|-------|
| {System} OAuth2 | OAuth2 API | Configure in n8n Credentials, auto-refresh enabled |
| {System} API Key | API Key Header | Header: `X-API-Key` |

**Testing Approach:**
- Manual testing in n8n UI with Limit nodes
- Visual verification in {target systems}
- Idempotency testing (re-run doesn't create duplicates)
```

---

## Usage

When generating an n8n spec, swap these sections for the code-based equivalents:

| Code-Based Section | n8n Section |
|-------------------|-------------|
| API References (table only) | API References + N8N Workflow section |
| Testing (pytest) | Manual Testing in N8N + Visual Verification |
| Implementation Notes (Python) | Implementation Notes (n8n) |
| Environment Variables | Credentials Setup |
