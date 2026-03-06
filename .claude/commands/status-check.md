---
description: Show automation status overview with automated verification
argument-hint: [client-name] [automation-id] [--verify]
---

# Automation Status Check

Display a comprehensive overview of automation statuses with optional automated verification against the actual codebase.

## Context

- Working directory: !`pwd`
- Client argument: $ARGUMENTS

## Parse Arguments

Parse $ARGUMENTS for:
1. **Client** (optional): e.g., `herbox`, `uplifted-consulting`. If omitted, detect from current path.
2. **Automation ID** (optional): e.g., `a6.1`, `a7`. Show specific automation only.
3. **`--verify`** (optional): Run automated verification against codebase

## Detect Client

If not in a client directory:
- Use `--client` argument if provided
- Detect from current path
- Ask user to specify

## Step 1: Load Status File

Read `workspace/clients/{client}/specs/automation-status.yaml`

If file doesn't exist:
- Check if client directory exists
- Check for specs in `specs/automations/`
- Offer to create status file from discovered specs

## Step 2: Display Status Overview

Show a formatted table:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ {CLIENT} AUTOMATION STATUS                                          {DATE} ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ STATUS FLOW:                                                             ║
║   planned → spec_created → implemented → tested_locally →                ║
║   deployed → tested_live → documentation_created → completed             ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
```

### Summary Statistics

```
┌──────────────────────────────────────────────────────────────────────────┐
│ OVERALL SUMMARY                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│ Total Automations:     {count}                                           │
│ Completed:             {completed_count} ({percentage}%)                 │
│ In Progress:           {in_progress_count}                               │
│ Not Started:           {not_started_count}                               │
│ Needs Fixes:           {needs_fixes_count}                               │
└──────────────────────────────────────────────────────────────────────────┘
```

### Status Breakdown

```
┌──────────────────────────────────────────────────────────────────────────┐
│ BY STATUS                                                                │
├──────────────────────────────────────────────────────────────────────────┤
│ spec_created:    {count} automations                                     │
│ implemented:     {count} automations                                     │
│ tested_locally:  {count} automations                                     │
│ deployed:        {count} automations                                     │
│ tested_live:     {count} automations                                     │
│ completed:       {count} automations                                     │
│ needs_fixes:     {count} automations                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

## Step 3: Display Automation Details

For each automation, show:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ [{ID}] {NAME}                                                            │
├──────────────────────────────────────────────────────────────────────────┤
│ Status:          {status}                                                │
│ Spec:            {spec_file}                                             │
│ Implementation:  {impl_file}                                             │
│ Trigger:         {trigger_type}                                          │
│ Systems:         {system_list}                                           │
│ Last Updated:    {date}                                                  │
│                                                                          │
│ {notes_preview}                                                          │
│                                                                          │
│ Next: {next_actions}                                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Color coding (if terminal supports):**
- `completed` / `tested_live`: Green ✓
- `tested_locally` / `deployed`: Yellow ~
- `implemented` / `spec_created`: Blue >
- `needs_fixes`: Red !

## Step 4: Automated Verification (if --verify flag)

When `--verify` is passed, perform automated checks:

### Check 1: Files Exist
- [ ] Spec file exists in `specs/automations/`
- [ ] Implementation exists in `app/automations/`
- [ ] Test file exists in `tests/` (if `tested_locally` or higher)

### Check 2: Deployment Status
- [ ] Railway project linked
- [ ] Deployment URL accessible
- [ ] Health endpoint responds

### Check 3: Registry Consistency
- [ ] Automation registered in `app/automations/__init__.py`
- [ ] Webhook route exists (if applicable)
- [ ] Correct trigger configuration

**Display verification results:**
```
┌──────────────────────────────────────────────────────────────────────────┐
│ VERIFICATION RESULTS                                                     │
├──────────────────────────────────────────────────────────────────────────┤
│ Files:           ✓ All files present                                     │
│ Deployment:      ~ Deployed to Railway (https://...)                     │
│ Registry:        ✗ {automation_id} not in __init__.py                     │
│                                                                          │
│ ⚠️  Status mismatch: YAML says "deployed" but not in registry            │
└──────────────────────────────────────────────────────────────────────────┘
```

## Step 5: Deployment Information

If deployment info exists in YAML:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ DEPLOYMENT                                                               │
├──────────────────────────────────────────────────────────────────────────┤
│ Railway App:     {app_name}                                             │
│ URL:             {url}                                                  │
│ Last Deployed:   {date}                                                 │
│                                                                          │
│ {deployment_notes}                                                       │
└──────────────────────────────────────────────────────────────────────────┘
```

## Step 6: Environment Variables

Show required environment variables:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ENVIRONMENT VARIABLES                                                    │
├──────────────────────────────────────────────────────────────────────────┤
│ Required:                                                                │
│   • AIRTABLE_API_KEY                                                     │
│   • AIRTABLE_BASE_ID                                                     │
│   • APIFY_API_TOKEN                                                      │
│                                                                          │
│ For {automation_id}:                                                     │
│   • LINKEDIN_COOKIES                                                     │
│   • LINKEDIN_USER_AGENT                                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Step 7: Next Actions

Display prioritized next actions from YAML:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ NEXT ACTIONS (Priority)                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│ HIGH:                                                                    │
│   → Deploy A6.2 to Railway (tested and ready)                           │
│   → Run local tests for A6.1                                             │
│                                                                          │
│ MEDIUM:                                                                  │
│   → Run local tests for A6.3 (Contact Enrichment)                       │
│   → Run local tests for A6.4 (Data Cleaning)                            │
│                                                                          │
│ LOW:                                                                     │
│   → Implement core operations (A1-A5)                                   │
│   → Generate documentation for completed automations                     │
└──────────────────────────────────────────────────────────────────────────┘
```

## Single Automation Mode

When `--automation ID` is specified, show detailed view:

```
╔════════════════════════════════════════════════════════════════════════════╗
║ {ID}: {NAME}                                                    {STATUS} ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ DESCRIPTION                                                              ║
║ {description}                                                            ║
║                                                                          ║
║ TRIGGER                                                                  ║
║   Type: {trigger_type}                                                   ║
║   Path:  {webhook_path or cron_schedule}                                 ║
║                                                                          ║
║ SYSTEMS                                                                  ║
║   • {system_1}                                                           ║
║   • {system_2}                                                           ║
║                                                                          ║
║ FILES                                                                    ║
║   Spec:           {spec_file} ✓                                         ║
║   Implementation:  {impl_file} ✓                                         ║
║   Tests:          {test_file} ✗ (not found)                             ║
║                                                                          ║
║ NOTES                                                                    ║
║ {notes}                                                                  ║
║                                                                          ║
║ HISTORY                                                                  ║
║   Created:  {created_date}                                               ║
║   Updated:  {updated_date}                                               ║
║                                                                          ║
║ NEXT STEPS                                                               ║
║   → {next_step_1}                                                        │
║   → {next_step_2}                                                        │
║                                                                          ║
╚════════════════════════════════════════════════════════════════════════════╝
```

## Suggested Commands

Based on status, suggest next commands:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SUGGESTED COMMANDS                                                       │
├──────────────────────────────────────────────────────────────────────────┤
│ /test a6.1           Run tests and mark as tested_locally                │
│ /verify-live a6.2    Verify production and mark as tested_live           │
│ /deploy herbox       Deploy to Railway                                    │
│ /build-automation    Create new automation from spec                     │
└──────────────────────────────────────────────────────────────────────────┘
```

## Error Handling

- **Status file not found**: Offer to create from discovered specs
- **YAML parsing error**: Show the error and line number
- **Client not found**: List available clients
- **Automation not found**: List available automation IDs
- **Verification fails**: Show which checks failed and why

## Examples

```bash
# Show all status for current client (auto-detect)
/status-check

# Show all status for specific client
/status-check herbox

# Show specific automation with verification
/status-check herbox a6.1 --verify

# Quick status check
/status-check outbound-consulting
```

## Notes

- This command provides visibility into automation status without making changes
- Use `--verify` to detect drift between YAML and actual state
- The status file should be the single source of truth
- Update status using `/test` and `/verify-live` commands
