# Gathering Testing Information

When generating a testing checklist, gather the following information:

## 1. Identify Automation

- Client name (from `workspace/clients/` folder)
- Automation ID (from user or file name)
- Automation file location

## 2. Analyze Code

Read the automation file and extract:
- Environment variables used (search for `settings.`, `os.getenv`, `environ`)
- External API calls (which systems it integrates with)
- Main entry point (how to run it)
- Dry-run support

## 3. Read Spec

Find and read the spec file:
- Location: `workspace/clients/{client}/specs/automations/{id}.md`
- Extract: Goal, trigger type, acceptance criteria
- Note any special test data requirements

## 4. Check Tests

Look for test files:
- `tests/test_{automation_id}.py`
- Check what test cases exist
- Note coverage gaps

## 5. Generate Checklist

Create the checklist in this order:
1. Pre-Test Setup (env vars, test data, deps)
2. Local Testing (dry-run command)
3. Live Test (sandbox/dev)
4. Deployment (git + railway)
5. Post-Deployment (verification steps)
