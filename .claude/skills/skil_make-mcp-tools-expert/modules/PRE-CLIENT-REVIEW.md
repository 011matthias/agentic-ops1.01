# Make.com Pre-Client Review Checklist

Run through this checklist before showing a Make.com project to a client for the first time.

## Scenario Hygiene
- [ ] All production scenarios use professional naming convention (`A1 — Name`, `A2 — Name`, etc.)
- [ ] No abandoned scenarios (0 executions, inactive) — delete them
- [ ] No orphaned webhooks (enabled but not attached to any scenario) — delete them
- [ ] No empty/unused data stores — delete them
- [ ] UTIL/diagnostic scenarios tagged with `ship: false` in infrastructure.yaml
- [ ] Error rate < 5% on all active scenarios (check execution history)

## Testing Verification
- [ ] Every scenario has been tested individually (check execution history for status:1)
- [ ] Edge cases tested: empty data, missing fields, API failures (if applicable)
- [ ] End-to-end pipeline tested: full lifecycle from trigger through all scenarios
- [ ] All test rows cleaned from tracking sheets/databases

## Documentation
- [ ] Client-facing overview doc matches current implementation
- [ ] Status transitions and lifecycle documented correctly
- [ ] Configurability section lists all adjustable settings with locations
- [ ] Specs updated to match implementation (moved to correct stage folder)
- [ ] infrastructure.yaml has full resource inventory with ship flags
- [ ] Doc freshness: client doc `Last updated` date is >= spec `updated` frontmatter date
- [ ] Doc version matches spec version (e.g., both say v2.0.0)
- [ ] Consolidated export generated (`/export-client-docs {client}`) and visually reviewed

## Blueprint Import Testing
- [ ] Run HANDOVER-FORMAT-CHECKER reconciler module on every handover blueprint
- [ ] Every handover blueprint tested via Make.com UI import (not just API deployment)
- [ ] Blueprint top-level keys: `flow`, `metadata`, `scheduling`, `interface` (omit `name`)
- [ ] Blueprint metadata includes `designer.orphans` and `scenario.dataloss` (required for UI import)
- [ ] Connections use `restore` metadata so clients are prompted to set their own
- [ ] No hardcoded resource IDs that belong to the dev account (spreadsheet IDs, data store IDs, etc.)
- [ ] Webhook modules use `hook: null` with `restore` label (not a dev hook ID) for handover blueprints

## Connections & Credentials
- [ ] All connections documented (dev vs production accounts)
- [ ] Handoff/notification emails point to correct recipients
- [ ] API keys stored securely (data store or connection, not hardcoded)
- [ ] Connection swap procedure documented for deployment day

## Webhook Configuration
- [ ] Webhook names are descriptive (not "My gateway-webhook webhook")
- [ ] Webhook URLs documented for external system integration
- [ ] Webhook `udt` status checked and documented

## Setup Wizard Verification
- [ ] Every Make.com UI reference verified against live UI (button locations, menu names, navigation paths)
- [ ] Walked through all wizard steps on a fresh Make.com account, following only the written instructions
- [ ] No step requires technical knowledge not explained in the wizard itself
- [ ] File import workflow tested (blueprint JSON files import correctly via file picker)
- [ ] Error scenarios tested: wrong webhook URL, expired API token, wrong Team ID
- [ ] Webhook payload format documented with exact field names for web developer handoff
