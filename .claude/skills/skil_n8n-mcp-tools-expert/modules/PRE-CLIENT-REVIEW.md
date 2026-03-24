# n8n Pre-Client Review Checklist

Run through before showing an n8n project to a client. Leaner than Make.com's checklist — n8n doesn't have blueprint format landmines or data store schema complexity.

---

## Workflow Hygiene

- [ ] All workflows use professional naming: `A{N} - {Description}` (e.g., `A1 - Enquiry Follow-Up`)
- [ ] No test/debug/abandoned workflows remain in client instance
- [ ] No workflows named "INSPECT", "TEST", "DEBUG", or "UTIL" unless `ship: false` in infrastructure.yaml
- [ ] Execution history cleaned — delete test executions that contain dummy data
- [ ] Workflow notes field populated with brief description of purpose

---

## Config Node Verification

Every workflow must have a Config Code node immediately after the trigger:

- [ ] Config node exists and is named exactly `Config`
- [ ] `testingMode: false` in all production workflows
- [ ] `limitItems: null` (no artificial caps on production)
- [ ] `dryRun: false`
- [ ] Each Config field has a descriptive comment
- [ ] No hardcoded test values remain (test emails, test IDs, etc.)

---

## Error Handling

- [ ] Error Trigger workflow exists for the project (catches errors from all workflows)
- [ ] Error Trigger sends notification to Slack/email with: workflow name, node name, error message
- [ ] `continueOnFail: true` on non-critical nodes (logging, notifications, analytics)
- [ ] Critical nodes (data writes, API calls) do NOT have `continueOnFail` — they should fail loudly
- [ ] No unhandled error paths — every branch either succeeds or triggers error handling

---

## Credentials

- [ ] All credentials use production accounts (not dev/test accounts)
- [ ] Credential names are documented in `context/credentials.md` or `infrastructure.yaml`
- [ ] No API keys hardcoded in Code nodes — use n8n credentials or `$env` variables
- [ ] OAuth credentials have sufficient scopes for all operations used
- [ ] Credential owner documented (whose Google account? whose Slack workspace?)

---

## Webhook Configuration

- [ ] Webhook paths use descriptive names (not default `/webhook` or `/webhook-test`)
- [ ] All webhook URLs documented in `context/webhook-urls.md`
- [ ] Webhook URLs communicated to external system operators (form providers, payment systems)
- [ ] Webhook authentication configured if the source supports it (API key in header, signature verification)

---

## Testing Verification

- [ ] Every workflow tested individually — execution history shows at least one successful run
- [ ] Edge cases tested: empty input, missing fields, API errors
- [ ] End-to-end pipeline tested (all workflows in sequence)
- [ ] No test data remains in downstream systems (sheets, databases, CRMs)
- [ ] Each spec's acceptance criteria verified against actual execution output

---

## Documentation

- [ ] Spec frontmatter updated: `stage: live`, `needs_fixes: false`
- [ ] `infrastructure.yaml` has complete workflow inventory with IDs
- [ ] Client context files complete: `context/README.md`, credentials, webhook URLs
- [ ] Client-facing docs match current implementation (if docs were generated)
- [ ] Any manual setup steps documented in a setup guide

---

## Final Activation

- [ ] All production workflows activated
- [ ] Webhook-triggered workflows tested with a real event after activation
- [ ] Scheduled workflows have correct cron expressions and timezone
- [ ] `infrastructure.yaml` `ship: true/false` flags are correct
- [ ] Dev-only workflows (UTIL, INSPECT, TEST) either deleted or marked `ship: false`
