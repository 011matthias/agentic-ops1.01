import { desc, count, eq, sql } from "drizzle-orm"
import { db } from "@/lib/db"
import { projects, clients, milestones } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import Badge from "@/components/ui/Badge"
import Link from "next/link"

export const metadata = { title: "Projects — Admin" }

type ProjectStatus = "active" | "paused" | "complete"

const STATUS_ORDER: ProjectStatus[] = ["active", "paused", "complete"]

const STATUS_LABELS: Record<ProjectStatus, string> = {
  active: "Active",
  paused: "Paused",
  complete: "Complete",
}

const ORCHESTRATOR_LABELS: Record<string, string> = {
  make: "Make",
  n8n: "n8n",
  "trigger-dev": "Trigger.dev",
  fastapi: "FastAPI",
}

function orchestratorLabel(value: string | null): string {
  if (!value) return "—"
  return ORCHESTRATOR_LABELS[value] ?? value
}

function formatTargetDate(date: Date | null): {
  label: string
  overdue: boolean
} {
  if (!date) return { label: "No target date", overdue: false }
  const now = new Date()
  const diff = Math.floor(
    (date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
  )
  if (diff < 0) {
    const days = Math.abs(diff)
    return {
      label: `Overdue by ${days} day${days !== 1 ? "s" : ""}`,
      overdue: true,
    }
  }
  return {
    label: `Due ${date.toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    })}`,
    overdue: false,
  }
}

export default async function AdminProjectsPage() {
  const allProjects = await db
    .select({
      id: projects.id,
      name: projects.name,
      clientId: projects.clientId,
      clientName: clients.companyName,
      status: projects.status,
      orchestrator: projects.orchestrator,
      targetDate: projects.targetDate,
      createdAt: projects.createdAt,
    })
    .from(projects)
    .leftJoin(clients, eq(projects.clientId, clients.id))
    .orderBy(desc(projects.createdAt))

  const milestoneCounts = await db
    .select({
      projectId: milestones.projectId,
      total: count(milestones.id),
      done: count(sql`CASE WHEN ${milestones.status} = 'done' THEN 1 END`),
    })
    .from(milestones)
    .groupBy(milestones.projectId)

  const milestoneMap = new Map(
    milestoneCounts.map((r) => [r.projectId, { total: r.total, done: r.done }])
  )

  const grouped = STATUS_ORDER.reduce(
    (acc, status) => {
      acc[status] = allProjects.filter((p) => p.status === status)
      return acc
    },
    {} as Record<ProjectStatus, typeof allProjects>
  )

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <PageHeader
        title="Projects"
        subtitle={`${allProjects.length} total project${allProjects.length !== 1 ? "s" : ""}`}
      />

      {allProjects.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center rounded-2xl border border-dashed border-border p-12">
          <h3 className="text-lg font-semibold text-foreground mb-2">
            No projects yet
          </h3>
          <p className="text-sm text-muted max-w-sm">
            Projects are created from the{" "}
            <Link
              href="/admin/clients"
              className="text-accent hover:underline"
            >
              client detail page
            </Link>
            .
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-10">
          {STATUS_ORDER.map((status) => {
            const group = grouped[status]
            if (group.length === 0) return null

            return (
              <section key={status}>
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-base font-semibold text-foreground">
                    {STATUS_LABELS[status]}
                  </h2>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                    {group.length}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {group.map((project) => {
                    const ms = milestoneMap.get(project.id) ?? {
                      total: 0,
                      done: 0,
                    }
                    const progressPct =
                      ms.total > 0
                        ? Math.round((ms.done / ms.total) * 100)
                        : 0
                    const target = formatTargetDate(project.targetDate)

                    return (
                      <div
                        key={project.id}
                        className="rounded-2xl border border-border bg-white dark:bg-gray-900 p-5 flex flex-col gap-3"
                      >
                        {/* Header */}
                        <div>
                          <p className="font-semibold text-foreground leading-snug">
                            {project.name}
                          </p>
                          {project.clientId && (
                            <Link
                              href={`/admin/clients/${project.clientId}`}
                              className="text-xs text-muted hover:text-accent transition-colors mt-0.5 inline-block"
                            >
                              {project.clientName ?? "Unknown client"}
                            </Link>
                          )}
                        </div>

                        {/* Badges */}
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge
                            variant={
                              project.status === "active"
                                ? "success"
                                : project.status === "paused"
                                  ? "warning"
                                  : "default"
                            }
                          >
                            {STATUS_LABELS[project.status as ProjectStatus] ??
                              project.status}
                          </Badge>
                          {project.orchestrator && (
                            <Badge variant="default">
                              {orchestratorLabel(project.orchestrator)}
                            </Badge>
                          )}
                        </div>

                        {/* Milestone progress */}
                        <div>
                          <div className="flex items-center justify-between text-xs text-muted mb-1">
                            <span>
                              {ms.done} / {ms.total} milestones done
                            </span>
                            {ms.total > 0 && (
                              <span>{progressPct}%</span>
                            )}
                          </div>
                          <div className="h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-accent transition-all"
                              style={{ width: `${progressPct}%` }}
                            />
                          </div>
                        </div>

                        {/* Target date */}
                        <p
                          className={`text-xs ${target.overdue ? "text-red-600 dark:text-red-400 font-medium" : "text-muted"}`}
                        >
                          {target.label}
                        </p>

                        {/* Link */}
                        <div className="mt-auto pt-1">
                          <Link
                            href={`/admin/projects/${project.id}`}
                            className="text-sm text-accent hover:underline font-medium"
                          >
                            Manage &rarr;
                          </Link>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
