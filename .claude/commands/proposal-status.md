---
description: Track all proposals — status, pipeline view, filters
argument-hint: [prospect-name | --status <status>]
---

# Proposal Status

Reads proposal frontmatter from all markdown files in `platform/src/content/proposals/` and displays a pipeline overview.

## Context

- Working directory: !`pwd`
- Arguments: $ARGUMENTS (optional filter)

## Step 1: Read All Proposals

Scan `platform/src/content/proposals/*.md` for all proposal files.

For each file, extract the YAML frontmatter fields:
- id, slug, prospect, project_title, status, created, sent, value_estimate, source, tags

Skip the sample proposal (`p000`).

## Step 2: Apply Filters

If $ARGUMENTS is provided:
- If it matches a prospect name (case-insensitive partial match), filter to that prospect
- If it starts with `--status`, filter to that status value (draft|sent|viewed|won|lost)
- If it's `--pipeline`, show the pipeline summary view (Step 3b)

## Step 3a: Display Table

Show all matching proposals sorted by created date (newest first):

```
Proposals ({count} total)

| ID   | Prospect     | Project Title              | Status | Source | Created    | Value       |
|------|-------------|----------------------------|--------|--------|------------|-------------|
| p001 | Acme Corp   | CRM Automation             | sent   | upwork | 2026-03-06 | $2,000-3,500|
| p002 | Beta Inc    | Email Pipeline              | draft  | direct | 2026-03-07 | $1,500-2,500|
```

## Step 3b: Pipeline Summary

If `--pipeline` flag or no proposals match a filter, show counts by status:

```
Pipeline Summary

  draft:  3
  sent:   2
  viewed: 1
  won:    0
  lost:   1
  ─────────
  total:  7

  Estimated pipeline value: $12,000-18,500 (sent + viewed)
  Conversion rate: 0/7 (0%)
```

## Step 4: Highlight Actionable Items

After the table, note any proposals that need attention:
- Proposals in `draft` status older than 3 days (stale drafts)
- Proposals in `sent` status older than 7 days (no response — consider follow-up)

```
Action Items:
  - p001 (Acme Corp): sent 5 days ago — consider follow-up
  - p003 (Gamma LLC): draft for 4 days — send or archive
```

## Notes

- This command is read-only — it doesn't modify any files
- To create a new proposal: /new-proposal
- To deploy a proposal to production: /publish-proposal
- Proposal files: platform/src/content/proposals/*.md
