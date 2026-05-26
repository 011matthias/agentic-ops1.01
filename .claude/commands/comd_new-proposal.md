---
description: Generate proposal site from Upwork job posting or project requirements. Two tracks -- video-led (Track 1) or full HTML site (Track 2). Ends with site deployed to production.
argument-hint: <prospect-name> "project description or pasted job posting"
---

# New Proposal

Creates a complete proposal package for a prospect: research context, cover letter, video script, and optionally a multi-page HTML site. Deploys to production. Ends with a live URL ready for Loom recording and Upwork submission.

## Context

- Working directory: !`pwd`
- Arguments: $ARGUMENTS

## Prerequisites

If $ARGUMENTS is empty, ask the user for:
1. Prospect/company name
2. Project description or pasted Upwork job posting URL/text

Parse arguments: first word or quoted phrase is the prospect name, remaining text is the project description or job posting.

## Skill Module Loading

Load these modules at the indicated steps. Do NOT load all at once -- load per step to keep context focused.

| Step | Modules to load |
|------|----------------|
| Step 1 | (none -- just slug/ID generation) |
| Step 2 | `POSITIONING.md`, `SYSTEM-THINKING.md` |
| Step 3 | (page inventory inlined in Step 3b below; research schema inlined in Step 2b) |
| Step 4 | `PROPOSAL-TEMPLATES.md`, `VIDEO-SCRIPT.md` + read `workspace/projects/platform/upwork-agency/profile-copy.md` for authority/bio content |

All modules are in `.claude/skills/skil_upwork-proposals/modules/`.

Also load `feedback_upwork_formatting.md` (memory) for cover letter text formatting rules, and `skil_client-comms/modules/STYLE-RULES.md` for all proposal text.

**The structural source of truth for proposal quality rules is `tools/validate-proposal.py`** — every check it runs is a rule. AGENT-CONSTRAINTS.md / PROPOSAL-CONFIG.md / PROFILE-CONTEXT.md were referenced by earlier versions of this command but never landed as files; the validator is the contract.

---

## Step 1: Generate Slug, ID, and Track

### Slug
Create a URL-safe slug from the prospect name + a short project keyword:
- Lowercase, kebab-case (e.g., `warme-wimmer-make-migration`)
- No special characters

### ID
Determine the next proposal ID by reading existing proposals in `platform/src/content/proposals/`:
- Pattern: `p{NNN}` (e.g., `p001`, `p015`)
- Skip the sample proposal (`p000`)

### Track
Determine the track based on job complexity:

| Track | When to use | Deliverables |
|-------|-------------|-------------|
| **Track 1** (Video-Led) | Simple jobs, < $200, clear scope, single-system | Cover letter (8-15 lines) + video script |
| **Track 2** (Full Site) | Complex jobs, > $200, multi-system, high competition | Cover letter (12-35 lines) + video script + HTML site + downloadable artifact |

Default to Track 2 for jobs > $200 or involving multiple integrations. State the track determination and reasoning.

---

## Step 2: Research Gate

**Load:** `POSITIONING.md`, `SYSTEM-THINKING.md`

### 2a: Read the Job Posting
- If user pasted text: analyze directly
- If user provided URL: fetch via WebFetch and analyze
- Extract: requirements, systems mentioned, budget, timeline, tone, pain points, must-haves vs nice-to-haves

### 2b: Populate Research Context
Fill the `research:` block (schema below):

```yaml
research:
  prospect_company: ""
  prospect_industry: ""
  prospect_location: ""
  prospect_contact: ""
  prospect_systems: []
  prospect_pain_points: []
  job_language_echoes: []      # Exact phrases from the posting
  location_advantage: ""        # Why Nico's location helps (or "")
  relevant_proof_points: []     # Cherry-picked from profile-copy.md
  budget_gap: ""                # Price mismatch (or "")
  profile_cherry_picks: []      # Reasoning for what to highlight
```

### 2c: Requirement Coverage Matrix
Create a matrix mapping every requirement from the job posting to where it will be addressed in the deliverables:

```
REQUIREMENT COVERAGE:
- [ ] {requirement 1} -> {cover letter / video script Beat X / site page}
- [ ] {requirement 2} -> {cover letter / video script Beat X / site page}
- [ ] {must-have 1} -> {explicit response location}
- [ ] {nice-to-have 1} -> {explicit response location}
Total: N requirements mapped
```

Every must-have and nice-to-have needs a response somewhere in deliverables. Gaps are visible before building.

### GATE: Research Completeness
Before proceeding, verify:
- [ ] `prospect_company` populated
- [ ] `prospect_pain_points` has 1+ items (Track 1) or 2+ items (Track 2)
- [ ] `prospect_systems` has 1+ items (Track 1) or all mentioned in posting (Track 2)
- [ ] `job_language_echoes` has 1+ phrases (Track 1) or 2+ phrases (Track 2)
- [ ] Requirement coverage matrix complete -- every requirement mapped to a deliverable

If any check fails, populate before continuing. Do not skip.

---

## Step 2.5: Project Details

Gather from user (or infer from job posting):
- **Project title** (clear, professional)
- **Source platform** (upwork | direct | linkedin | referral)
- **Source URL** (if applicable)
- **Estimated value range** (our price, not posted budget)
- **Estimated timeline**
- **Contact name** (if known, else "TBD")
- **Tags** (relevant technologies/domains)

---

## Step 3: Design Decisions

Present these decisions to the user for confirmation:

### 3a: Track Confirmation
Confirm Track 1 or Track 2 (determined in Step 1, user can override).

### 3b: Page Selection (Track 2 only) — Page Inventory
- **Required:** index.html, solution.html, timeline.html, investment.html, faq.html, onboarding.html
- **Conditional:** workflow.html (if visual demo adds value), gdpr.html (if EU/personal data)
- **Design decision:** brief.html (client understanding + market context -- include when problem interpretation is the differentiator)

State which pages will be built and why.

### 3c: Access Code
Generate access code: `{slug-year}` format (e.g., `fieldnation-2026`). Every Track 2 site gets an access code by default. Only skip if explicitly requested.

### 3d: Pricing
- State the posted budget (if any)
- State our proposed price
- If budget gap exists: note it -- cover letter must address it (enforced by validate-proposal.py)
- Pricing must be scope-based (phases/deliverables), never technology-based

### 3e: Artifact Type (Track 2 only)
What downloadable artifact to include:
- n8n workflow JSON (for n8n jobs)
- Make.com blueprint (for Make jobs)
- Audit checklist (for audit/review jobs)
- Project brief PDF (for complex projects)
- Other (specify)

### 3f: Cross-Pitch Framing (if applicable)
If applying to a non-automation job (e.g., GDPR review, marketing audit): lead with "I'm not applying as [X], I build automation tools" framing per `feedback_cross_pitch_framing.md`.

### GATE: User Confirms
Present all design decisions as a summary. Wait for user confirmation before building. This prevents building the wrong thing.

---

## Step 4: Generate Deliverables

**Load:** `PROPOSAL-TEMPLATES.md`, `VIDEO-SCRIPT.md` + read `workspace/projects/platform/upwork-agency/profile-copy.md` for authority content. The quality contract is `tools/validate-proposal.py` (run in Step 5 — fix all FAILs before deploy).

### 4a: Create Proposal Markdown
Create `platform/src/content/proposals/{slug}.md` with full frontmatter:

```yaml
---
id: {id}
slug: {slug}
prospect: {prospect name}
contact: {contact or "TBD"}
source: {source}
source_url: "{url or empty}"
project_title: "{title}"
status: draft
track: {1 or 2}
created: "{YYYY-MM-DD}"
sent: null
value_estimate: "{range}"
timeline: "{timeline}"
tags: [{tags}]
access_code: "{code or empty}"
deliverables:
  - cover-letter
  - video-script
  # Track 2 additions:
  - html-site
  - downloadable-artifact
research:
  # ... full research block from Step 2
---
```

### 4b: Cover Letter
Create `workspace/proposals/{slug}/cover-letter.md`:
- Track 1: Template 1 or 2 (8-15 lines, video link in first 3 lines)
- Track 2: Template 3 (12-35 lines, access code + URL in first 3 lines)
- Format: `.md` file, plain text only (no markdown formatting in body)
- Opening: "Hi there," -- never credentials, never "I hope this finds you well"
- Must include: video link (even placeholder `{VIDEO_LINK}` if not recorded yet)
- Must include: at least one `job_language_echo` from research
- Must include: budget gap acknowledgment if `research.budget_gap` is non-empty
- Sign-off: "Cheers, / Nico / UnpauseAI"
- See canonical format in `feedback_cover_letter_format.md`

### 4c: Video Script
Create `workspace/proposals/{slug}/video-script.md`:
- Format: `.md` file with `###` headers and `---` dividers
- Opening: "Hi there, Nico here."
- Structure: Beat 1 (Reframe) -> Authority -> Beat 2 (Structure/Demo) -> Beat 3+ -> Close
- Authority section: between Beat 1 and Beat 2, cherry-picked from profile-copy.md, max 20s/3 sentences
- SAY:/>> interleaving: max 2 consecutive SAY, max 3 consecutive >>
- Every `>> Nav:` / `>> Sidebar:` must match actual HTML headings (grep to verify after site build)
- Prospect name in Beat 1 and Close minimum
- Duration is dynamic: content determines length, don't pad or cut substance
- Must end with LOOM NOTES VERSION section (condensed bullet-point teleprompter version)
- If site has a live demo: walk through it in the video script

### 4d: HTML Site (Track 2 only)
Create `platform/public/clients/{slug}/` with all selected pages.

Every page must include:
- Navigation with all pages linked (absolute paths: `/clients/{slug}/`, `/clients/{slug}/solution`, etc.)
- Theme toggle (`data-theme` on `<html>`, `toggleTheme()`, localStorage key `{slug}-theme`)
- Access gate (full-screen overlay, validates against access code, localStorage key `{slug}-access`)
- Footer ("Prepared by UnpauseAI" + contact + year)
- Responsive design (hamburger menu on mobile < 768px)

Page-specific requirements (enforced by validate-proposal.py):
- **FAQ:** `<details>/<summary>` accordion, min 3 items
- **Onboarding:** All form inputs enabled (no `disabled`/`readonly`)
- **Investment:** Comparison table with 3+ rows, external links, source footnotes
- **Solution:** Min 1 visual + 3+ sections
- Prospect name in visible text on 3+ pages
- Prospect systems named specifically (not genericized)

### 4e: Downloadable Artifact (Track 2 only)
Create the artifact file in `platform/public/clients/{slug}/`:
- Naming: `{slug}-{description}.json` (or appropriate extension)
- Must be linked from a relevant page with a working download button

### Quality Checks (apply to ALL deliverables)
Pre-delivery self-check (validate-proposal.py enforces these structurally; this list is for awareness):
- Zero em dashes (all files)
- Zero banned AI phrases (all files)
- Contractions used ("I've" not "I have")
- Emoji limits (max 3 functional per HTML page, zero in letters/scripts)
- Pricing uses scope framing, support is retainer-inclusive
- Personalization injection complete (prospect name, systems, echoes, authority)

---

## Step 5: Validator Gate

Run validation before deploying:

```bash
uv run tools/validate-proposal.py {slug}
```

Track 2 additionally:
```bash
uv run tools/validate-html.py platform/public/clients/{slug}/
```

### GATE: Validation Results
- **FAIL items:** Fix all before proceeding. Re-run validator after fixes.
- **WARN items:** List for user awareness. Proceed unless user flags one.
- **PASS:** Continue to deploy.

### Video Script Cross-Check (Track 2)
After HTML site is built, verify all `>> Nav:` and `>> Sidebar:` directions in the video script match actual HTML headings. Grep the HTML files for each referenced heading. Fix mismatches.

---

## Step 6: Deploy to Production

Ship gate: entire chain as ONE action. Do not pause for confirmation.

```bash
# 1. Create branch
git checkout -b proposal/{slug}

# 2. Add all proposal files
git add platform/src/content/proposals/{slug}.md
git add platform/public/clients/{slug}/

# 3. Commit
git commit -m "Add proposal: {prospect name} {project title} ({id})"

# 4. Push
git push -u origin proposal/{slug}

# 5. Create PR
gh pr create --title "Add proposal: {prospect name} ({id})" --body "Track {N} proposal for {prospect}. Pages: {list}."

# 6. Merge
gh pr merge --squash --delete-branch

# 7. Force deploy (avoid CDN caching)
bash tools/vercel-force-deploy.sh
```

### Deploy Verification
After deploy:
1. WebFetch `https://unpauseai.com/clients/{slug}/` -- verify 200 response
2. Check access gate works (if configured)
3. Check key content present (prospect name, pricing, nav links)
4. State: "Verified: {URL} -- {checks passed}."

---

## Step 7: Output Summary

```
Proposal deployed: {id} — {prospect name}

  Track:      {1 or 2}
  Live URL:   https://unpauseai.com/clients/{slug}/
  Access:     {code} (or "none")
  Branch:     proposal/{slug} (merged to main)

Deliverables:
  - [x] Cover letter: workspace/proposals/{slug}/cover-letter.md
  - [x] Video script: workspace/proposals/{slug}/video-script.md
  - [x] HTML site: {N} pages (Track 2 only)
  - [x] Artifact: {filename} (Track 2 only)
  - [x] Proposal markdown: platform/src/content/proposals/{slug}.md

Next steps:
  1. Record Loom video (script: workspace/proposals/{slug}/video-script.md)
  2. Update cover letter with Loom link (replace {VIDEO_LINK} placeholder)
  3. Submit on Upwork with cover letter text
  4. Update proposal status: draft -> sent (in frontmatter)
  5. Run /proposal-retro {slug} to log friction and improve pipeline
```

## Notes

- Track 2 sites are self-contained HTML -- no build step needed, deployed as static files via Vercel
- Access codes are set per proposal, not globally
- The validator (`tools/validate-proposal.py`) is the source of truth for quality checks -- treat its FAILs as the contract
- Run `/proposal-retro {slug}` after submission to capture what went well and what to improve
- To check all proposals: `/proposal-status`
