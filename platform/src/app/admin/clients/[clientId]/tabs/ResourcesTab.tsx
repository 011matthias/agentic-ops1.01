"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import EmptyState from "@/components/ui/EmptyState"
import Card from "@/components/ui/Card"
import Button from "@/components/ui/Button"

const RESOURCE_TYPES = ["html_page", "video", "link", "file"] as const
const RESOURCE_CATEGORIES = ["documentation", "setup", "guides", "videos"] as const

const TYPE_LABELS: Record<string, string> = {
  html_page: "HTML Page",
  video: "Video",
  link: "Link",
  file: "File",
}

const CATEGORY_LABELS: Record<string, string> = {
  documentation: "Documentation",
  setup: "Setup & Config",
  guides: "Guides",
  videos: "Videos",
}

const TYPE_ICONS: Record<string, string> = {
  html_page: "📄",
  video: "▶",
  link: "🔗",
  file: "📁",
}

interface ResourceRecord {
  id: string
  title: string
  description: string | null
  type: string
  url: string
  category: string
  sortOrder: number
  published: boolean
  createdAt: string
}

interface ResourcesTabProps {
  resources: ResourceRecord[]
  clientId: string
}

export default function ResourcesTab({ resources: resourceList, clientId }: ResourcesTabProps) {
  const router = useRouter()
  const [deleting, setDeleting] = useState<string | null>(null)
  const [toggling, setToggling] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState({
    title: "",
    description: "",
    type: "html_page" as string,
    url: "",
    category: "documentation" as string,
    sortOrder: "0",
    published: false,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch("/api/admin/resources", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          clientId,
          title: form.title,
          description: form.description || null,
          type: form.type,
          url: form.url,
          category: form.category,
          sortOrder: parseInt(form.sortOrder) || 0,
          published: form.published,
        }),
      })
      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.error ?? "Failed to add resource")
      }
      setForm({ title: "", description: "", type: "html_page", url: "", category: "documentation", sortOrder: "0", published: false })
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add resource")
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this resource? This cannot be undone.")) return
    setDeleting(id)
    try {
      const res = await fetch(`/api/admin/resources/${id}`, { method: "DELETE" })
      if (!res.ok) throw new Error("Delete failed")
      router.refresh()
    } catch {
      alert("Failed to delete resource")
    } finally {
      setDeleting(null)
    }
  }

  const handleTogglePublished = async (id: string, current: boolean) => {
    setToggling(id)
    try {
      const res = await fetch(`/api/admin/resources/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ published: !current }),
      })
      if (!res.ok) throw new Error("Update failed")
      router.refresh()
    } catch {
      alert("Failed to update resource")
    } finally {
      setToggling(null)
    }
  }

  // Group by category
  const groups = new Map<string, ResourceRecord[]>()
  for (const resource of resourceList) {
    if (!groups.has(resource.category)) groups.set(resource.category, [])
    groups.get(resource.category)!.push(resource)
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Add resource form */}
      <Card>
        <h2 className="text-base font-semibold text-foreground mb-4">Add resource</h2>
        <p className="text-xs text-muted mb-4">
          Admin-curated resources only. For client file uploads, use the Files tab.
        </p>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted mb-1">Title *</label>
              <input
                type="text"
                required
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="System Overview"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-white dark:bg-gray-800 text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted mb-1">Type *</label>
              <select
                required
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-white dark:bg-gray-800 text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
              >
                {RESOURCE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1">
              URL *
              {form.type === "video" && (
                <span className="ml-2 font-normal text-muted/70">
                  For Loom: use https://www.loom.com/embed/&#123;id&#125;
                </span>
              )}
            </label>
            <input
              type="text"
              required
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
              placeholder={
                form.type === "video"
                  ? "https://www.loom.com/embed/abc123"
                  : form.type === "html_page"
                  ? "/client-docs/meji-media/meji-media-system-overview.html"
                  : "https://..."
              }
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-white dark:bg-gray-800 text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted mb-1">Category *</label>
              <select
                required
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-white dark:bg-gray-800 text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
              >
                {RESOURCE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {CATEGORY_LABELS[c]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-muted mb-1">Sort order</label>
              <input
                type="number"
                value={form.sortOrder}
                onChange={(e) => setForm({ ...form, sortOrder: e.target.value })}
                min="0"
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-white dark:bg-gray-800 text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
              />
            </div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.published}
                  onChange={(e) => setForm({ ...form, published: e.target.checked })}
                  className="rounded"
                />
                Publish immediately
              </label>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1">Description (optional)</label>
            <input
              type="text"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Brief description shown to the client"
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-white dark:bg-gray-800 text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50"
            />
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <Button type="submit" disabled={submitting} size="sm">
            {submitting ? "Adding..." : "Add resource"}
          </Button>
        </form>
      </Card>

      {/* Resource list */}
      {resourceList.length === 0 ? (
        <EmptyState
          title="No resources yet"
          description="Add documentation, guides, and links using the form above."
        />
      ) : (
        <div className="space-y-8">
          {Array.from(groups.entries()).map(([category, categoryResources]) => (
            <div key={category}>
              <h2 className="text-sm font-semibold text-muted uppercase tracking-wide mb-3">
                {CATEGORY_LABELS[category] ?? category}
              </h2>
              <div className="rounded-2xl border border-border bg-white dark:bg-gray-900 overflow-hidden">
                <ul className="divide-y divide-border">
                  {categoryResources.map((resource) => (
                    <li
                      key={resource.id}
                      className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 text-lg shrink-0">
                        {TYPE_ICONS[resource.type] ?? "📄"}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium text-foreground truncate">{resource.title}</p>
                          {!resource.published && (
                            <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 shrink-0">
                              Draft
                            </span>
                          )}
                        </div>
                        {resource.description && (
                          <p className="text-xs text-muted mt-0.5 truncate">{resource.description}</p>
                        )}
                        <p className="text-xs text-muted/60 mt-0.5 truncate">{resource.url}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleTogglePublished(resource.id, resource.published)}
                          disabled={toggling === resource.id}
                          className="text-xs"
                        >
                          {toggling === resource.id
                            ? "..."
                            : resource.published
                            ? "Unpublish"
                            : "Publish"}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(resource.id)}
                          disabled={deleting === resource.id}
                          className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                        >
                          {deleting === resource.id ? "..." : "Delete"}
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
