import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { db } from "@/lib/db"
import { docComments } from "@/lib/schema"
import { eq } from "drizzle-orm"
import { cookieMatches, WIMMER_COOKIE } from "@/lib/wimmer-auth"
import { auth } from "@/lib/auth"

export const runtime = "nodejs"

const EDIT_WINDOW_MS = 24 * 60 * 60 * 1000 // 24h

async function passcodeOk(): Promise<boolean> {
  const secret = process.env.WIMMER_AUTH_SECRET?.trim()
  if (!secret) return false
  const cookie = (await cookies()).get(WIMMER_COOKIE)?.value
  return cookieMatches(cookie, secret)
}

export async function DELETE(
  _req: Request,
  ctx: { params: Promise<{ id: string }> }
) {
  if (!(await passcodeOk())) {
    return NextResponse.json({ error: "passcode_required" }, { status: 401 })
  }
  const session = await auth()
  const email = session?.user?.email
  const role = session?.user?.role
  if (!email) {
    return NextResponse.json({ error: "signin_required" }, { status: 401 })
  }
  const { id } = await ctx.params
  const rows = await db.select().from(docComments).where(eq(docComments.id, id))
  const row = rows[0]
  if (!row) {
    return NextResponse.json({ error: "not_found" }, { status: 404 })
  }
  const isAuthor = row.authorEmail.toLowerCase() === email.toLowerCase()
  const isAdmin = role === "admin"
  const withinWindow =
    new Date(row.createdAt).getTime() + EDIT_WINDOW_MS > Date.now()
  if (!(isAdmin || (isAuthor && withinWindow))) {
    return NextResponse.json({ error: "not_allowed" }, { status: 403 })
  }
  await db
    .update(docComments)
    .set({ deleted: true, editedAt: new Date() })
    .where(eq(docComments.id, id))
  return NextResponse.json({ ok: true })
}
