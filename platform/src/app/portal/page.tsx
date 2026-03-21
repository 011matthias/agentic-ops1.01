import { eq, isNull, and, count } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clients, projects, milestones, messages } from "@/lib/schema"
import StatCard from "@/components/portal/StatCard"
import PortalCard from "@/components/portal/PortalCard"

export default async function PortalPage() {
  const session = await auth()

  const firstName = session?.user?.name?.split(" ")[0] ?? "there"

  type ProjectWithProgress = {
    id: string
    name: string
    status: string
    orchestrator: string | null
    totalMilestones: number
    doneMilestones: number
  }

  let activeAutomations = "—"
  let milestonesdone = "—"
  let openMessages = "—"
  let clientProjects: ProjectWithProgress[] = []

  if (session?.user?.id) {
    const client = await db.query.clients.findFirst({
      where: eq(clients.userId, session.user.id),
    })

    if (client) {
      const [activeProjectRows, unreadMessages] = await Promise.all([
        db.query.projects.findMany({
          where: and(
            eq(projects.clientId, client.id),
            eq(projects.status, "active")
          ),
        }),
        db.query.messages.findMany({
          where: and(
            eq(messages.clientId, client.id),
            isNull(messages.readAt)
          ),
        }),
      ])

      // Fetch milestone progress for each project
      const projectsWithProgress: ProjectWithProgress[] = await Promise.all(
        activeProjectRows.map(async (p) => {
          const [totalResult] = await db
            .select({ value: count(milestones.id) })
            .from(milestones)
            .where(eq(milestones.projectId, p.id))

          const [doneResult] = await db
            .select({ value: count(milestones.id) })
            .from(milestones)
            .where(and(eq(milestones.projectId, p.id), eq(milestones.status, "done")))

          return {
            id: p.id,
            name: p.name,
            status: p.status,
            orchestrator: p.orchestrator,
            totalMilestones: totalResult?.value ?? 0,
            doneMilestones: doneResult?.value ?? 0,
          }
        })
      )

      const totalDone = projectsWithProgress.reduce((acc, p) => acc + p.doneMilestones, 0)

      activeAutomations = String(activeProjectRows.length)
      milestonesdone = String(totalDone)
      openMessages = String(unreadMessages.length)
      clientProjects = projectsWithProgress
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <div className="mb-10">
        <h1 className="text-3xl font-bold">Welcome back, {firstName}</h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Here&apos;s an overview of your automations and activity.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-12">
        <StatCard label="Active Automations" value={activeAutomations} />
        <StatCard label="Milestones Done" value={milestonesdone} />
        <StatCard label="Open Messages" value={openMessages} />
      </div>

      {/* Active projects */}
      {clientProjects.length > 0 ? (
        <div className="mb-12">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Your Projects
          </h2>
          <ul className="space-y-3">
            {clientProjects.map((p) => {
              const pct =
                p.totalMilestones > 0
                  ? Math.round((p.doneMilestones / p.totalMilestones) * 100)
                  : 0
              return (
                <li
                  key={p.id}
                  className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 px-5 py-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {p.name}
                      </p>
                      {p.orchestrator && (
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 capitalize">
                          {p.orchestrator.replace(/-/g, " ")}
                        </p>
                      )}
                    </div>
                    <span className="text-sm text-gray-500 dark:text-gray-400 shrink-0 ml-4">
                      {p.doneMilestones}/{p.totalMilestones} steps
                    </span>
                  </div>
                  {p.totalMilestones > 0 && (
                    <div className="h-1.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-blue-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      ) : (
        <div className="mb-12 rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 p-10 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Your project is being set up. Check back soon.
          </p>
        </div>
      )}

      {/* Navigation cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <PortalCard
          title="Messages"
          description="Communicate with the UnpauseAI team about your project."
          href="/portal/messages"
          icon="💬"
        />
        <PortalCard
          title="Resources"
          description="Documentation, guides, and setup materials for your automations."
          href="/portal/resources"
          icon="📚"
        />
        <PortalCard
          title="Settings"
          description="Manage your account and preferences."
          href="/portal/settings"
          icon="⚙️"
        />
      </div>
    </div>
  )
}
