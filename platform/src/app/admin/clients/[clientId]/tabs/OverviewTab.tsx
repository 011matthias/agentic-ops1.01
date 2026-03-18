import Link from "next/link"
import StatCard from "@/components/admin/StatCard"
import Badge from "@/components/ui/Badge"
import Card from "@/components/ui/Card"

interface ClientRecord {
  id: string
  userId: string
  companyName: string
  status: "active" | "inactive" | null
  createdAt: Date | null
}

interface ProjectRecord {
  id: string
  name: string
  description: string | null
  status: string
  orchestrator: string | null
  targetDate: Date | null
}

interface OverviewTabProps {
  client: ClientRecord
  counts: {
    projects: number
    unreadMessages: number
    files: number
    purchases: number
  }
  recentProjects: ProjectRecord[]
}

export default function OverviewTab({ client, counts, recentProjects }: OverviewTabProps) {
  return (
    <div className="flex flex-col gap-8">
      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Projects" value={counts.projects} />
        <StatCard
          label="Unread messages"
          value={counts.unreadMessages}
          sublabel={counts.unreadMessages > 0 ? "needs attention" : undefined}
        />
        <StatCard label="Files" value={counts.files} />
        <StatCard label="Purchases" value={counts.purchases} />
      </div>

      {/* Client details */}
      <Card>
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

      {/* Recent projects */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-foreground">
            Recent projects
          </h2>
          {counts.projects > 3 && (
            <Link
              href="?tab=projects"
              className="text-sm text-accent hover:underline"
            >
              View all ({counts.projects}) →
            </Link>
          )}
        </div>

        {recentProjects.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center rounded-2xl border border-dashed border-border p-10">
            <p className="text-sm text-muted">No projects yet.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {recentProjects.map((project) => (
              <Link key={project.id} href={`/admin/projects/${project.id}`}>
                <Card className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
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
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
