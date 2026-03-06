# Testing Checklist Generator

This script generates an actionable testing checklist for any automation.

## Process

### Step 1: Identify Files

```
Automation: workspace/clients/{client}/automations/app/automations/{automation_id}.py
Spec: workspace/clients/{client}/specs/automations/{spec_id}.md
Tests: workspace/clients/{client}/automations/tests/test_{automation_id}.py
Config: workspace/clients/{client}/automations/app/config.py
```

### Step 2: Extract Environment Variables

Search the automation code for:
- `settings.{variable_name}`
- `os.getenv("VAR_NAME")`
- `os.environ["VAR_NAME"]`

For each env var found:
- Check if defined in `config.py`
- Note if required or optional
- Add to Pre-Test Setup section

### Step 3: Determine Test Commands

From the automation code:
- Check for `if __name__ == "__main__"` block
- Look for `--dry-run` flag support
- Note the module path: `app.automations.{automation_id}`

Generate commands:
```bash
cd workspace/clients/{client}/automations
uv run python -m app.automations.{automation_id} --dry-run
```

### Step 4: Check Test Coverage

Read the test file if it exists:
- List test functions found
- Note any missing test scenarios
- Check if acceptance criteria are covered

### Step 5: Read Spec for Context

From the spec file:
- Trigger type (cron/webhook) - affects how to test
- External systems involved - need test accounts?
- Acceptance criteria - what to verify
- Special test data needs

### Step 6: Generate Checklist

Use this template:

```markdown
# Testing Checklist: {Automation Name}

**Automation ID:** {automation_id}
**Client:** {client}
**Generated:** {date}

---

## Pre-Test Setup

### Environment Variables

Set these in your local `.env` or Railway:

| Variable | Required | Description |
|----------|----------|-------------|
| {VAR_1} | Yes | {description} |
| {VAR_2} | No | {description} |

- [ ] All environment variables configured

### Test Data

- [ ] Create test records in {system}
  - [ ] {specific test data needed}
  - [ ] {specific test data needed}

### Dependencies

```bash
cd workspace/clients/{client}/automations
uv sync
```

- [ ] Dependencies installed

---

## Local Testing (Dry Run)

```bash
cd workspace/clients/{client}/automations
uv run python -m app.automations.{automation_id} --dry-run
```

**What to look for:**
- {expected output from dry-run}
- No errors or exceptions
- Correct number of items reported

- [ ] Dry-run completes without errors
- [ ] Output shows expected behavior
- [ ] No unintended side effects

---

## Live Test (Sandbox/Dev)

```bash
cd workspace/clients/{client}/automations
uv run python -m app.automations.{automation_id}
```

**Verify in {system}:**
- [ ] Records created/updated correctly
- [ ] {field_name} has correct value
- [ ] {field_name} has correct value

**Test error handling:**
- [ ] Try invalid test data - errors logged gracefully
- [ ] Check logs for error messages

---

## Test Suite

```bash
cd workspace/clients/{client}/automations
uv run pytest tests/test_{automation_id}.py -v
```

**Coverage:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Acceptance criteria verified

---

## Deployment

### Commit Changes

```bash
git add workspace/clients/{client}/automations
git commit -m "Implement {automation_id}: {name}"
```

- [ ] Changes committed

### Push to Railway

```bash
cd workspace/clients/{client}/automations
railway up
```

- [ ] Deployment successful
- [ ] Environment variables set in Railway dashboard
  - Navigate to: https://railway.app/project/{project}/variables
  - Set: {VAR_1}, {VAR_2}, ...

---

## Post-Deployment Verification

### Check Logs

```bash
cd workspace/clients/{client}/automations
railway logs
```

- [ ] No error messages in logs
- [ ] Automation runs on schedule/webhook

### Verify in Systems

- [ ] {System} records are being created/updated
- [ ] Dashboard shows execution in logs
- [ ] {specific verification from acceptance criteria}

### Monitoring

- [ ] Set up alerts for failures (if applicable)
- [ ] Monitor for 24 hours

---

## Acceptance Criteria

From spec: {spec_file}

- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

---

## Notes

{Any additional notes about testing this automation}
```

### Step 7: Save Checklist

Save the checklist to one of:
- `workspace/clients/{client}/specs/testing/{automation_id}-checklist.md`
- Output to console for immediate use
- Attach to existing spec file

### Step 8: Report to User

Provide:
- Checklist location/content
- Quick start: "First, set these env vars..."
- Next command to run
