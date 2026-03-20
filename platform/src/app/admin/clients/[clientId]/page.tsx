import { redirect } from "next/navigation"
import { eq, and, isNull, count, desc, asc } from "drizzle-orm"
import { db } from "@/lib/db"
import { clients, projects, messages, files, purchases, products, clientResources } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import Badge from "@/components/ui/Badge"
import EmptyState from "@/components/ui/EmptyState"
import TabNav from "@/components/ui/TabNav"
import MessageThread from "@/components/portal/MessageThread"
import Link from "next/link"
import OverviewTab from "./tabs/OverviewTab"
import ProjectsTab from "./tabs/ProjectsTab"
import FilesTab from "./tabs/FilesTab"
import ResourcesTab from "./tabs/ResourcesTab"

type Tab = "overview" | "projects" | "messages" | "files" | "purchases" | "resources"
const VALID_TABS: Tab[] = ["overview", "projects", "messages", "files", "purchases", "resources"]

interface Props {
  params: Promise<{ clientId: string }>
  searchParams: Promise<{ tab?: string }>
}

export async function generateMetadata({ params }: { params: Promise<{ clientId: string }> }) {
  const { clientId } = await params
  const client = await db.query.clients.findFirst({
    where: eq(clients.id, clientId),
  })
  return { title: client ? `${client.companyName} — Admin` : "Client — Admin" }
}

function formatCents(cents: number | string | null): string {
  const n = typeof cents === "string" ? parseFloat(cents) : (cents ?? 0)
  return (n / 100).toLocaleString("en-US", { style: "currency", currency: "USD" })
}

export default async function AdminClientDetailPage({ params, searchParams }: Props) {
  const { clientId } = await params
  const { tab: tabParam } = await searchParams
  const tab: Tab = VALID_TABS.includes(tabParam as Tab) ? (tabParam as Tab) : "overview"

  // Always fetch: client + counts
  const client = await db.query.clients.findFirst({
    where: eq(clients.id, clientId),
  })

  if (!client) {
    redirect("/admin/clients")
  }

  const [projectCount, unreadCount, fileCount, purchaseCount, resourceCount] = await Promise.all([
    db.select({ value: count() }).from(projects).where(eq(projects.clientId, clientId)).then((r) => r[0]?.value ?? 0),
    db.select({ value: count() }).from(messages).where(and(eq(messages.clientId, clientId), isNull(messages.readAt))).then((r) => r[0]?.value ?? 0),
    db.select({ value: count() }).from(files).where(eq(files.clientId, clientId)).then((r) => r[0]?.value ?? 0),
    db.select({ value: count() }).from(purchases).where(eq(purchases.userId, client.userId)).then((r) => r[0]?.value ?? 0),
    db.select({ value: count() }).from(clientResources).where(eq(clientResources.clientId, clientId)).then((r) => r[0]?.value ?? 0),
  ])

  // Per-tab data fetching
  let projectList: Awaited<ReturnType<typeof db.query.projects.findMany>> | undefined
  let messageList: Array<{ id: string; authorRole: "admin" | "client"; body: string; createdAt: Date }> | undefined
  let fileList: Array<{
    id: string
    filename: string
    url: string
    sizeBytes: number | null
    mimeType: string | null
    createdAt: Date
    project: { id: string; name: string } | null
  }> | undefined
  let purchaseList: Array<{
    id: string
    status: string
    stripeSessionId: string | null
    createdAt: Date
    productName: string | null
    priceUsd: number | null
  }> | undefined
  let resourceList: Awaited<ReturnType<typeof db.query.clientResources.findMany>> | undefined

  if (tab === "overview" || tab === "projects") {
    projectList = await db.query.projects.findMany({
      where: eq(projects.clientId, clientId),
      orderBy: (p, { desc }) => [desc(p.createdAt)],
    })
  }

  if (tab === "messages") {
    // Mark unread as read
    await db
      .update(messages)
      .set({ readAt: new Date() })
      .where(and(eq(messages.clientId, clientId), isNull(messages.readAt)))

    messageList = await db.query.messages.findMany({
      where: eq(messages.clientId, clientId),
      orderBy: (m, { asc }) => [asc(m.createdAt)],
    })
  }

  if (tab === "files") {
    fileList = await db.query.files.findMany({
      where: eq(files.clientId, clientId),
      orderBy: desc(files.createdAt),
      with: { project: true },
    }) as typeof fileList
  }

  if (tab === "resources") {
    resourceList = await db.query.clientResources.findMany({
      where: eq(clientResources.clientId, clientId),
      orderBy: [asc(clientResources.category), asc(clientResources.sortOrder)],
    })
  }

  if (tab === "purchases") {
    purchaseList = await db
      .select({
        id: purchases.id,
        status: purchases.status,
        stripeSessionId: purchases.stripeSessionId,
        createdAt: purchases.createdAt,
        productName: products.name,
        priceUsd: products.priceUsd,
      })
      .from(purchases)
      .leftJoin(products, eq(purchases.productId, products.id))
      .where(eq(purchases.userId, client.userId))
      .orderBy(desc(purchases.createdAt))
  }

  const tabs = [
    { key: "overview", label: "Overview" },
    { key: "projects", label: "Projects", count: projectCount },
    { key: "messages", label: "Messages", count: unreadCount > 0 ? unreadCount : undefined },
    { key: "files", label: "Files", count: fileCount },
    { key: "resources", label: "Resources", count: resourceCount },
    { key: "purchases", label: "Purchases", count: purchaseCount },
  ]

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="mb-2">
        <Link
          href="/admin/clients"
          className="text-sm text-muted hover:text-foreground transition-colors mb-4 inline-block"
        >
          ← Back to clients
        </Link>
        <div className="flex items-center gap-3">
          <PageHeader title={client.companyName} />
          <Badge variant={client.status === "active" ? "success" : "warning"}>
            {client.status ?? "active"}
          </Badge>
        </div>
      </div>

      <TabNav tabs={tabs} activeTab={tab} />

      {/* Overview */}
      {tab === "overview" && (
        <OverviewTab
          client={client}
          counts={{ projects: projectCount, unreadMessages: unreadCount, files: fileCount, purchases: purchaseCount }}
          recentProjects={(projectList ?? []).slice(0, 3)}
        />
      )}

      {/* Projects */}
      {tab === "projects" && (
        <ProjectsTab projects={projectList ?? []} clientId={clientId} />
      )}

      {/* Messages */}
      {tab === "messages" && (
        <MessageThread
          initialMessages={messageList ?? []}
          apiEndpoint="/api/admin/messages"
          clientId={clientId}
        />
      )}

      {/* Files */}
      {tab === "files" && (
        <FilesTab
          files={(fileList ?? []).map((f) => ({
            ...f,
            createdAt: f.createdAt.toISOString(),
          }))}
          clientId={clientId}
        />
      )}

      {/* Resources */}
      {tab === "resources" && (
        <ResourcesTab
          resources={(resourceList ?? []).map((r) => ({
            ...r,
            createdAt: r.createdAt.toISOString(),
          }))}
          clientId={clientId}
        />
      )}

      {/* Purchases */}
      {tab === "purchases" && (
        <>
          {!purchaseList || purchaseList.length === 0 ? (
            <EmptyState
              title="No purchases yet"
              description="Purchases by this client will appear here."
            />
          ) : (
            <div className="rounded-2xl border border-border bg-white dark:bg-gray-900 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-gray-50 dark:bg-gray-800/50">
                    <th className="text-left px-6 py-3 font-medium text-muted">Date</th>
                    <th className="text-left px-6 py-3 font-medium text-muted">Product</th>
                    <th className="text-left px-6 py-3 font-medium text-muted">Amount</th>
                    <th className="text-left px-6 py-3 font-medium text-muted">Status</th>
                    <th className="text-left px-6 py-3 font-medium text-muted">Stripe</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {purchaseList.map((purchase) => (
                    <tr
                      key={purchase.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
                    >
                      <td className="px-6 py-4 text-muted whitespace-nowrap">
                        {purchase.createdAt.toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </td>
                      <td className="px-6 py-4 text-foreground">
                        {purchase.productName ?? <span className="text-muted">—</span>}
                      </td>
                      <td className="px-6 py-4 text-foreground whitespace-nowrap">
                        {purchase.priceUsd != null ? formatCents(purchase.priceUsd) : "—"}
                      </td>
                      <td className="px-6 py-4">
                        <Badge
                          variant={
                            purchase.status === "complete"
                              ? "success"
                              : purchase.status === "refunded"
                              ? "error"
                              : "warning"
                          }
                        >
                          {purchase.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4">
                        {purchase.stripeSessionId ? (
                          <a
                            href={`https://dashboard.stripe.com/payments/${purchase.stripeSessionId}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-accent hover:underline text-sm"
                          >
                            View →
                          </a>
                        ) : (
                          <span className="text-muted">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

