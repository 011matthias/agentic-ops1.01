import { redirect } from "next/navigation"
import { and, asc, eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clientResources, clients } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import EmptyState from "@/components/ui/EmptyState"

export const metadata = { title: "Resources" }

type ResourceType = "html_page" | "video" | "link" | "file"
type ResourceCategory = "documentation" | "setup" | "guides" | "videos"

const TYPE_ICONS: Record<ResourceType, string> = {
  html_page: "📄",
  video: "▶",
  link: "🔗",
  file: "📁",
}

const CATEGORY_LABELS: Record<ResourceCategory, string> = {
  documentation: "Documentation",
  setup: "Setup & Config",
  guides: "Guides",
  videos: "Videos",
}

type ResourceRow = typeof clientResources.$inferSelect

export default async function ResourcesPage() {
  const session = await auth()
  if (!session?.user?.id) redirect("/login")

  const client = await db.query.clients.findFirst({
    where: eq(clients.userId, session.user.id),
  })

  const resourceList: ResourceRow[] = client
    ? await db.query.clientResources.findMany({
        where: and(
          eq(clientResources.clientId, client.id),
          eq(clientResources.published, true)
        ),
        orderBy: [asc(clientResources.category), asc(clientResources.sortOrder)],
      })
    : []

  // Group by category
  const groups = new Map<ResourceCategory, ResourceRow[]>()
  for (const resource of resourceList) {
    const cat = resource.category as ResourceCategory
    if (!groups.has(cat)) groups.set(cat, [])
    groups.get(cat)!.push(resource)
  }

  // Sort categories in a logical order
  const categoryOrder: ResourceCategory[] = ["documentation", "guides", "setup", "videos"]
  const sortedGroups = categoryOrder
    .filter((cat) => groups.has(cat))
    .map((cat) => [cat, groups.get(cat)!] as [ResourceCategory, ResourceRow[]])

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader
        title="Resources"
        subtitle="Documentation, guides, and tools from your team."
      />

      {resourceList.length === 0 ? (
        <EmptyState
          title="No resources yet"
          description="Your team will add documentation and guides here."
        />
      ) : (
        <div className="space-y-10">
          {sortedGroups.map(([category, resources]) => (
            <div key={category}>
              <h2 className="text-sm font-semibold text-muted uppercase tracking-wide mb-4">
                {CATEGORY_LABELS[category]}
              </h2>

              {category === "videos" ? (
                // Video cards with embedded iframes
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {resources.map((resource) => (
                    <div
                      key={resource.id}
                      className="rounded-2xl border border-border bg-white dark:bg-gray-900 overflow-hidden"
                    >
                      <div className="aspect-video w-full">
                        <iframe
                          src={resource.url}
                          className="w-full h-full"
                          allowFullScreen
                          title={resource.title}
                        />
                      </div>
                      <div className="px-5 py-4">
                        <p className="text-sm font-medium text-foreground">{resource.title}</p>
                        {resource.description && (
                          <p className="text-xs text-muted mt-1">{resource.description}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                // List cards for html_page, link, file
                <div className="rounded-2xl border border-border bg-white dark:bg-gray-900 overflow-hidden">
                  <ul className="divide-y divide-border">
                    {resources.map((resource) => {
                      const type = resource.type as ResourceType
                      return (
                        <li
                          key={resource.id}
                          className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                        >
                          <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 text-lg shrink-0">
                            {TYPE_ICONS[type]}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground truncate">
                              {resource.title}
                            </p>
                            {resource.description && (
                              <p className="text-xs text-muted mt-0.5 truncate">
                                {resource.description}
                              </p>
                            )}
                          </div>
                          <a
                            href={resource.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="shrink-0 px-4 py-2 text-xs font-medium rounded-lg bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
                          >
                            {type === "file" ? "Download" : "Open"}
                          </a>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
