---
description: Publish client automation to GitHub (triggers auto-deploy)
argument-hint: <client-name>
---

# Publish to GitHub

Push client automation code to their GitHub repository. Delegates to the `deployer` agent with publish-only mode.

## Prerequisites
- Client name from arguments. If missing, ask.
- Git subtree must be configured (see `/client-handoff`).

## Execute

Invoke the `deployer` agent with the client name.

The deployer handles:
1. Stage and commit changes
2. Push to origin main
3. Push subtree to client's GitHub repo
4. Verify the push was successful

Note: This does NOT trigger a deployment. Use `/deploy` for full deploy.
