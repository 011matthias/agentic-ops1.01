import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { users, clients, verificationTokens } from "@/lib/schema"
import { sendEmail } from "@/lib/email"

export async function POST(request: NextRequest) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }
  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const body = await request.json()
  const { email, companyName } = body as { email?: string; companyName?: string }

  if (!email?.trim() || !companyName?.trim()) {
    return NextResponse.json(
      { error: "email and companyName are required" },
      { status: 400 }
    )
  }

  const cleanEmail = email.trim().toLowerCase()
  const cleanCompany = companyName.trim()

  // Upsert user with client role
  const [existingUser] = await db
    .select()
    .from(users)
    .where(eq(users.email, cleanEmail))
    .limit(1)

  let userId: string

  if (existingUser) {
    userId = existingUser.id
    if (existingUser.role !== "client") {
      await db
        .update(users)
        .set({ role: "client", emailVerified: new Date() })
        .where(eq(users.id, userId))
    }
  } else {
    const [newUser] = await db
      .insert(users)
      .values({
        email: cleanEmail,
        role: "client",
        emailVerified: new Date(),
      })
      .returning({ id: users.id })
    userId = newUser.id
  }

  // Ensure client record exists
  const [existingClient] = await db
    .select()
    .from(clients)
    .where(eq(clients.userId, userId))
    .limit(1)

  if (!existingClient) {
    await db.insert(clients).values({
      userId,
      companyName: cleanCompany,
      status: "active",
    })
  }

  // Generate invite token (7-day expiry)
  const token = crypto.randomUUID()
  const expires = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)

  // Delete any existing verification tokens for this email first
  await db
    .delete(verificationTokens)
    .where(eq(verificationTokens.identifier, cleanEmail))

  await db.insert(verificationTokens).values({
    identifier: cleanEmail,
    token,
    expires,
  })

  // Build magic link URL
  const baseUrl = process.env.NEXTAUTH_URL ?? "https://unpauseai.com"
  const callbackUrl = encodeURIComponent("/portal")
  const inviteUrl = `${baseUrl}/api/auth/callback/resend?callbackUrl=${callbackUrl}&token=${token}&email=${encodeURIComponent(cleanEmail)}`

  // Send invite email
  await sendEmail({
    to: cleanEmail,
    subject: "You're invited to the UnpauseAI client portal",
    text: `Hi there,

Your client portal is ready. Click the link below to sign in — no password needed.

${inviteUrl}

This link expires in 7 days. If you have any questions, reply to this email.

The UnpauseAI Team`,
  })

  return NextResponse.json({ success: true })
}
