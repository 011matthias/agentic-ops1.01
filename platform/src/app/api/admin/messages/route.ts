import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clients, messages } from "@/lib/schema"

export async function POST(request: NextRequest) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const { body, clientId } = await request.json()

  if (!body?.trim()) {
    return NextResponse.json({ error: "Message body required" }, { status: 400 })
  }

  if (!clientId) {
    return NextResponse.json({ error: "clientId required" }, { status: 400 })
  }

  // Verify the client exists
  const client = await db.query.clients.findFirst({
    where: eq(clients.id, clientId),
  })

  if (!client) {
    return NextResponse.json({ error: "Client not found" }, { status: 404 })
  }

  const [message] = await db
    .insert(messages)
    .values({
      clientId: client.id,
      authorId: session.user.id,
      authorRole: "admin",
      body: body.trim(),
    })
    .returning()

  return NextResponse.json(message, { status: 201 })
}
