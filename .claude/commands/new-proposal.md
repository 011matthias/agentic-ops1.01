---
description: Generate proposal landing page from project requirements
argument-hint: <prospect-name> "project description"
---

# New Proposal

Creates a proposal landing page for a prospect. Generates a markdown file with frontmatter, creates a feature branch, and pushes to trigger a Vercel preview deployment.

## Context

- Working directory: !`pwd`
- Arguments: $ARGUMENTS

## Prerequisites

If $ARGUMENTS is empty, ask the user for:
1. Prospect/company name
2. Project description or pasted Upwork requirements

Parse arguments: first word or quoted phrase is the prospect name, remaining text is the project description.

## Step 1: Generate Slug and ID

Create a URL-safe slug from the prospect name + a short project keyword:
- Lowercase, kebab-case (e.g., `acme-corp-crm-automation`)
- No special characters

Determine the next proposal ID by reading existing proposals in `platform/src/content/proposals/`:
- Pattern: `p{NNN}` (e.g., `p001`, `p002`)
- If no proposals exist, start at `p001`
- Skip the sample proposal (`p000`)

## Step 2: Ask for Project Details

If the user only provided a short description, ask for more context. Offer to paste the full Upwork job posting or project requirements.

Gather at minimum:
- Project title (clear, professional)
- Source platform (upwork | direct | linkedin | referral)
- Source URL (if applicable)
- Estimated value range
- Estimated timeline
- Contact name (if known)
- Tags (relevant technologies/domains)

## Step 3: Generate Proposal Markdown

Create `platform/src/content/proposals/{slug}.md` with:

```yaml
---
id: {id}
slug: {slug}
prospect: {prospect name}
contact: {contact name or "TBD"}
source: {source}
source_url: "{url or empty}"
project_title: "{title}"
status: draft
created: "{YYYY-MM-DD}"
sent: null
value_estimate: "{range}"
timeline: "{timeline}"
tags: [{tags}]
---
```

Generate the proposal body with these sections based on the project requirements:

1. **What We Understood** — Restate the prospect's needs in our own words. Show we listened. Reference specific pain points from their requirements.

2. **Our Proposed Solution** — Concrete approach, not vague promises. Mention specific technologies/platforms. Use bullet points for clarity.

3. **Timeline & Milestones** — Weekly breakdown with deliverables per week. Realistic, not optimistic.

4. **Investment** — Price range with what's included. List deliverables. Mention post-launch support.

5. **About UnpausAI** — 3 sentences max. Focus on relevant experience. No fluff.

Write in a professional but direct tone. No buzzwords. The prospect should feel like we understand their problem and have a clear plan.

## Step 4: Create Branch and Commit

```bash
git checkout -b proposal/{slug}
git add platform/src/content/proposals/{slug}.md
git commit -m "Add proposal: {prospect name} — {project title}"
git push -u origin proposal/{slug}
```

## Step 5: Output Summary

Report to user:

```
Proposal created: platform/src/content/proposals/{slug}.md

  ID:       {id}
  Prospect: {prospect name}
  Status:   draft
  Branch:   proposal/{slug}

Preview URL (after Vercel builds):
  https://{branch-slug}-agentic-ops.vercel.app/proposals/{slug}

Production URL (after merge to main):
  https://unpausai.com/proposals/{slug}

Next steps:
  1. Review the proposal content and edit if needed
  2. Run `npm run dev` in platform/ to preview locally
  3. When ready, update status to "sent" in frontmatter
  4. Use /publish-proposal {slug} to merge to main
```

## Notes

- The proposal is a markdown file — edit it directly for refinements
- Vercel creates a preview deployment for every branch push
- The sample proposal (`p000`) is for testing — don't send it to prospects
- To check all proposals: /proposal-status
