---
description: Deploy project automation (Trigger.dev or Railway)
argument-hint: <project-name>
---

# Deploy Automation

Deploy a project's automation to production. Delegates to the `agnt_deployer` agent.

## Prerequisites
- Project name from arguments. If missing, ask.
- Resolve project directory — check `workspace/clients/{project}/` first, then `workspace/projects/{project}/`.
- The agnt_deployer agent auto-detects the orchestrator from `infrastructure.yaml` and the automations folder structure.

## Execute

Invoke the `agnt_deployer` agent with the project name.

The agnt_deployer handles:
1. Pre-deployment test gate (blocks on failure)
2. Git commit and push to main
3. Subtree push to client repo
4. Deploy via `npx trigger.dev deploy` (Trigger.dev) or `railway up` (FastAPI)
5. Post-deploy health verification
