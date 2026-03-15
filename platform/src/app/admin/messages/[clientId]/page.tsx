import { redirect } from "next/navigation"
import { and, isNull, eq } from "drizzle-orm"
import { db } from "@/lib/db"
import { clients, messages } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import MessageThread from "@/components/portal/MessageThread"

export const metadata = { title: "Thread — Admin" }

interface Props {
  params: Promise<{ clientId: string }>
}

export default async function AdminThreadPage({ params }: Props) {
  const { clientId } = await params

  // Fetch client record
  const client = await db.query.clients.findFirst({
    where: eq(clients.id, clientId),
  })

  if (!client) {
    redirect("/admin/messages")
  }

  // Mark all unread messages for this client as read
  await db
    .update(messages)
    .set({ readAt: new Date() })
    .where(and(eq(messages.clientId, clientId), isNull(messages.readAt)))

  // Fetch all messages for this client ordered oldest first
  const messageList = await db.query.messages.findMany({
    where: eq(messages.clientId, clientId),
    orderBy: (m, { asc }) => [asc(m.createdAt)],
  })

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <div className="mb-8">
        <a
          href="/admin/messages"
          className="text-sm text-muted hover:text-foreground transition-colors mb-4 inline-block"
        >
          ← Back to messages
        </a>
        <PageHeader
          title={client.companyName}
          subtitle={`Thread for client ${client.userId}`}
        />
      </div>
      <MessageThread
        initialMessages={messageList}
        clientId={clientId}
        apiEndpoint="/api/admin/messages"
      />
    </div>
  )
}
