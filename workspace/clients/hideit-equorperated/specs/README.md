# HideItEquorperated — Work Items

## Overview

| ID | Name | Type | Stage | Trigger | Orchestrator |
|----|------|------|-------|---------|--------------|
| app1 | OmniBoard Frontend | app | build | manual | — |
| be1 | OmniBoard API | backend | build | http | hono |
| a1 | Deadline Scanner | automation | build | cron (hourly) | trigger-dev |
| a2 | Daily Digest | automation | build | cron (8am) | trigger-dev |
| a3 | AI Task Insights | automation | build | webhook | trigger-dev |

## Pipeline Stages

- **1-spec/** — Specifications, no implementation yet
- **2-build/** — Actively being implemented
- **3-test/** — Testing in progress
- **4-live/** — Deployed and working in production
- **_archive/** — Deprecated or superseded specs
- **_checklists/** — Testing checklists (per work item)
