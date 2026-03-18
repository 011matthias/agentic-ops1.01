import { NextRequest, NextResponse } from "next/server"
import { put } from "@vercel/blob"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clients, files } from "@/lib/schema"

export async function POST(request: NextRequest) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  if (session.user.role !== "client") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  // Scope to authenticated client
  const client = await db.query.clients.findFirst({
    where: eq(clients.userId, session.user.id),
  })

  if (!client) {
    return NextResponse.json({ error: "Client record not found" }, { status: 404 })
  }

  const formData = await request.formData()
  const file = formData.get("file") as File | null
  const projectId = (formData.get("projectId") as string | null) || null

  if (!file) {
    return NextResponse.json({ error: "File required" }, { status: 400 })
  }

  // Upload to Vercel Blob
  const blob = await put(file.name, file, { access: "public" })

  // Save to database
  const [record] = await db
    .insert(files)
    .values({
      clientId: client.id,
      projectId,
      uploadedBy: session.user.id,
      filename: file.name,
      url: blob.url,
      sizeBytes: file.size,
      mimeType: file.type || null,
    })
    .returning()

  return NextResponse.json(record, { status: 201 })
}
