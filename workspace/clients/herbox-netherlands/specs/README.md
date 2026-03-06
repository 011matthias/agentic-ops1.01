# Herbox Netherlands Automations

## Overview

| ID | Name | Stage | Trigger | Systems | Orchestrator |
|----|------|-------|---------|---------|--------------|
| a1 | Invoicing Automation | build | Airtable webhook (Leveringstatus → Verstuurd) | Airtable, TeamLeader Focus | n8n |

## Pipeline Stages

- **Spec**: Specification exists, no implementation yet
- **Build**: Implementation in progress
- **Test**: Testing in progress
- **Live**: Deployed and working in production

## Quick Links

- [Context Notes](../context/README.md)
- [Reference Materials](../reference/)

## Adding New Automations

Use `/spec-creator` to add new automations.

## Contacts

- **Patrick Bosma** — `patrick@herbox.nl` — Head of Benelux Operations (primary)
- **Koen Stielstra** — `koen@herbox.nl` — Technical contact

## Notes

- Orchestrator: **n8n** (HTTP Request nodes for TeamLeader Focus OAuth2)
- Contract signed Jan 30, 2026 — €1,500 — invoice paid Feb 10, 2026
- TeamLeader OAuth2 setup in progress (sandbox available, production access via Teams call with Patrick)
- Airtable view "Riccardo invoicing" created under "contracten of locaties" table
- Phase 2 (full delivery-cycle automation) is out of scope until Phase 1 is stable
