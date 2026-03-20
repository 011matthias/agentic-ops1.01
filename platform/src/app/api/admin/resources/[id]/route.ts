import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clientResources } from "@/lib/schema"

interface Params {
  params: Promise<{ id: string }>
}

export async function DELETE(_request: NextRequest, { params }: Params) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const { id } = await params

  const existing = await db.query.clientResources.findFirst({
    where: eq(clientResources.id, id),
  })

  if (!existing) {
    return NextResponse.json({ error: "Resource not found" }, { status: 404 })
  }

  await db.delete(clientResources).where(eq(clientResources.id, id))

  return new NextResponse(null, { status: 204 })
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

  const existing = await db.query.clientResources.findFirst({
    where: eq(clientResources.id, id),
  })

  if (!existing) {
    return NextResponse.json({ error: "Resource not found" }, { status: 404 })
  }

  const updates: Partial<typeof clientResources.$inferInsert> = {
    updatedAt: new Date(),
  }

  if (typeof body.published === "boolean") updates.published = body.published
  if (typeof body.sortOrder === "number") updates.sortOrder = body.sortOrder
  if (body.title?.trim()) updates.title = body.title.trim()
  if (body.description !== undefined) updates.description = body.description?.trim() ?? null
  if (body.url?.trim()) updates.url = body.url.trim()

  const [updated] = await db
    .update(clientResources)
    .set(updates)
    .where(eq(clientResources.id, id))
    .returning()

  return NextResponse.json(updated)
}
