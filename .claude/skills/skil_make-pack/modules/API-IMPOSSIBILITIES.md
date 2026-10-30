# Make.com API Impossibilities

> **Check this list FIRST before attempting any Make.com API approach.**
> If your task touches anything in the "Cannot do via API" section, state the UI requirement in your FIRST response — do not attempt API workarounds first.

This is the primary cause of redundant-escalation friction. The 3-iteration limit in `behaviors.md` does not apply here — these operations have zero API path. Escalate on attempt 0.

---

## Cannot Do Via API — Escalate Immediately

These operations have no API workaround. Attempting them wastes time.

### OAuth Connection Setup & Testing

| Operation | Why API Fails | Action |
|-----------|--------------|--------|
| Create a new Gmail / Google Sheets / Google Calendar / Slack connection | OAuth requires browser-based consent flow | Tell user: "1 UI step required: create the connection in Make.com Settings → Connections" |
| Test that an OAuth connection is working | No API endpoint for connection health | Use `scenarios_run` with a minimal test scenario after UI binding |
| Execute a scenario that has an unbound OAuth module | Silently fails or returns misleading errors | Confirm binding in UI first (see POST-DEPLOYMENT-VERIFICATION.md) |

### Scenario Execution with Unbound Modules

Running `scenarios_run` on a scenario where any module has no bound connection **will not error cleanly** — it either silently skips the module or produces a generic failure. There is no API call that binds a connection to a module.

**Pattern that wasted 45 min (2026-03-15):** Trying to execute a Gmail-based email render test scenario via API. 6 approaches attempted before escalating. Correct approach: tell user up front that the 2-module Gmail scenario is a 1 UI step.

---

## Requires UI Rebinding BUT IS Deployable via API

These CAN be deployed via API — but need a UI rebinding step before they function. Document the required rebinding upfront (Step 6 of the make-pack Build Procedure).

See [POST-DEPLOYMENT-VERIFICATION.md](./POST-DEPLOYMENT-VERIFICATION.md) for the full rebinding checklist.

| Module Type | Deploy via API? | UI Step Required |
|-------------|----------------|-----------------|
| `datastore:*` | YES | Select data store in UI dropdown |
| `gmail:*` | YES | Select Gmail connection in UI |
| `google-sheets:*` | YES | Select Sheets connection in UI |
| `mysql:*` / any DB | YES | Select DB connection in UI |
| `scenario-service:StartSubscenario` | YES | Set interface via `scenarios_set_interface` + UI bind |

---

## Safe for Full API-Only Deployment (No UI Step)

| Module Type | Notes |
|-------------|-------|
| `http:ActionSendData` | URL-based, no connection |
| `builtin:*` (Router, Resume, Sleep, Feeder) | No external resources |
| `util:*`, `flow:*` | Scenario-internal only |
| `gateway:CustomWebhook` | Webhook URL auto-assigned |

---

## Decision Flow

```
Task involves Make.com scenario with Gmail/OAuth?
  └─ YES: State "1 UI step required" in first response.
          Deploy blueprint via API. Give user rebinding checklist. Done.
  └─ NO:  Proceed with API approach.
          Check POST-DEPLOYMENT-VERIFICATION.md after deployment.
```

---

## Integration

- Referenced from **make-pack/SKILL.md** Critical Rules (pre-build check)
- Companion to [POST-DEPLOYMENT-VERIFICATION.md](./POST-DEPLOYMENT-VERIFICATION.md) (what to do after deployment)
- Root cause documented in `docs/friction-register.md` (2026-03-15 redundant-escalation)
