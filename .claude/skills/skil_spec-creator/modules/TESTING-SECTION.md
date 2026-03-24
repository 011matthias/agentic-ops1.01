# Testing Section Template

Use this module to define the testing section of an automation spec. Choose the appropriate pattern based on the orchestrator.

- **Code-based (Trigger.dev / FastAPI):** Unit tests + integration tests (pytest)
- **n8n:** Manual testing in n8n UI + visual verification in target systems

---

## Code-Based Testing (Trigger.dev / FastAPI)

### 1. Unit Tests

Test individual functions in isolation. Focus on:
- Transform logic
- Data mapping/conversion
- Validation functions
- Edge case handlers

**Template:**

```python
def test_{automation_id}_transform():
    """
    Spec: {automation_id} - Step 3 Transform
    Tests that {specific behavior}.
    """
    # Arrange
    input_data = {
        "field": "value"
    }

    # Act
    result = transform(input_data)

    # Assert
    assert result["output_field"] == "expected"

def test_{automation_id}_filter():
    """Filter should only include items matching criteria."""
    items = [
        {"id": 1, "status": "active"},
        {"id": 2, "status": "inactive"}
    ]
    result = filter_items(items)
    assert len(result) == 1
    assert result[0]["id"] == 1

def test_{automation_id}_skip_duplicate():
    """Should skip items that already exist."""
    existing = {"item_123": True}
    new_item = {"id": "item_123"}
    result = should_process(new_item, existing)
    assert result is False
```

### 2. Integration Tests

Test with real/sandbox APIs:

```python
def test_{automation_id}_dry_run():
    """
    Spec: {automation_id} - Full Flow
    Tests complete automation in dry-run mode.
    No side effects should occur.
    """
    automation = MyAutomation()
    result = automation.run(dry_run=True)

    assert result["dry_run"] is True
    assert "would_process" in result
    assert result["would_process"] >= 0

def test_{automation_id}_sandbox():
    """
    Spec: {automation_id} - Full Flow (Sandbox)
    Tests complete automation against sandbox API.
    """
    automation = MyAutomation(use_sandbox=True)
    result = automation.run()

    assert result["status"] == "success"
```

### 3. Acceptance Criteria Tests

Each acceptance criterion should map to a test:

| Criterion | Test Name | What It Verifies |
|-----------|-----------|------------------|
| "Items created correctly" | `test_create_item_fields` | All fields set properly |
| "No duplicates" | `test_skip_existing` | Existing items skipped |
| "Errors logged" | `test_error_logging` | Failed items in logs |
| "Dashboard updated" | `test_log_written` | Execution logged to DB |

### Acceptance Criteria Format

Write criteria that are specific and testable:

**Good:**
- [ ] Draft orders created with customer_number, order_rows, and delivery_date
- [ ] Orders not created for contracts with existing order in same period
- [ ] Dashboard shows count of created orders after each run
- [ ] Failed order creations logged with error reason

**Bad:**
- [ ] Orders work correctly (too vague)
- [ ] System is fast (not measurable)
- [ ] No errors (too broad)

### Test Data Guidelines

#### Use Fixtures

```python
@pytest.fixture
def sample_contract():
    return {
        "id": "contract_123",
        "customer_number": "C001",
        "next_invoice_date": "2024-02-01",
        "contract_rows": [...]
    }

@pytest.fixture
def mock_fortnox_client():
    client = Mock()
    client.get_contracts.return_value = [...]
    return client
```

#### Test Edge Cases

```python
def test_empty_input():
    """Should handle empty data gracefully."""
    result = transform([])
    assert result == []

def test_missing_field():
    """Should use default when field is missing."""
    data = {"id": 1}  # missing "name"
    result = transform(data)
    assert result["name"] == "Unknown"

def test_invalid_date():
    """Should skip records with invalid dates."""
    data = {"date": "invalid"}
    result = validate(data)
    assert result is None
```

### Running Tests

```bash
# Run all tests for an automation
uv run pytest tests/test_{automation_id}.py -v

# Run with coverage
uv run pytest tests/test_{automation_id}.py --cov=app.automations.{automation_id}

# Run dry-run test only
uv run pytest tests/test_{automation_id}.py -k "dry_run"
```

### Test File Location

```
workspace/clients/{client}/automations/
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_{automation_id}.py  # Automation tests
│   └── test_clients/            # API client tests
│       └── test_{system}.py
```

---

## n8n Testing

n8n workflows are tested manually through the UI and by verifying results in target systems.

### 1. Manual Testing in n8n UI

**Setup (prevent side effects):**
1. Add **Limit node** (set to 2-3) after the main data fetch to process only a few items
2. **Disable write nodes** — any POST/PUT/DELETE HTTP Request nodes
3. **Disable notification nodes** — Slack, email, etc.

**Test execution:**
1. Click "Execute Workflow" in n8n UI
2. Watch execution flow in real-time
3. Inspect each node's input/output data
4. Verify transformations produce expected format
5. Check API responses contain expected fields

**Single write test:**
1. Enable one write node (keep Limit = 1)
2. Execute manually
3. Verify the item was created/updated correctly in the target system
4. Confirm data fields match expectations

**Production run:**
1. Remove Limit node
2. Enable all nodes
3. Monitor first full execution
4. Verify all items processed correctly

### 2. Visual Verification in Target Systems

After the workflow runs, verify results directly in the target system's UI:

**Template:**
```
1. Open {System} → {Section/Page}
2. Find {resource} by {identifier}
3. Verify {field} is populated: {expected value}
4. Check {field} matches: {expected value or pattern}
5. Confirm no duplicate entries created
```

**Example (Fortnox Order Creation):**
```
1. Open Fortnox → Orders
2. Find order by DocumentNumber from workflow output
3. Verify CustomerNumber matches contract
4. Check OrderRows contain expected line items
5. Confirm DeliveryDate matches contract PeriodEnd
6. Ensure YourOrderNumber follows pattern C{DocNum}-{Date}
```

### 3. Idempotency Test

Verify re-running the workflow doesn't create duplicates:

1. Run workflow manually (items created/updated)
2. Note what was created
3. Run workflow again on the same data
4. Verify NO duplicate items created
5. Check workflow execution shows items were skipped

### 4. Error Scenario Testing

Test how the workflow handles failures:

1. **Invalid input:** Use a non-existent ID — verify Continue On Fail works
2. **Missing fields:** Check Code node handles missing data with fallbacks
3. **API errors:** Temporarily break a credential — verify retry/error handling

### n8n Acceptance Criteria Format

Write criteria that are verifiable through UI inspection:

**Good:**
- [ ] All contract pages fetched (check node output count ≈ 1828)
- [ ] Only ACTIVE contracts processed (verify Filter node output)
- [ ] Draft order fields match contract data in Fortnox UI
- [ ] Duplicate orders prevented (re-run creates no new orders)
- [ ] Slack notification sent per created order

**Bad:**
- [ ] Workflow works (too vague)
- [ ] Data is correct (not specific about what to check)

### n8n Test Documentation

n8n workflows don't have test files. All testing documentation goes in the spec itself:

```
workspace/clients/{client}/specs/automations/
├── a1-workflow-name.md      # Spec includes testing section
└── README.md                # Index of automations
```

---

## Make.com Testing

Make.com scenarios are tested via the scenario editor's "Run once" feature and by verifying results in target systems.

### 1. Manual Testing in Make.com

**Setup (prevent side effects):**
1. Ensure scenario scheduling is **OFF** (toggle in bottom-left)
2. Prepare test data in source system (or use test webhook payload)
3. Open scenario in Make.com editor

**Test execution (Run once):**
1. Click **"Run once"** button
2. Watch execution flow -- each module shows an execution bubble
3. Click each bubble to inspect input/output data
4. Verify data mappings produce expected format
5. Check that filters pass/block expected items

**Single write test:**
1. Run once with a small dataset (1-2 items)
2. Verify item created/updated correctly in target system
3. Confirm field mappings are correct

**Production run:**
1. Toggle scheduling ON
2. Monitor execution history for first 2-3 scheduled runs
3. Verify all items processed correctly

### 2. Visual Verification in Target Systems

After the scenario runs, verify results directly in the target system's UI:

**Template:**
```
1. Open {System} → {Section/Page}
2. Find {resource} by {identifier}
3. Verify {field} is populated: {expected value}
4. Check {field} matches: {expected value or pattern}
5. Confirm no duplicate entries created
```

(Same approach as n8n -- inspect target system UI for correct data)

### 3. Idempotency Test

Verify re-running the scenario doesn't create duplicates:

1. Run scenario once (items created/updated)
2. Note what was created
3. Run scenario again on the same data
4. Verify NO duplicate items created
5. Check execution history shows items were filtered/skipped

### 4. Error Scenario Testing

Test how the scenario handles failures:

1. **Invalid input:** Provide malformed data -- verify error handler catches it
2. **Missing fields:** Check that `ifempty()` defaults work in mappings
3. **Connection errors:** Temporarily break a connection -- verify error handler route triggers
4. **Rate limits:** Process enough items to trigger rate limits -- verify Sleep module works

### Make.com Acceptance Criteria Format

Write criteria that are verifiable through the Make.com execution inspector and target system UIs:

**Good:**
- [ ] Scenario completes all modules without errors (check execution history)
- [ ] Only items matching filter criteria are processed
- [ ] Resources created in target system with correct field values
- [ ] Re-run does not create duplicates
- [ ] Error handler catches and logs failures gracefully

**Bad:**
- [ ] Scenario works (too vague)
- [ ] Data is correct (not specific)

### Make.com Test Documentation

Make.com scenarios don't have test files. All testing documentation goes in the spec itself:

```
workspace/clients/{client}/specs/automations/
├── a3-scenario-name.md      # Spec includes testing section
└── README.md                # Index of automations
```
