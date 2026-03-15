import { desc, eq, count, max } from "drizzle-orm"
import { db } from "@/lib/db"
import { clients, projects, messages } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import Badge from "@/components/ui/Badge"
import Link from "next/link"

export const metadata = { title: "Clients — Admin" }

export default async function AdminClientsPage() {
  const allClients = await db
    .select({
      id: clients.id,
      userId: clients.userId,
      companyName: clients.companyName,
      status: clients.status,
      createdAt: clients.createdAt,
    })
    .from(clients)
    .orderBy(desc(clients.createdAt))

  // Active project counts per client
  const activeProjectCounts = await db
    .select({
      clientId: projects.clientId,
      activeCount: count(projects.id),
    })
    .from(projects)
    .where(eq(projects.status, "active"))
    .groupBy(projects.clientId)

  const activeCountMap = new Map(
    activeProjectCounts.map((r) => [r.clientId, r.activeCount])
  )

  // Most recent message per client
  const lastMessageDates = await db
    .select({
      clientId: messages.clientId,
      lastContact: max(messages.createdAt),
    })
    .from(messages)
    .groupBy(messages.clientId)

  const lastContactMap = new Map(
    lastMessageDates.map((r) => [r.clientId, r.lastContact])
  )

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader
        title="Clients"
        subtitle={`${allClients.length} total client${allClients.length !== 1 ? "s" : ""}`}
      />

      {allClients.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center rounded-2xl border border-dashed border-border p-12">
          <h3 className="text-lg font-semibold text-foreground mb-2">No clients yet</h3>
          <p className="text-sm text-muted max-w-sm">
            Client records are created when users sign up and are assigned the client role.
          </p>
        </div>
      ) : (
        <div className="rounded-2xl border border-border bg-white dark:bg-gray-900 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-gray-50 dark:bg-gray-800/50">
                <th className="text-left px-6 py-3 font-medium text-muted">Client</th>
                <th className="text-left px-6 py-3 font-medium text-muted">Status</th>
                <th className="text-left px-6 py-3 font-medium text-muted">Active projects</th>
                <th className="text-left px-6 py-3 font-medium text-muted">Last contact</th>
                <th className="px-6 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {allClients.map((client) => {
                const activeCount = activeCountMap.get(client.id) ?? 0
                const lastContact = lastContactMap.get(client.id)

                return (
                  <tr key={client.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                    <td className="px-6 py-4">
                      <Link
                        href={`/admin/clients/${client.id}`}
                        className="font-medium text-foreground hover:text-accent transition-colors"
                      >
                        {client.companyName}
                      </Link>
                      <p className="text-xs text-muted mt-0.5">{client.userId}</p>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={client.status === "active" ? "success" : "warning"}>
                        {client.status ?? "active"}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-foreground">
                      {activeCount}
                    </td>
                    <td className="px-6 py-4 text-muted">
                      {lastContact
                        ? lastContact.toLocaleDateString("en-GB", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          })
                        : "No messages yet"}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/admin/messages?clientId=${client.id}`}
                        className="text-accent hover:underline text-sm"
                      >
                        View messages
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
