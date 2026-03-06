# Uplifted Consulting Automations

## Overview

| ID | Name | Stage | Trigger | Systems | Orchestrator |
|----|------|-------|---------|---------|--------------|
| A1 | [Positive Reply Notifier](pipeline/build/a1-positive-reply-notifier.md) | build | Webhook | Smartlead, OpenRouter, Slack | trigger-dev |

## Pipeline Stages

- **Spec**: Specification exists, no implementation yet
- **Build**: Implementation in progress
- **Test**: Testing in progress
- **Live**: Deployed and working in production

## Quick Links

- [Context Notes](../context/)
- [Reference Materials](../reference/)
- [Automations Code](../automations/)

## Adding New Automations

Use `/spec-creator` or `/build-automation uplifted-consulting` to create new automation specs.

Specs follow the standard format defined in `templates/specs/automation-spec.md`.

## Migration Note

- 2026-02-16: Migrated from `specs/automations/` to `specs/pipeline/{stage}/` structure
- Specs migrated from combined `automation-workflows.md` on 2026-01-09
