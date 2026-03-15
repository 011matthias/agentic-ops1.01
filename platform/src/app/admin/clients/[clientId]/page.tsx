import { redirect } from "next/navigation"
import { eq } from "drizzle-orm"
import { db } from "@/lib/db"
import { clients, projects } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import Badge from "@/components/ui/Badge"
import Card from "@/components/ui/Card"
import CreateProjectForm from "./CreateProjectForm"
import Link from "next/link"

export const metadata = { title: "Client Detail — Admin" }

interface Props {
  params: Promise<{ clientId: string }>
}

export default async function AdminClientDetailPage({ params }: Props) {
  const { clientId } = await params

  const client = await db.query.clients.findFirst({
    where: eq(clients.id, clientId),
  })

  if (!client) {
    redirect("/admin/clients")
  }

  const projectList = await db.query.projects.findMany({
    where: eq(projects.clientId, clientId),
    orderBy: (p, { desc }) => [desc(p.createdAt)],
  })

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <div className="mb-8">
        <Link
          href="/admin/clients"
          className="text-sm text-muted hover:text-foreground transition-colors mb-4 inline-block"
        >
          ← Back to clients
        </Link>
        <PageHeader title={client.companyName} />
      </div>

      {/* Client details */}
      <Card className="mb-8">
        <h2 className="text-base font-semibold text-foreground mb-4">Details</h2>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-muted mb-0.5">User ID</dt>
            <dd className="text-foreground font-mono text-xs break-all">{client.userId}</dd>
          </div>
          <div>
            <dt className="text-muted mb-0.5">Status</dt>
            <dd>
              <Badge variant={client.status === "active" ? "success" : "warning"}>
                {client.status ?? "active"}
              </Badge>
            </dd>
          </div>
          <div>
            <dt className="text-muted mb-0.5">Client ID</dt>
            <dd className="text-foreground font-mono text-xs break-all">{client.id}</dd>
          </div>
          <div>
            <dt className="text-muted mb-0.5">Created</dt>
            <dd className="text-foreground">
              {client.createdAt
                ? new Date(client.createdAt).toLocaleDateString("en-GB", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })
                : "—"}
            </dd>
          </div>
        </dl>
      </Card>

      {/* Projects */}
      <div className="mb-8">
        <h2 className="text-base font-semibold text-foreground mb-4">
          Projects{" "}
          <span className="text-muted font-normal text-sm">({projectList.length})</span>
        </h2>

        {projectList.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center rounded-2xl border border-dashed border-border p-10">
            <p className="text-sm text-muted">No projects yet. Create one below.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {projectList.map((project) => (
              <Card key={project.id} className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-foreground">{project.name}</p>
                    {project.description && (
                      <p className="text-sm text-muted mt-0.5">{project.description}</p>
                    )}
                    <div className="flex items-center gap-2 mt-2">
                      <Badge
                        variant={
                          project.status === "active"
                            ? "success"
                            : project.status === "paused"
                            ? "warning"
                            : "default"
                        }
                      >
                        {project.status}
                      </Badge>
                      {project.orchestrator && (
                        <Badge variant="default">{project.orchestrator}</Badge>
                      )}
                    </div>
                  </div>
                  {project.targetDate && (
                    <div className="text-right shrink-0">
                      <p className="text-xs text-muted">Target</p>
                      <p className="text-sm text-foreground">
                        {new Date(project.targetDate).toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </p>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create project form */}
      <Card>
        <h2 className="text-base font-semibold text-foreground mb-4">Create project</h2>
        <CreateProjectForm clientId={clientId} />
      </Card>
    </div>
  )
}
