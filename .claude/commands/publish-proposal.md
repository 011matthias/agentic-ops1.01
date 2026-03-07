---
description: Deploy proposal to production (merge branch to main)
argument-hint: <slug>
---

# Publish Proposal

Merges a proposal branch to main, triggering a Vercel production deployment. The proposal becomes accessible at `unpauseai.com/proposals/{slug}`.

## Context

- Working directory: !`pwd`
- Arguments: $ARGUMENTS (proposal slug)

## Prerequisites

If $ARGUMENTS is empty, list all open proposal branches and ask the user which one to publish:

```bash
git branch --list 'proposal/*'
```

## Step 1: Verify Proposal Exists

Check that `platform/src/content/proposals/{slug}.md` exists.
Check that the branch `proposal/{slug}` exists.

If the proposal status is already `sent` or `won`, warn the user and confirm they want to republish.

## Step 2: Verify Build

Run a build check to ensure the proposal renders correctly:

```bash
cd platform && npm run build
```

If the build fails, show the error and stop. Do not merge a broken build.

## Step 3: Update Status

If the proposal status is `draft`, ask the user if they want to update it to `sent`. If yes, update the frontmatter:

- Set `status: sent`
- Set `sent: "{YYYY-MM-DD}"` to today's date

Commit the status change to the proposal branch.

## Step 4: Merge to Main

```bash
git checkout main
git pull origin main
git merge proposal/{slug} --no-ff -m "Publish proposal: {slug}"
git push origin main
```

## Step 5: Cleanup

Ask the user if they want to delete the proposal branch:

```bash
git branch -d proposal/{slug}
git push origin --delete proposal/{slug}
```

## Step 6: Output Summary

```
Proposal published: {slug}

  Production URL: https://unpauseai.com/proposals/{slug}
  Status: {status}
  Merged to: main
  Branch: {deleted or kept}

The page will be live within ~60 seconds after Vercel deploys.
```

## Notes

- This merges to main — ensure the proposal content is reviewed
- Vercel automatically deploys on push to main
- The production URL requires DNS to be configured (unpauseai.com → Vercel)
- Until DNS is set up, the page is accessible at the Vercel project URL
