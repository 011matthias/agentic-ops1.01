/**
 * POST /api/agents/proposal — Trigger the Proposal Agent
 *
 * Creates an agent task record and dispatches to the Trigger.dev proposal-agent task.
 * Returns the task ID for status tracking.
 */

import { NextRequest, NextResponse } from "next/server"
import { tasks } from "@trigger.dev/sdk"
import { db } from "@/lib/db"
import { agentTasks } from "@/lib/schema"
import { eq } from "drizzle-orm"

export async function POST(request: NextRequest) {
  const body = await request.json()
  const { prospectName, jobPosting, track, sourceUrl } = body

  if (!prospectName || !jobPosting) {
    return NextResponse.json(
      { error: "prospectName and jobPosting are required" },
      { status: 400 }
    )
  }

  // Create the task record
  const [agentTask] = await db
    .insert(agentTasks)
    .values({
      agentType: "proposal",
      status: "pending",
      payload: JSON.stringify({ prospectName, jobPosting, track, sourceUrl }),
    })
    .returning()

  // Trigger the Trigger.dev task
  const run = await tasks.trigger("proposal-agent", {
    taskId: agentTask.id,
    prospectName,
    jobPosting,
    track,
    sourceUrl,
  })

  // Store the run ID
  await db
    .update(agentTasks)
    .set({ triggerRunId: run.id, updatedAt: new Date() })
    .where(eq(agentTasks.id, agentTask.id))

  return NextResponse.json({
    taskId: agentTask.id,
    runId: run.id,
    status: "dispatched",
  })
}
