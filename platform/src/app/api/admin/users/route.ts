import { NextResponse } from "next/server"
import { desc, eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { users, clients } from "@/lib/schema"

export async function GET() {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }
  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const allUsers = await db
    .select({
      id: users.id,
      name: users.name,
      email: users.email,
      role: users.role,
      createdAt: users.createdAt,
      clientId: clients.id,
      companyName: clients.companyName,
    })
    .from(users)
    .leftJoin(clients, eq(clients.userId, users.id))
    .orderBy(desc(users.createdAt))

  return NextResponse.json(allUsers)
}
