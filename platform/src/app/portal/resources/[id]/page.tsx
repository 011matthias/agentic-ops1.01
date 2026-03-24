import { redirect, notFound } from "next/navigation"
import Link from "next/link"
import { and, eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clientResources, clients } from "@/lib/schema"

export const metadata = { title: "Resource" }

export default async function ResourceViewerPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const session = await auth()
  if (!session?.user?.id) redirect("/login")

  const { id } = await params

  const client = await db.query.clients.findFirst({
    where: eq(clients.userId, session.user.id),
  })
  if (!client) notFound()

  const resource = await db.query.clientResources.findFirst({
    where: and(
      eq(clientResources.id, id),
      eq(clientResources.clientId, client.id),
      eq(clientResources.published, true)
    ),
  })
  if (!resource) notFound()

  // Non-HTML resources redirect to their URL directly
  if (resource.type !== "html_page") {
    redirect(resource.url)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-0px)] sm:h-screen">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-white dark:bg-gray-900">
        <Link
          href="/portal/resources"
          className="text-sm text-muted hover:text-foreground transition-colors"
        >
          &larr; Resources
        </Link>
        <span className="text-border">|</span>
        <h1 className="text-sm font-medium text-foreground truncate">
          {resource.title}
        </h1>
      </div>
      <iframe
        src={resource.url}
        className="flex-1 w-full border-0"
        title={resource.title}
      />
    </div>
  )
}
