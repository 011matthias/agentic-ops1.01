import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { users, clients } from "@/lib/schema"
import { sendEmail } from "@/lib/email"

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }
  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const { userId } = await params
  const body = await request.json()
  const { companyName } = body as { role: string; companyName?: string }
  const validRoles = ["admin", "client", "prospect"] as const
  type Role = (typeof validRoles)[number]
  const role = body.role as Role

  if (!validRoles.includes(role)) {
    return NextResponse.json({ error: "Invalid role" }, { status: 400 })
  }

  // Prevent self-demotion
  if (userId === session.user.id && role !== "admin") {
    return NextResponse.json(
      { error: "Cannot change your own role" },
      { status: 400 }
    )
  }

  // Fetch the target user
  const [targetUser] = await db
    .select()
    .from(users)
    .where(eq(users.id, userId))
    .limit(1)

  if (!targetUser) {
    return NextResponse.json({ error: "User not found" }, { status: 404 })
  }

  // Promoting to client: require companyName, create client record
  if (role === "client" && targetUser.role !== "client") {
    if (!companyName?.trim()) {
      return NextResponse.json(
        { error: "companyName is required when promoting to client" },
        { status: 400 }
      )
    }

    // Check if client record already exists
    const [existingClient] = await db
      .select()
      .from(clients)
      .where(eq(clients.userId, userId))
      .limit(1)

    if (!existingClient) {
      await db.insert(clients).values({
        userId,
        companyName: companyName.trim(),
        status: "active",
      })
    }

    // Send welcome email
    if (targetUser.email) {
      await sendEmail({
        to: targetUser.email,
        subject: "Welcome to UnpauseAI",
        text: `Hi ${targetUser.name ?? "there"},\n\nYour account has been approved. You now have full access to the UnpauseAI client portal.\n\nSign in at: https://unpauseai.com/portal\n\nWelcome aboard!\n\nThe UnpauseAI Team`,
      })
    }
  }

  // Update role
  await db.update(users).set({ role }).where(eq(users.id, userId))

  return NextResponse.json({ success: true, role })
}
