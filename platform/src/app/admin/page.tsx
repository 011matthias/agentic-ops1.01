import { db } from "@/lib/db"
import { clients, projects, milestones, messages, users } from "@/lib/schema"
import { eq, count, desc, isNull, and, isNotNull } from "drizzle-orm"
import PageHeader from "@/components/ui/PageHeader"
import StatCard from "@/components/admin/StatCard"

export const metadata = { title: "Dashboard — Admin" }

/**
 * Returns a human-readable relative time string, e.g. "3h ago", "2d ago".
 * Server-safe — no browser APIs required.
 */
function formatRelative(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)

  if (diffSecs < 60) return `${diffSecs}s ago`
  const diffMins = Math.floor(diffSecs / 60)
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 30) return `${diffDays}d ago`
  const diffMonths = Math.floor(diffDays / 30)
  return `${diffMonths}mo ago`
}

type ActivityEvent =
  | {
      type: "message"
      id: string
      clientCompanyName: string
      authorRole: "admin" | "client"
      body: string
      timestamp: Date
    }
  | {
      type: "milestone"
      id: string
      milestoneTitle: string
      projectName: string
      timestamp: Date
    }

export default async function AdminDashboardPage() {
  // ── Stats ─────────────────────────────────────────────────────────────────

  const [activeClientsResult] = await db
    .select({ value: count(clients.id) })
    .from(clients)
    .where(eq(clients.status, "active"))

  const [activeProjectsResult] = await db
    .select({ value: count(projects.id) })
    .from(projects)
    .where(eq(projects.status, "active"))

  const [unreadMessagesResult] = await db
    .select({ value: count(messages.id) })
    .from(messages)
    .where(and(isNull(messages.readAt), eq(messages.authorRole, "client")))

  const [prospectsResult] = await db
    .select({ value: count(users.id) })
    .from(users)
    .where(eq(users.role, "prospect"))

  const activeClientsCount = activeClientsResult?.value ?? 0
  const activeProjectsCount = activeProjectsResult?.value ?? 0
  const unreadMessagesCount = unreadMessagesResult?.value ?? 0
  const prospectsCount = prospectsResult?.value ?? 0

  // ── Activity feed ─────────────────────────────────────────────────────────

  // Recent messages with client company name
  const recentMessages = await db
    .select({
      id: messages.id,
      clientId: messages.clientId,
      clientCompanyName: clients.companyName,
      authorRole: messages.authorRole,
      body: messages.body,
      createdAt: messages.createdAt,
    })
    .from(messages)
    .leftJoin(clients, eq(messages.clientId, clients.id))
    .orderBy(desc(messages.createdAt))
    .limit(10)

  // Recent milestones marked done with project and client names
  const recentMilestones = await db
    .select({
      id: milestones.id,
      title: milestones.title,
      completedAt: milestones.completedAt,
      projectName: projects.name,
    })
    .from(milestones)
    .leftJoin(projects, eq(milestones.projectId, projects.id))
    .where(and(eq(milestones.status, "done"), isNotNull(milestones.completedAt)))
    .orderBy(desc(milestones.completedAt))
    .limit(10)

  // Build unified activity list
  const events: ActivityEvent[] = []

  for (const msg of recentMessages) {
    if (!msg.createdAt) continue
    events.push({
      type: "message",
      id: msg.id,
      clientCompanyName: msg.clientCompanyName ?? "Unknown client",
      authorRole: msg.authorRole,
      body: msg.body.length > 80 ? msg.body.slice(0, 80) + "…" : msg.body,
      timestamp: msg.createdAt,
    })
  }

  for (const ms of recentMilestones) {
    if (!ms.completedAt) continue
    events.push({
      type: "milestone",
      id: ms.id,
      milestoneTitle: ms.title,
      projectName: ms.projectName ?? "Unknown project",
      timestamp: ms.completedAt,
    })
  }

  // Sort by timestamp desc, take top 10
  events.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
  const topEvents = events.slice(0, 10)

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader title="Dashboard" />

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        <StatCard label="Active clients" value={activeClientsCount} />
        <StatCard label="Active projects" value={activeProjectsCount} />
        <StatCard
          label="Unread messages"
          value={unreadMessagesCount}
          sublabel="from clients"
        />
        <StatCard
          label="Pending review"
          value={prospectsCount}
          sublabel="prospects"
        />
      </div>

      {/* Activity feed */}
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Recent Activity
      </h2>

      {topEvents.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 p-12 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">No recent activity yet.</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {topEvents.map((event) => (
            <li
              key={`${event.type}-${event.id}`}
              className="flex items-start gap-3 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-3"
            >
              <span className="mt-0.5 text-base leading-none shrink-0">
                {event.type === "message" ? "💬" : "✅"}
              </span>
              <div className="flex-1 min-w-0">
                {event.type === "message" ? (
                  <p className="text-sm text-gray-800 dark:text-gray-200">
                    <span className="font-medium">
                      Message from {event.authorRole}
                    </span>{" "}
                    re: {event.clientCompanyName}
                  </p>
                ) : (
                  <p className="text-sm text-gray-800 dark:text-gray-200">
                    <span className="font-medium">Milestone done:</span>{" "}
                    {event.milestoneTitle}{" "}
                    <span className="text-gray-500 dark:text-gray-400">
                      on {event.projectName}
                    </span>
                  </p>
                )}
              </div>
              <span className="shrink-0 text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                {formatRelative(event.timestamp)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
