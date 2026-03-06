---
id: {id}
name: {name}
status: planned
version: 1.0.0
trigger:
  type: {trigger_type}
  {trigger_config}
systems: [{systems}]
source:
  type: n8n
  workflow_name: {original_workflow_name}
  converted_at: {timestamp}
---

# {id_upper}: {name}

> Converted from N8N workflow: **{original_workflow_name}**

## Goal

**Problem:** {problem_description}

**Solution:** {solution_description}

**Business Value:** {business_value}

## Flow Diagram

```mermaid
{mermaid_diagram}
```

## API References

| System | Endpoints | Auth | Notes |
|--------|-----------|------|-------|
{api_references}

## Step Details

### 1. Initialize

- Load configuration and credentials
- Validate required environment variables
{init_details}

### 2. Fetch Data

{fetch_details}

### 3. Transform

{transform_details}

### 4. Execute

{execute_details}

### 5. Finalize

- Log execution summary
- Update status in database
{finalize_details}

## Edge Cases

| Scenario | Original N8N Handling | Python Implementation |
|----------|----------------------|----------------------|
{edge_cases}

## Testing

### Unit Tests

```python
# test_{id}.py

def test_transform_logic():
    """Test data transformation."""
    pass

def test_edge_case_handling():
    """Test error scenarios."""
    pass
```

### Integration Tests

```bash
# Dry run
uv run python -m app.automations.{id} --dry-run

# With test data
uv run python -m app.automations.{id} --test
```

### Acceptance Criteria

- [ ] Triggers correctly on {trigger_description}
- [ ] Processes data matching original N8N behavior
- [ ] Handles errors gracefully
- [ ] Logs all significant events

## Conversion Notes

### Original N8N Structure

| Step | N8N Node | Python Equivalent |
|------|----------|-------------------|
{node_mapping_table}

### Manual Review Required

{manual_review_items}

### Expressions Converted

| Original Expression | Python Code |
|---------------------|-------------|
{expression_conversions}

### Improvements Over N8N

- Type safety with Pydantic models
- Better error handling and logging
- Testable with dry-run support
- Version controlled specifications

---

*Converted from N8N on {timestamp}*
