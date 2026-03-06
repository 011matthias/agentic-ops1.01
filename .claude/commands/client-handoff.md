---
description: Create GitHub repo and git subtree for client handoff
argument-hint: <client-name>
---

# Client Handoff

Creates a dedicated GitHub repository for a client and sets up git subtree for deployment.

## Context

- Working directory: !`pwd`
- Client name: $ARGUMENTS
- GitHub username: nickswagster
- Repo naming convention: `agentic-ops--{client-name}`

## Prerequisites

1. Client folder must exist: `workspace/clients/$ARGUMENTS/automations/`
2. GitHub CLI must be installed: `gh --version`
3. Must be authenticated: `gh auth status`

If any prerequisite fails, provide instructions and abort.

## Step 1: Verify Client Exists

Check if `workspace/clients/$ARGUMENTS/automations/` exists.

If not, suggest running `/new-client $ARGUMENTS` first.

## Step 2: Check Current Git State

Run `git status` to ensure:
- Working directory is clean (or ask user to commit/stash changes)
- Client automations folder exists and has content

## Step 3: Check if GitHub Repo Exists

```bash
gh repo view nickswagster/agentic-ops--$ARGUMENTS 2>/dev/null
```

| Result | Action |
|--------|--------|
| Repo exists | Skip to Step 5 (subtree setup) |
| Repo not found | Continue to Step 4 |

## Step 4: Create GitHub Repository

Create private repository:

```bash
gh repo create nickswagster/agentic-ops--$ARGUMENTS \
  --private \
  --description "Automation service for $ARGUMENTS" \
  --disable-wiki \
  --disable-issues
```

**Repository settings:**
- Private (client-specific code)
- No wiki (docs in dashboard)
- No issues (tracked in Agentic Ops)

## Step 5: Check Subtree Status

Determine if git subtree is already configured.

Check for existing remote:
```bash
git remote -v | grep "agentic-ops--$ARGUMENTS"
```

| Result | Action |
|--------|--------|
| Remote exists | Skip to Step 7 (push only) |
| No remote | Continue to Step 6 |

## Step 6: Add Git Subtree

Add the subtree for the client's automations folder:

```bash
# First, ensure the automations folder is committed
git add workspace/clients/$ARGUMENTS/automations/
git commit -m "Prepare $ARGUMENTS automations for subtree" --allow-empty

# Add subtree
git subtree add \
  --prefix=workspace/clients/$ARGUMENTS/automations \
  git@github.com:nickswagster/agentic-ops--$ARGUMENTS.git \
  main \
  --squash
```

If the repo is new/empty, we need to push first:

```bash
# Push initial content to new repo
git subtree push \
  --prefix=workspace/clients/$ARGUMENTS/automations \
  git@github.com:nickswagster/agentic-ops--$ARGUMENTS.git \
  main
```

## Step 7: Push to Client Repo

Push the automations subtree to GitHub:

```bash
git subtree push \
  --prefix=workspace/clients/$ARGUMENTS/automations \
  git@github.com:nickswagster/agentic-ops--$ARGUMENTS.git \
  main
```

## Step 8: Verify Push

Check that the repository has content:

```bash
gh repo view nickswagster/agentic-ops--$ARGUMENTS --json defaultBranchRef
```

Visit the repo to confirm files are present.

## Step 9: Detect Orchestrator and Configure Deployment

Check if the client uses Trigger.dev or FastAPI:

```bash
test -f workspace/clients/$ARGUMENTS/automations/trigger.config.ts && echo "trigger-dev" || echo "fastapi"
```

### If Trigger.dev:

Set up GitHub secrets for CI/CD deployment:

```bash
# Prompt user for their Trigger.dev access token
gh secret set TRIGGER_ACCESS_TOKEN \
  --repo nickswagster/agentic-ops--$ARGUMENTS \
  --body "<prompt-user-for-token>"
```

If self-hosted Trigger.dev, also set:
```bash
gh secret set TRIGGER_API_URL \
  --repo nickswagster/agentic-ops--$ARGUMENTS \
  --body "<trigger-dev-api-url>"
```

The `.github/workflows/deploy.yml` in the repo handles auto-deployment on push.

### If FastAPI:

Output instructions for connecting Railway:

```
## Railway Deployment

1. Create Railway project:
   railway init

2. Link to project:
   cd workspace/clients/$ARGUMENTS/automations
   railway link

3. Connect GitHub repo:
   - Go to Railway dashboard
   - Select project → Settings → GitHub
   - Connect: nickswagster/agentic-ops--$ARGUMENTS

4. Set environment variables:
   railway variables --set "KEY=value"

5. Deploy:
   railway up
```

## Output Summary

```
✓ GitHub repository created: nickswagster/agentic-ops--$ARGUMENTS
✓ Git subtree configured for workspace/clients/$ARGUMENTS/automations/

Repository: https://github.com/nickswagster/agentic-ops--$ARGUMENTS

Subtree commands for future updates:

  # Push changes to client repo
  git subtree push \
    --prefix=workspace/clients/$ARGUMENTS/automations \
    git@github.com:nickswagster/agentic-ops--$ARGUMENTS.git \
    main

  # Pull from client repo (rare)
  git subtree pull \
    --prefix=workspace/clients/$ARGUMENTS/automations \
    git@github.com:nickswagster/agentic-ops--$ARGUMENTS.git \
    main --squash

Next steps (Trigger.dev):
1. Ensure TRIGGER_ACCESS_TOKEN is set as GitHub secret
2. Push to main triggers auto-deploy via GitHub Actions
3. Monitor via Trigger.dev dashboard

Next steps (FastAPI):
1. Connect Railway to GitHub repo
2. Configure environment variables
3. Deploy with: /deploy $ARGUMENTS
```

## Error Handling

| Error | Resolution |
|-------|------------|
| gh not installed | `brew install gh` |
| gh not authenticated | `gh auth login` |
| Repo creation fails | Check GitHub permissions |
| Subtree push fails | Ensure local changes are committed |
| Branch mismatch | Check if repo uses `main` or `master` |

## Notes

- Subtree keeps client code in sync between workspaces
- **Trigger.dev clients:** GitHub Actions deploys on push to main via `npx trigger.dev deploy`
- **FastAPI clients:** Railway auto-deploys when GitHub repo is updated
- Client repos are private by default
- Use `/deploy` command for manual deployments
