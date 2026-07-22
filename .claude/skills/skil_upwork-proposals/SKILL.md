# Upwork Proposal System

Structured playbook for creating Upwork proposals — cover letters and video walkthroughs that demonstrate competence through proof, not claims.

## When to Load

- Creating a new proposal (`/new-proposal`)
- Drafting an Upwork application
- Writing a proposal video script
- Reviewing/improving an existing proposal

## Modules

| Module | Load when... |
|--------|-------------|
| `POSITIONING.md` | Starting any proposal — sets the strategic frame |
| `PROPOSAL-TEMPLATES.md` | Writing the cover letter / application text |
| `VIDEO-SCRIPT.md` | Planning or scripting a Loom walkthrough |
| `SYSTEM-THINKING.md` | Analyzing a job post to design the proposed solution |

Load only what you need per task. For a full proposal (letter + video), load all four.

## Related System Components

- **`/new-proposal {prospect}`** — Creates the proposal page (platform landing page with pricing, timeline, phases)
- **`feedback_upwork_formatting.md`** — Upwork-specific text formatting (plain text, numbered sections, line breaks)
- **`/draft`** — For follow-up messages after proposal is sent
- **Live example** — `workspace/proposals/volabyg-lead-automation/video-script.md` (live reference)

## Workflow

```
1. Read job post
2. Load SYSTEM-THINKING → decompose into pipeline
3. Load POSITIONING → frame the approach
4. Load VIDEO-SCRIPT → record Loom walkthrough
5. Load PROPOSAL-TEMPLATES → write the cover letter
6. Submit application (video link + letter)
7. If progressed: /new-proposal → full proposal page with pricing
```

## Key Principle

> Clients don't buy services, hours, or skills. They buy certainty, clarity, and reduced risk.
> Your job: make them feel "this is already solved — I just need this person to execute it."