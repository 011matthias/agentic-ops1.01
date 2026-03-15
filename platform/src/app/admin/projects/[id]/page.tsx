import { eq } from "drizzle-orm"
import { notFound } from "next/navigation"
import Link from "next/link"
import { db } from "@/lib/db"
import { projects, clients, milestones } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import Badge from "@/components/ui/Badge"
import Card from "@/components/ui/Card"
import MilestoneToggle from "@/components/admin/MilestoneToggle"
import AddMilestoneForm from "./AddMilestoneForm"
import ProjectStatusForm from "./ProjectStatusForm"

export const metadata = { title: "Project Detail — Admin" }

const ORCHESTRATOR_LABELS: Record<string, string> = {
  make: "Make",
  n8n: "n8n",
  "trigger-dev": "Trigger.dev",
  fastapi: "FastAPI",
}

interface Props {
  params: Promise<{ id: string }>
}

export default async function AdminProjectDetailPage({ params }: Props) {
  const { id } = await params

  const rows = await db
    .select({
      id: projects.id,
      name: projects.name,
      description: projects.description,
      status: projects.status,
      orchestrator: projects.orchestrator,
      targetDate: projects.targetDate,
      startDate: projects.startDate,
      createdAt: projects.createdAt,
      clientId: projects.clientId,
      clientName: clients.companyName,
    })
    .from(projects)
    .leftJoin(clients, eq(projects.clientId, clients.id))
    .where(eq(projects.id, id))

  const project = rows[0]

  if (!project) {
    notFound()
  }

  const projectMilestones = await db
    .select()
    .from(milestones)
    .where(eq(milestones.projectId, id))
    .orderBy(milestones.createdAt)

  const done = projectMilestones.filter((m) => m.status === "done").length
  const total = projectMilestones.length
  const progressPct = total > 0 ? Math.round((done / total) * 100) : 0

  const statusVariant =
    project.status === "active"
      ? "success"
      : project.status === "paused"
        ? "warning"
        : "default"

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      {/* Back link */}
      <Link
        href="/admin/projects"
        className="text-sm text-muted hover:text-foreground transition-colors mb-6 inline-block"
      >
        &larr; Projects
      </Link>

      {/* Page header */}
      <PageHeader
        title={project.name}
        subtitle={project.clientName ?? undefined}
      />

      {/* Project meta */}
      <div className="flex items-center gap-2 flex-wrap mb-8 -mt-4">
        <Badge variant={statusVariant}>{project.status}</Badge>
        {project.orchestrator && (
          <Badge variant="default">
            {ORCHESTRATOR_LABELS[project.orchestrator] ?? project.orchestrator}
          </Badge>
        )}
        {project.targetDate && (
          <span className="text-sm text-muted">
            Target:{" "}
            {new Date(project.targetDate).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </span>
        )}
      </div>

      {/* Status update */}
      <Card className="mb-8">
        <h2 className="text-base font-semibold text-foreground mb-4">
          Update status
        </h2>
        <ProjectStatusForm
          projectId={project.id}
          currentStatus={project.status as "active" | "paused" | "complete"}
        />
      </Card>

      {/* Milestones */}
      <Card>
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-base font-semibold text-foreground">
            Milestones
          </h2>
          <span className="text-sm text-muted">
            {done} / {total} done
          </span>
        </div>

        {/* Progress bar */}
        {total > 0 && (
          <div className="h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden mb-5">
            <div
              className="h-full rounded-full bg-accent transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        )}

        {/* Milestone list */}
        {projectMilestones.length === 0 ? (
          <p className="text-sm text-muted py-4 text-center">
            No milestones yet. Add one below.
          </p>
        ) : (
          <div className="divide-y divide-border mb-6">
            {projectMilestones.map((milestone) => (
              <MilestoneToggle
                key={milestone.id}
                id={milestone.id}
                initialStatus={
                  milestone.status as "pending" | "in-progress" | "done"
                }
                title={milestone.title}
              />
            ))}
          </div>
        )}

        {/* Add milestone */}
        <div className={projectMilestones.length > 0 ? "" : "mt-4"}>
          <p className="text-sm font-medium text-foreground mb-3">
            Add milestone
          </p>
          <AddMilestoneForm projectId={project.id} />
        </div>
      </Card>
    </div>
  )
}
