import { NextRequest, NextResponse } from "next/server"
import { del } from "@vercel/blob"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { files } from "@/lib/schema"

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ fileId: string }> }
) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const { fileId } = await params

  const file = await db.query.files.findFirst({
    where: eq(files.id, fileId),
  })

  if (!file) {
    return NextResponse.json({ error: "File not found" }, { status: 404 })
  }

  // Delete from Vercel Blob
  await del(file.url)

  // Delete from database
  await db.delete(files).where(eq(files.id, fileId))

  return NextResponse.json({ ok: true })
}
