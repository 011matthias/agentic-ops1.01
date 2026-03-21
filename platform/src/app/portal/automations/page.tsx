import { redirect } from "next/navigation"
import { desc, eq, asc } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clients, projects, milestones, moduleExecutions } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import EmptyState from "@/components/ui/EmptyState"
import Card from "@/components/ui/Card"
import Badge from "@/components/ui/Badge"

export const metadata = { title: "Automations" }

type ProjectStatus = "active" | "paused" | "complete"
type MilestoneStatus = "pending" | "in-progress" | "done"
type ExecutionStatus = "success" | "error" | "partial"

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

const executionStatusVariant: Record<ExecutionStatus, "success" | "error" | "warning"> = {
  success: "success",
  error: "error",
  partial: "warning",
}

const orchestratorLabel: Record<string, string> = {
  make: "Make.com",
  n8n: "n8n",
  "trigger-dev": "Trigger.dev",
  fastapi: "FastAPI",
}

function formatDate(date: Date | null): string {
  if (!date) return ""
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  })
}

function formatRelativeTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return "just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return formatDate(date)
}

function MilestoneIcon({ status }: { status: MilestoneStatus }) {
  if (status === "done") {
    return (
      <span
        className="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold shrink-0"
        style={{ color: "var(--accent)", border: "2px solid var(--accent)" }}
        aria-label="Done"
      >
        ✓
      </span>
    )
  }
  if (status === "in-progress") {
    return (
      <span
        className="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs shrink-0"
        style={{
          color: "var(--foreground)",
          border: "2px solid var(--foreground)",
          backgroundColor: "var(--foreground)",
        }}
        aria-label="In progress"
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: "var(--background)" }}
        />
      </span>
    )
  }
  return (
    <span
      className="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs shrink-0"
      style={{ border: "2px solid var(--muted)" }}
      aria-label="Pending"
    />
  )
}

type MilestoneRow = typeof milestones.$inferSelect
type ExecutionRow = typeof moduleExecutions.$inferSelect
type ProjectWithData = typeof projects.$inferSelect & {
  milestones: MilestoneRow[]
  moduleExecutions: ExecutionRow[]
}

function MilestoneTimeline({
  projectMilestones,
}: {
  projectMilestones: MilestoneRow[]
}) {
  if (projectMilestones.length === 0) return null

  const doneCount = projectMilestones.filter((m) => m.status === "done").length
  const total = projectMilestones.length

  return (
    <div className="mt-4 pt-4 border-t border-border">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-foreground">Milestones</span>
        <span className="text-xs text-muted">
          {doneCount} / {total} complete
        </span>
      </div>
      <ul className="space-y-2">
        {projectMilestones.map((milestone) => {
          const status = milestone.status as MilestoneStatus
          const labelColor =
            status === "done"
              ? "var(--accent)"
              : status === "in-progress"
                ? "var(--foreground)"
                : "var(--muted)"
          return (
            <li key={milestone.id} className="flex items-center gap-3">
              <MilestoneIcon status={status} />
              <span
                className="flex-1 text-sm truncate"
                style={{ color: labelColor }}
              >
                {milestone.title}
              </span>
              {milestone.dueDate && (
                <span className="text-xs shrink-0" style={{ color: "var(--muted)" }}>
                  {formatDate(milestone.dueDate)}
                </span>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function ExecutionSummary({ executions }: { executions: ExecutionRow[] }) {
  if (executions.length === 0) return null

  const latest = executions[0]
  const totalRuns = executions.length
  const latestStatus = latest.status as ExecutionStatus

  return (
    <div className="mt-4 pt-4 border-t border-border">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-foreground">Recent Activity</span>
        <span className="text-xs text-muted">{totalRuns} run{totalRuns !== 1 ? "s" : ""}</span>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant={executionStatusVariant[latestStatus]}>
          {latestStatus}
        </Badge>
        <span className="text-xs text-muted">
          {formatRelativeTime(latest.executedAt)}
        </span>
        {latest.itemCount > 0 && (
          <span className="text-xs text-muted">
            {latest.itemCount} item{latest.itemCount !== 1 ? "s" : ""}
          </span>
        )}
      </div>
    </div>
  )
}

export default async function AutomationsPage() {
  const session = await auth()
  if (!session?.user?.id) redirect("/login")

  const client = await db.query.clients.findFirst({
    where: eq(clients.userId, session.user.id),
  })

  const projectList: ProjectWithData[] = client
    ? await db.query.projects.findMany({
        where: eq(projects.clientId, client.id),
        orderBy: desc(projects.createdAt),
        with: {
          milestones: {
            orderBy: asc(milestones.dueDate),
          },
          moduleExecutions: {
            orderBy: desc(moduleExecutions.executedAt),
            limit: 10,
          },
        },
      })
    : []

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader
        title="Automations"
        subtitle="Monitor your active automations, run history, and status."
      />

      {projectList.length === 0 ? (
        <EmptyState
          title="No projects yet"
          description="Your team is setting things up. Your automation projects will appear here once they are ready."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {projectList.map((project) => {
            const status = project.status as ProjectStatus
            return (
              <Card key={project.id} className="flex flex-col gap-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h2 className="text-base font-semibold text-foreground truncate">
                      {project.name}
                    </h2>
                    {project.description && (
                      <p className="mt-1 text-sm text-muted line-clamp-2">
                        {project.description}
                      </p>
                    )}
                  </div>
                  <Badge variant={statusVariant[status]}>
                    {statusLabel[status]}
                  </Badge>
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
                  {project.orchestrator && (
                    <span>
                      {orchestratorLabel[project.orchestrator] ??
                        project.orchestrator}
                    </span>
                  )}
                  {project.targetDate && (
                    <span>Target: {formatDate(project.targetDate)}</span>
                  )}
                  {project.startDate && (
                    <span>Started: {formatDate(project.startDate)}</span>
                  )}
                </div>

                <ExecutionSummary executions={project.moduleExecutions} />

                {project.milestones.length > 0 && (
                  <MilestoneTimeline projectMilestones={project.milestones} />
                )}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
