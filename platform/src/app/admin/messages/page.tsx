import { redirect } from "next/navigation"
import { isNull, count, max } from "drizzle-orm"
import { db } from "@/lib/db"
import { messages } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import Badge from "@/components/ui/Badge"
import Link from "next/link"

export const metadata = { title: "Messages — Admin" }

interface Props {
  searchParams: Promise<{ clientId?: string }>
}

export default async function AdminMessagesPage({ searchParams }: Props) {
  const { clientId } = await searchParams

  // If ?clientId= is present, redirect to the thread page
  if (clientId) {
    redirect(`/admin/messages/${clientId}`)
  }

  // Unread messages grouped by client
  const unreadByClient = await db
    .select({
      clientId: messages.clientId,
      unreadCount: count(messages.id),
      latestAt: max(messages.createdAt),
    })
    .from(messages)
    .where(isNull(messages.readAt))
    .groupBy(messages.clientId)

  // Fetch client records for the grouped clientIds
  const clientIds = unreadByClient.map((r) => r.clientId)

  const clientMap = new Map<string, { id: string; companyName: string; userId: string }>()
  if (clientIds.length > 0) {
    const clientRecords = await db.query.clients.findMany()
    for (const c of clientRecords) {
      clientMap.set(c.id, { id: c.id, companyName: c.companyName, userId: c.userId })
    }
  }

  // Fetch preview body for each group (most recent unread message body)
  const previews = new Map<string, string>()
  for (const group of unreadByClient) {
    const latestMsg = await db.query.messages.findFirst({
      where: (m, { and, isNull, eq }) =>
        and(eq(m.clientId, group.clientId), isNull(m.readAt)),
      orderBy: (m, { desc }) => [desc(m.createdAt)],
    })
    if (latestMsg) {
      previews.set(group.clientId, latestMsg.body)
    }
  }

  // Sort groups by latest message date desc
  const sorted = [...unreadByClient].sort((a, b) => {
    const aTime = a.latestAt ? a.latestAt.getTime() : 0
    const bTime = b.latestAt ? b.latestAt.getTime() : 0
    return bTime - aTime
  })

  const totalUnread = unreadByClient.reduce((sum, r) => sum + r.unreadCount, 0)

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <PageHeader
        title="Messages"
        subtitle={
          totalUnread > 0
            ? `${totalUnread} unread message${totalUnread !== 1 ? "s" : ""} across ${sorted.length} client${sorted.length !== 1 ? "s" : ""}`
            : "No unread messages"
        }
      />

      {sorted.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center rounded-2xl border border-dashed border-border p-12">
          <h3 className="text-lg font-semibold text-foreground mb-2">All caught up</h3>
          <p className="text-sm text-muted max-w-sm">
            No unread messages from any clients right now.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {sorted.map((group) => {
            const client = clientMap.get(group.clientId)
            const preview = previews.get(group.clientId) ?? ""
            const truncatedPreview =
              preview.length > 80 ? preview.slice(0, 80) + "…" : preview

            return (
              <div
                key={group.clientId}
                className="rounded-2xl border border-border bg-white dark:bg-gray-900 p-5 hover:border-accent/40 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-foreground">
                        {client?.companyName ?? group.clientId}
                      </span>
                      <Badge variant="warning">{group.unreadCount} unread</Badge>
                    </div>
                    {client && (
                      <p className="text-xs text-muted mb-2">{client.userId}</p>
                    )}
                    <p className="text-sm text-muted truncate">{truncatedPreview}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    {group.latestAt && (
                      <span className="text-xs text-muted">
                        {group.latestAt.toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "short",
                        })}
                      </span>
                    )}
                    <Link
                      href={`/admin/messages/${group.clientId}`}
                      className="text-sm text-accent hover:underline font-medium"
                    >
                      Open thread
                    </Link>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
