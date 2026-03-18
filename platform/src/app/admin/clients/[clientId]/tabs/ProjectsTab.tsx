import Link from "next/link"
import Badge from "@/components/ui/Badge"
import Card from "@/components/ui/Card"
import CreateProjectForm from "../CreateProjectForm"

interface ProjectRecord {
  id: string
  name: string
  description: string | null
  status: string
  orchestrator: string | null
  targetDate: Date | null
}

interface ProjectsTabProps {
  projects: ProjectRecord[]
  clientId: string
}

export default function ProjectsTab({ projects: projectList, clientId }: ProjectsTabProps) {
  return (
    <div className="flex flex-col gap-8">
      {/* Project list */}
      <div>
        <h2 className="text-base font-semibold text-foreground mb-4">
          All projects{" "}
          <span className="text-muted font-normal text-sm">({projectList.length})</span>
        </h2>

        {projectList.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center rounded-2xl border border-dashed border-border p-10">
            <p className="text-sm text-muted">No projects yet. Create one below.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {projectList.map((project) => (
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

      {/* Create project form */}
      <Card>
        <h2 className="text-base font-semibold text-foreground mb-4">Create project</h2>
        <CreateProjectForm clientId={clientId} />
      </Card>
    </div>
  )
}
