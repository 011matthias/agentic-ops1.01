import { NextRequest, NextResponse } from "next/server"
import { eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clientResources, clients } from "@/lib/schema"

const VALID_TYPES = ["html_page", "video", "link", "file"] as const
const VALID_CATEGORIES = ["documentation", "setup", "guides", "videos"] as const

type ResourceType = (typeof VALID_TYPES)[number]
type ResourceCategory = (typeof VALID_CATEGORIES)[number]

export async function POST(request: NextRequest) {
  const session = await auth()
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  if (session.user.role !== "admin") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 })
  }

  const { clientId, title, description, type, url, category, projectId, sortOrder, published } =
    await request.json()

  if (!clientId) return NextResponse.json({ error: "clientId required" }, { status: 400 })
  if (!title?.trim()) return NextResponse.json({ error: "title required" }, { status: 400 })
  if (!type || !VALID_TYPES.includes(type as ResourceType)) {
    return NextResponse.json(
      { error: `type must be one of: ${VALID_TYPES.join(", ")}` },
      { status: 400 }
    )
  }
  if (!url?.trim()) return NextResponse.json({ error: "url required" }, { status: 400 })
  if (!category || !VALID_CATEGORIES.includes(category as ResourceCategory)) {
    return NextResponse.json(
      { error: `category must be one of: ${VALID_CATEGORIES.join(", ")}` },
      { status: 400 }
    )
  }

  const client = await db.query.clients.findFirst({ where: eq(clients.id, clientId) })
  if (!client) return NextResponse.json({ error: "Client not found" }, { status: 404 })

  const [resource] = await db
    .insert(clientResources)
    .values({
      clientId: client.id,
      title: title.trim(),
      description: description?.trim() ?? null,
      type: type as ResourceType,
      url: url.trim(),
      category: category as ResourceCategory,
      projectId: projectId ?? null,
      sortOrder: typeof sortOrder === "number" ? sortOrder : 0,
      published: typeof published === "boolean" ? published : false,
    })
    .returning()

  return NextResponse.json(resource, { status: 201 })
}
