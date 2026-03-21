import { redirect } from "next/navigation"
import { desc, eq, and, isNull } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clients, messages } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import MessageThread from "@/components/portal/MessageThread"

export const metadata = { title: "Messages" }

export default async function MessagesPage() {
  const session = await auth()
  if (!session?.user?.id) redirect("/login")

  const client = await db.query.clients.findFirst({
    where: eq(clients.userId, session.user.id),
  })

  if (client) {
    // Mark unread messages as read when client views the page
    await db
      .update(messages)
      .set({ readAt: new Date() })
      .where(and(eq(messages.clientId, client.id), isNull(messages.readAt)))
  }

  const messageList = client
    ? await db.query.messages.findMany({
        where: eq(messages.clientId, client.id),
        orderBy: desc(messages.createdAt),
      })
    : []

  // Reverse so oldest is shown first (thread order)
  const sorted = [...messageList].reverse()

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <PageHeader
        title="Messages"
        subtitle="Communicate with the UnpauseAI team about your project."
      />
      <MessageThread initialMessages={sorted} />
    </div>
  )
}
