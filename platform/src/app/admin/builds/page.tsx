import { db } from "@/lib/db"
import { autopilotBuilds, projects } from "@/lib/schema"
import { desc, eq, sql } from "drizzle-orm"
import PageHeader from "@/components/ui/PageHeader"
import StatCard from "@/components/admin/StatCard"
import Badge from "@/components/ui/Badge"
import EmptyState from "@/components/ui/EmptyState"

export const metadata = { title: "Builds — Admin" }

const statusVariant: Record<string, "success" | "warning" | "error" | "default"> = {
  pending: "default",
  running: "warning",
  waiting: "warning",
  completed: "success",
  failed: "error",
  cancelled: "default",
}

function formatDate(date: Date | null) {
  if (!date) return "—"
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default async function BuildsPage() {
  const builds = await db
    .select({
      id: autopilotBuilds.id,
      specId: autopilotBuilds.specId,
      status: autopilotBuilds.status,
      directive: autopilotBuilds.directive,
      currentPhase: autopilotBuilds.currentPhase,
      startedAt: autopilotBuilds.startedAt,
      completedAt: autopilotBuilds.completedAt,
      createdAt: autopilotBuilds.createdAt,
      projectName: projects.name,
    })
    .from(autopilotBuilds)
    .leftJoin(projects, eq(autopilotBuilds.projectId, projects.id))
    .orderBy(desc(autopilotBuilds.createdAt))
    .limit(50)

  const statusCounts = await db
    .select({
      status: autopilotBuilds.status,
      count: sql<number>`count(*)::int`,
    })
    .from(autopilotBuilds)
    .groupBy(autopilotBuilds.status)

  const counts: Record<string, number> = {}
  for (const row of statusCounts) {
    counts[row.status] = row.count
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <PageHeader
        title="Autopilot Builds"
        subtitle="Monitor autonomous build runs across projects."
      />

      {builds.length === 0 ? (
        <EmptyState
          title="No builds yet"
          description="Autopilot builds will appear here once the task layer is deployed and builds are triggered."
        />
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            <StatCard label="Pending" value={String(counts.pending ?? 0)} />
            <StatCard label="Running" value={String(counts.running ?? 0)} />
            <StatCard label="Completed" value={String(counts.completed ?? 0)} />
            <StatCard label="Failed" value={String(counts.failed ?? 0)} />
          </div>

          <div className="rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Project</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Spec</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Phase</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Started</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400">Completed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {builds.map((build) => (
                  <tr key={build.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                      {build.projectName ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400 font-mono text-xs">
                      {build.specId}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={statusVariant[build.status] ?? "default"}>
                        {build.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                      {build.currentPhase ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-500 text-xs">
                      {formatDate(build.startedAt)}
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-500 text-xs">
                      {formatDate(build.completedAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
