/**
 * Proposal Agent — First member of the agent constellation
 *
 * Runs as a Trigger.dev task. Receives a job posting payload,
 * generates a complete proposal package autonomously, and deploys it.
 * Pauses at approval gates for user review.
 *
 * Flow: Job posting -> Research -> Design decisions (GATE) -> Build -> Validate -> Deploy (GATE)
 */

import { task, wait } from "@trigger.dev/sdk"
import { db } from "@/lib/db"
import { agentTasks, agentApprovals, agentLogs } from "@/lib/schema"
import { eq } from "drizzle-orm"
import { executeAgent } from "@/lib/agents/runner"
import { PROPOSAL_AGENT_PROMPT } from "@/lib/agents/prompts"

// Steps in the proposal pipeline
const STEPS = [
  "research",        // Parse job posting, populate research context
  "design",          // Track selection, page selection, pricing decisions
  "build",           // Generate all deliverables (cover letter, video script, HTML)
  "validate",        // Run validators — BLOCKING gate
  "deploy",          // Git branch, commit, push, PR, merge
] as const

type StepName = (typeof STEPS)[number]

// Steps requiring user approval before proceeding
const APPROVAL_GATES: StepName[] = ["design", "deploy"]

export const proposalAgent = task({
  id: "proposal-agent",
  retry: { maxAttempts: 1 },
  run: async (payload: {
    taskId: string
    prospectName: string
    jobPosting: string
    track?: 1 | 2
    sourceUrl?: string
  }) => {
    const { taskId, prospectName, jobPosting, track, sourceUrl } = payload

    // Mark task as running
    await db
      .update(agentTasks)
      .set({ status: "running", startedAt: new Date(), updatedAt: new Date() })
      .where(eq(agentTasks.id, taskId))

    await db.insert(agentLogs).values({
      taskId,
      level: "info",
      message: `Proposal Agent started for prospect: ${prospectName}`,
      metadata: JSON.stringify({ track, sourceUrl }),
    })

    // Execute each step sequentially
    for (const step of STEPS) {
      // Update current step
      await db
        .update(agentTasks)
        .set({ currentStep: step, updatedAt: new Date() })
        .where(eq(agentTasks.id, taskId))

      // Build step-specific prompt
      const prompt = buildStepPrompt(step, prospectName, jobPosting, taskId, track, sourceUrl)

      // Execute agent for this step
      const result = await executeAgent({
        prompt,
        cwd: process.cwd(),
        systemPrompt: PROPOSAL_AGENT_PROMPT,
        maxTurns: step === "build" ? 80 : 30,
        taskId,
      })

      // Log step result
      await db.insert(agentLogs).values({
        taskId,
        step,
        level: result.success ? "info" : "error",
        message: result.success
          ? `Step ${step} completed (${result.turns} turns, $${result.cost?.toFixed(4)})`
          : `Step ${step} failed: ${result.error}`,
        metadata: JSON.stringify({
          turns: result.turns,
          cost: result.cost,
          messageCount: result.messages.length,
        }),
      })

      // If step failed, mark task as failed and stop
      if (!result.success) {
        await db
          .update(agentTasks)
          .set({
            status: "failed",
            error: `Failed at step: ${step}. ${result.error}`,
            completedAt: new Date(),
            updatedAt: new Date(),
          })
          .where(eq(agentTasks.id, taskId))

        return { status: "failed", failedStep: step, error: result.error, taskId }
      }

      // Approval gate: pause and wait for user review
      if (APPROVAL_GATES.includes(step)) {
        const [approval] = await db
          .insert(agentApprovals)
          .values({ taskId, step, status: "pending" })
          .returning()

        await db
          .update(agentTasks)
          .set({ status: "waiting", updatedAt: new Date() })
          .where(eq(agentTasks.id, taskId))

        // Create waitpoint — $0 cost while waiting
        const token = await wait.createToken({
          idempotencyKey: `proposal-${taskId}-${step}`,
          timeout: "72h",
        })

        await db
          .update(agentApprovals)
          .set({ waitpointTokenId: token.id })
          .where(eq(agentApprovals.id, approval.id))

        await db.insert(agentLogs).values({
          taskId,
          step,
          level: "info",
          message: `Waiting for approval after step: ${step}`,
          metadata: JSON.stringify({ approvalId: approval.id, tokenId: token.id }),
        })

        // Pause execution until user approves via portal
        const approvalResult = await wait.forToken<{
          approved: boolean
          comments?: string
          reviewerId?: string
        }>(token.id)

        const approved = approvalResult.ok && approvalResult.output?.approved

        await db
          .update(agentApprovals)
          .set({
            status: approved ? "approved" : "rejected",
            comments: approvalResult.ok ? approvalResult.output?.comments ?? null : "Timed out",
            reviewerId: approvalResult.ok ? approvalResult.output?.reviewerId ?? null : null,
            resolvedAt: new Date(),
          })
          .where(eq(agentApprovals.id, approval.id))

        if (!approved) {
          await db
            .update(agentTasks)
            .set({
              status: "cancelled",
              error: `Rejected at approval gate: ${step}`,
              completedAt: new Date(),
              updatedAt: new Date(),
            })
            .where(eq(agentTasks.id, taskId))

          return {
            status: "cancelled",
            rejectedStep: step,
            comments: approvalResult.ok ? approvalResult.output?.comments : "Timed out",
            taskId,
          }
        }

        // Resume
        await db
          .update(agentTasks)
          .set({ status: "running", updatedAt: new Date() })
          .where(eq(agentTasks.id, taskId))
      }
    }

    // All steps complete
    await db
      .update(agentTasks)
      .set({ status: "completed", completedAt: new Date(), updatedAt: new Date() })
      .where(eq(agentTasks.id, taskId))

    return { status: "completed", taskId }
  },
})

function buildStepPrompt(
  step: StepName,
  prospectName: string,
  jobPosting: string,
  taskId: string,
  track?: 1 | 2,
  sourceUrl?: string
): string {
  const baseContext = `Task ID: ${taskId}
Prospect: ${prospectName}
${sourceUrl ? `Source URL: ${sourceUrl}` : ""}
${track ? `Track: ${track}` : "Track: determine from job complexity"}

Job Posting:
---
${jobPosting}
---`

  switch (step) {
    case "research":
      return `## Step: Research

${baseContext}

Execute the research phase of the proposal pipeline:

1. Generate a URL-safe slug from the prospect name + project keyword
2. Determine the next proposal ID by reading existing proposals in platform/src/content/proposals/
3. Check for duplicate proposals (files already exist for this slug) -- if found, log a warning
4. Parse the job posting: extract requirements, systems, budget, timeline, pain points
5. Load and read .claude/skills/skil_upwork-proposals/modules/POSITIONING.md and SYSTEM-THINKING.md
6. Populate the full research context (prospect_company, pain_points, systems, job_language_echoes, scope_estimate, competitor_research, value_hook)
7. Build a requirement coverage matrix mapping every requirement to a deliverable location
8. Call update_task_status with status="running" and currentStep="research"
9. Call log_event with the research summary including slug, ID, track determination, and requirement matrix

Output the complete research context so it can be reviewed.`

    case "design":
      return `## Step: Design Decisions

${baseContext}

Present design decisions based on the research:

1. Load .claude/skills/skil_upwork-proposals/modules/PROPOSAL-CONFIG.md
2. Confirm Track (1 or 2) with reasoning
3. For Track 2: select pages from the Page Inventory (required + conditional)
4. Pricing: calculate from scope_estimate (hours x $65/hr rate). Never match exact asking price.
5. Lead magnet selection (if applicable): downloadable artifact type
6. Call update_task_status with status="running" and currentStep="design"
7. Call log_event with all design decisions

Output a clear summary of all decisions. This step pauses for user approval.`

    case "build":
      return `## Step: Build Deliverables

${baseContext}

Generate all proposal deliverables:

1. Load all remaining modules: AGENT-CONSTRAINTS.md, PROFILE-CONTEXT.md, PROPOSAL-TEMPLATES.md, VIDEO-SCRIPT.md
2. Also load .claude/skills/skil_client-comms/modules/STYLE-RULES.md for text formatting
3. Create proposal frontmatter: platform/src/content/proposals/{slug}.md
4. Create cover letter: workspace/proposals/{slug}/cover-letter.md
   - Format: .md file, "Hi there,", URL + access code + Loom link placeholder, dash bullets, "Cheers, / Nico / UnpauseAI"
   - MUST include video link (even placeholder)
   - No em dashes. No numbered lists.
5. Create video script: workspace/proposals/{slug}/demo-video-script.md (if applicable)
   - .md with ### headers + --- dividers
   - >> directions reference sidebar labels
   - Opens on job posting, pitch-first, nav-follows-scroll
6. For Track 2: Create HTML site pages in platform/public/clients/{slug}/
   - Use existing proposal sites as templates (read an existing one in platform/public/clients/)
   - Sidebar nav required for video workflow
   - Dark/light mode toggle, copy buttons on code blocks
7. For Track 2: Create downloadable artifact (JSON blueprint, template, etc.)
8. Call update_task_status with status="running" and currentStep="build"
9. Call log_event with list of all files created

Build everything. Do not cut corners.`

    case "validate":
      return `## Step: Validate (BLOCKING GATE)

${baseContext}

Run structural validation on all deliverables:

1. Run: uv run tools/validate-proposal.py {slug}
   - This MUST pass. All FAIL items must be fixed before proceeding.
   - WARN items should be fixed if possible.
2. For Track 2: Run: uv run tools/validate-html.py platform/public/clients/{slug}/
   - All failures must be fixed.
3. Verify manually:
   - Cover letter has video link (even placeholder)
   - No em dashes in any file
   - No known client names in public HTML
   - Price is not exact asking price
   - Every requirement from the matrix has a response
4. Call update_task_status with status="running" and currentStep="validate"
5. Call log_event with validator results

If validation fails, fix the issues and re-run. Max 3 attempts. If still failing after 3, escalate.`

    case "deploy":
      return `## Step: Deploy to Production

${baseContext}

Deploy the proposal to production:

1. Create git branch: proposal/{slug}
2. Stage all proposal files (platform/src/content/proposals/{slug}.md, platform/public/clients/{slug}/, workspace/proposals/{slug}/)
3. Commit with descriptive message
4. Push branch and create PR
5. Merge PR to main
6. Run: bash tools/vercel-force-deploy.sh (bypass CDN cache)
7. Verify deployment: WebFetch the deployed URL, check 200 status and key content
8. Call update_task_status with status="running" and currentStep="deploy"
9. Call log_event with deployed URL and verification results

This step pauses for user approval before executing. Once approved, execute the full deploy chain as ONE action (no pausing mid-chain).`
  }
}
