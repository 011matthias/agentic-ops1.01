import { redirect } from "next/navigation"
import { desc, eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clients, projects } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import EmptyState from "@/components/ui/EmptyState"
import Card from "@/components/ui/Card"
import Badge from "@/components/ui/Badge"

export const metadata = { title: "Reports" }

type ProjectStatus = "active" | "paused" | "complete"

const statusVariant: Record<ProjectStatus, "success" | "warning" | "default"> =
  {
    active: "success",
    paused: "warning",
    complete: "default",
  }

const statusLabel: Record<ProjectStatus, string> = {
  active: "Active",
  paused: "Paused",
  complete: "Complete",
}

function formatDate(date: Date | null): string {
  if (!date) return ""
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  })
}

function daysRemaining(targetDate: Date | null): number | null {
  if (!targetDate) return null
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const target = new Date(targetDate)
  target.setHours(0, 0, 0, 0)
  return Math.round((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
}

export default async function ReportsPage() {
  const session = await auth()
  if (!session?.user?.id) redirect("/login")

  const client = await db.query.clients.findFirst({
    where: eq(clients.userId, session.user.id),
  })

  const projectList = client
    ? await db.query.projects.findMany({
        where: eq(projects.clientId, client.id),
        orderBy: desc(projects.createdAt),
        with: {
          milestones: true,
        },
      })
    : []

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader
        title="Reports"
        subtitle="Progress summaries and milestone tracking for your projects."
      />

      {projectList.length === 0 ? (
        <EmptyState
          title="No projects yet"
          description="Project progress reports and milestone summaries will appear here once your automations are running."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {projectList.map((project) => {
            const status = project.status as ProjectStatus
            const milestoneList = project.milestones ?? []
            const total = milestoneList.length
            const doneCount = milestoneList.filter(
              (m) => m.status === "done"
            ).length
            const pct = total > 0 ? Math.round((doneCount / total) * 100) : 0
            const days = daysRemaining(project.targetDate)
            const isOverdue = days !== null && days < 0

            return (
              <Card key={project.id} className="flex flex-col gap-4">
                {/* Header row */}
                <div className="flex items-start justify-between gap-4">
                  <h2 className="text-base font-semibold text-foreground">
                    {project.name}
                  </h2>
                  <Badge variant={statusVariant[status]}>
                    {statusLabel[status]}
                  </Badge>
                </div>

                {/* Progress bar */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs text-muted">
                      {total > 0
                        ? `${doneCount} of ${total} milestones complete`
                        : "No milestones"}
                    </span>
                    {total > 0 && (
                      <span className="text-xs font-medium text-foreground">
                        {pct}%
                      </span>
                    )}
                  </div>
                  {total > 0 && (
                    <div
                      className="w-full rounded-full overflow-hidden"
                      style={{
                        height: "6px",
                        backgroundColor: "var(--border)",
                      }}
                    >
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${pct}%`,
                          backgroundColor:
                            pct === 100 ? "var(--accent)" : "var(--accent)",
                        }}
                      />
                    </div>
                  )}
                </div>

                {/* Target date + days remaining */}
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                  {project.targetDate ? (
                    <>
                      <span>Target: {formatDate(project.targetDate)}</span>
                      {days !== null && (
                        <span
                          className={
                            isOverdue ? "font-semibold" : ""
                          }
                          style={
                            isOverdue ? { color: "#dc2626" } : {}
                          }
                        >
                          {isOverdue
                            ? `Overdue by ${Math.abs(days)} day${Math.abs(days) === 1 ? "" : "s"}`
                            : days === 0
                              ? "Due today"
                              : `${days} day${days === 1 ? "" : "s"} remaining`}
                        </span>
                      )}
                    </>
                  ) : (
                    <span>No target date set</span>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
