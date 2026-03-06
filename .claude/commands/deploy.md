---
description: Deploy client automation (Trigger.dev or Railway)
argument-hint: <client-name>
---

# Deploy Automation

Deploy a client's automation to production. Delegates to the `deployer` agent.

## Prerequisites
- Client name from arguments. If missing, ask.
- The deployer agent auto-detects the orchestrator (Trigger.dev or FastAPI/Railway) from `.claude/rules/detection.md`.

## Execute

Invoke the `deployer` agent with the client name.

The deployer handles:
1. Pre-deployment test gate (blocks on failure)
2. Git commit and push to main
3. Subtree push to client repo
4. Deploy via `npx trigger.dev deploy` (Trigger.dev) or `railway up` (FastAPI)
5. Post-deploy health verification
