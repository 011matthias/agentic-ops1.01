import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { milestones } from "@/lib/schema"

type MilestoneStatus = "pending" | "in-progress" | "done"

const VALID_STATUSES: MilestoneStatus[] = ["pending", "in-progress", "done"]

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
  const { status } = await request.json()

  if (!status || !VALID_STATUSES.includes(status as MilestoneStatus)) {
    return NextResponse.json(
      { error: `status must be one of: ${VALID_STATUSES.join(", ")}` },
      { status: 400 }
    )
  }

  const existing = await db.query.milestones.findFirst({
    where: eq(milestones.id, id),
  })

  if (!existing) {
    return NextResponse.json({ error: "Milestone not found" }, { status: 404 })
  }

  const completedAt = status === "done" ? new Date() : null

  const [updated] = await db
    .update(milestones)
    .set({
      status: status as MilestoneStatus,
      completedAt,
    })
    .where(eq(milestones.id, id))
    .returning({ id: milestones.id, status: milestones.status })

  return NextResponse.json(updated)
}
