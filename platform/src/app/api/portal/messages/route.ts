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

  const { body } = await request.json()
  if (!body?.trim()) {
    return NextResponse.json({ error: "Message body required" }, { status: 400 })
  }

  const client = await db.query.clients.findFirst({
    where: eq(clients.userId, session.user.id),
  })
  if (!client) {
    return NextResponse.json({ error: "No client record found" }, { status: 404 })
  }

  const [message] = await db
    .insert(messages)
    .values({
      clientId: client.id,
      authorId: session.user.id,
      authorRole: session.user.role ?? "client",
      body: body.trim(),
    })
    .returning()

  return NextResponse.json(message, { status: 201 })
}
