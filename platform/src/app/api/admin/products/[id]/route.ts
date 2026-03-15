import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { products } from "@/lib/schema"

interface PatchBody {
  name?: string
  priceUsd?: number
  active?: boolean
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = await auth()

  if (!session?.user || session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const { id } = await params

  let body: PatchBody
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 })
  }

  const updates: Partial<{ name: string; priceUsd: number; active: boolean }> = {}

  if (body.name !== undefined) {
    if (typeof body.name !== "string" || !body.name.trim()) {
      return NextResponse.json({ error: "name must be a non-empty string" }, { status: 400 })
    }
    updates.name = body.name.trim()
  }

  if (body.priceUsd !== undefined) {
    if (typeof body.priceUsd !== "number" || !Number.isInteger(body.priceUsd) || body.priceUsd < 0) {
      return NextResponse.json({ error: "priceUsd must be a non-negative integer (cents)" }, { status: 400 })
    }
    updates.priceUsd = body.priceUsd
  }

  if (body.active !== undefined) {
    if (typeof body.active !== "boolean") {
      return NextResponse.json({ error: "active must be a boolean" }, { status: 400 })
    }
    updates.active = body.active
  }

  if (Object.keys(updates).length === 0) {
    return NextResponse.json({ error: "No valid fields to update" }, { status: 400 })
  }

  const [updated] = await db
    .update(products)
    .set(updates)
    .where(eq(products.id, id))
    .returning()

  if (!updated) {
    return NextResponse.json({ error: "Product not found" }, { status: 404 })
  }

  return NextResponse.json(updated)
}
