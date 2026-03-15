import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { projects, milestones } from "@/lib/schema"

export async function POST(request: NextRequest) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const { projectId, title } = await request.json()

  if (!projectId) {
    return NextResponse.json({ error: "projectId required" }, { status: 400 })
  }

  if (!title?.trim()) {
    return NextResponse.json({ error: "title required" }, { status: 400 })
  }

  // Verify project exists
  const project = await db.query.projects.findFirst({
    where: eq(projects.id, projectId),
  })

  if (!project) {
    return NextResponse.json({ error: "Project not found" }, { status: 404 })
  }

  const [milestone] = await db
    .insert(milestones)
    .values({
      projectId,
      title: title.trim(),
      status: "pending",
    })
    .returning()

  return NextResponse.json(milestone, { status: 201 })
}
