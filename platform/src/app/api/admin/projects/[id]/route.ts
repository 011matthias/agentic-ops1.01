import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { projects } from "@/lib/schema"

type ProjectStatus = "active" | "paused" | "complete"

const VALID_STATUSES: ProjectStatus[] = ["active", "paused", "complete"]

interface Params {
  params: Promise<{ id: string }>
}

export async function PATCH(request: NextRequest, { params }: Params) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const { id } = await params
  const body = await request.json()
  const { status, targetDate } = body

  if (status !== undefined && !VALID_STATUSES.includes(status as ProjectStatus)) {
    return NextResponse.json(
      { error: `status must be one of: ${VALID_STATUSES.join(", ")}` },
      { status: 400 }
    )
  }

  const existing = await db.query.projects.findFirst({
    where: eq(projects.id, id),
  })

  if (!existing) {
    return NextResponse.json({ error: "Project not found" }, { status: 404 })
  }

  const updateValues: Partial<{
    status: ProjectStatus
    targetDate: Date | null
  }> = {}

  if (status !== undefined) {
    updateValues.status = status as ProjectStatus
  }

  if (targetDate !== undefined) {
    updateValues.targetDate = targetDate ? new Date(targetDate) : null
  }

  if (Object.keys(updateValues).length === 0) {
    return NextResponse.json(
      { error: "No valid fields to update" },
      { status: 400 }
    )
  }

  const [updated] = await db
    .update(projects)
    .set(updateValues)
    .where(eq(projects.id, id))
    .returning({ id: projects.id, status: projects.status })

  return NextResponse.json(updated)
}
