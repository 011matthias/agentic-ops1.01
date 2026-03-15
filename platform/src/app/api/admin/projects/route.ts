import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clients, projects } from "@/lib/schema"

export async function POST(request: NextRequest) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const { clientId, name, orchestrator, targetDate } = await request.json()

  if (!clientId) {
    return NextResponse.json({ error: "clientId required" }, { status: 400 })
  }

  if (!name?.trim()) {
    return NextResponse.json({ error: "Project name required" }, { status: 400 })
  }

  // Verify client exists
  const client = await db.query.clients.findFirst({
    where: eq(clients.id, clientId),
  })

  if (!client) {
    return NextResponse.json({ error: "Client not found" }, { status: 404 })
  }

  // Validate orchestrator if provided
  const validOrchestrators = ["make", "n8n", "trigger-dev", "fastapi"] as const
  type OrchestratorType = (typeof validOrchestrators)[number]

  const resolvedOrchestrator: OrchestratorType | null =
    orchestrator && validOrchestrators.includes(orchestrator as OrchestratorType)
      ? (orchestrator as OrchestratorType)
      : null

  const [project] = await db
    .insert(projects)
    .values({
      clientId: client.id,
      name: name.trim(),
      orchestrator: resolvedOrchestrator ?? undefined,
      targetDate: targetDate ? new Date(targetDate) : undefined,
      status: "active",
    })
    .returning()

  return NextResponse.json(project, { status: 201 })
}
