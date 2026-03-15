import { redirect } from "next/navigation"
import { desc, eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clients, projects } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import EmptyState from "@/components/ui/EmptyState"
import Card from "@/components/ui/Card"
import Badge from "@/components/ui/Badge"

export const metadata = { title: "Automations" }

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

export default async function AutomationsPage() {
  const session = await auth()
  if (!session?.user?.id) redirect("/login")

  const client = await db.query.clients.findFirst({
    where: eq(clients.userId, session.user.id),
  })

  const projectList = client
    ? await db.query.projects.findMany({
        where: eq(projects.clientId, client.id),
        orderBy: desc(projects.createdAt),
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
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
