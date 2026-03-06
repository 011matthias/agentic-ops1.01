---
id: a3
name: AI Task Insights
type: automation
stage: build
orchestrator: trigger-dev
version: 1.0
created: 2026-03-05
updated: 2026-03-05
trigger:
  type: webhook
  description: On-demand — trigger from Trigger.dev dashboard or React app button
systems: [omniboard-api, openrouter]
last_changes: Initial spec
next_steps: Implement ai_insights.py using OpenRouter client, write TS wrapper
---

# A3: AI Task Insights

On-demand webhook task. Reads board state, sends to OpenRouter GPT-4o-mini, returns structured insights (priorities, blockers, next actions). Result visible in Trigger.dev dashboard.

## Payload Schema

```typescript
{
  projectId?: string;   // null = analyze all projects
  focus: "priorities" | "blockers" | "next-actions";  // default: "priorities"
}
```

## Flow

```
1. initialize  → validate OMNIBOARD_API_URL + OPENROUTER_API_KEY
2. fetch_data  → GET /api/board-state (filtered by projectId if provided)
               → serialize board as structured text:
                   "Project: Work (4 backlog, 2 todo, 3 in-progress, 1 completed)
                    Cards in backlog: Fix bug #102 [Priority: High], Write tests...
                    In progress: Deploy v2 [Deadline: 2026-03-06]
                    OVERDUE: Fix production crash [Deadline: 2026-03-04]"
3. transform   → build prompt based on focus:
                   priorities: "Rank tasks by urgency and importance. Output JSON."
                   blockers: "Identify tasks that might be blocked or blocking others."
                   next-actions: "Suggest the top 3 tasks to work on right now."
4. execute     → call OpenRouter (openai/gpt-4o-mini) with board summary + focus prompt
               → parse JSON response
5. finalize    → return result as task output (visible in Trigger.dev dashboard)
```

## AI Response Schema

```typescript
{
  insights: string[];        // 3-5 bullet points
  suggested_next: string[];  // top 3 task titles to work on
  risk_flags: string[];      // tasks at risk (overdue, blocked, etc.)
  summary: string;           // one-sentence board health summary
}
```

## OpenRouter Config

- Model: `openai/gpt-4o-mini`
- Uses `openrouter/client.py` from `python/clients/openrouter/`
- System prompt: "You are a productivity assistant analyzing a Kanban board..."

## Environment Variables

```
OMNIBOARD_API_URL=http://localhost:3001/api
OPENROUTER_API_KEY=...
```

## Acceptance Criteria

- [ ] Task can be triggered from Trigger.dev dashboard with a test payload
- [ ] Returns valid JSON matching the AI response schema
- [ ] Works for single project (projectId provided) and all projects (no projectId)
- [ ] Handles empty board gracefully (returns "No tasks found" insights)
- [ ] OpenRouter errors are caught and return error message (not crash)
