---
description: Publish client automation to GitHub (triggers auto-deploy)
argument-hint: <client-name>
---

# Publish to GitHub

Push client automation code to their GitHub repository. Delegates to the `agnt_deployer` agent with publish-only mode.

## Prerequisites
- Client name from arguments. If missing, ask.
- Git subtree must be configured (see `/comd_client-handoff`).

## Execute

Invoke the `agnt_deployer` agent with the client name.

The agnt_deployer handles:
1. Stage and commit changes
2. Push to origin main
3. Push subtree to client's GitHub repo
4. Verify the push was successful

Note: This does NOT trigger a deployment. Use `/comd_deploy` for full deploy.
