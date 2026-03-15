"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Button from "@/components/ui/Button"

type ProjectStatus = "active" | "paused" | "complete"

interface Props {
  projectId: string
  currentStatus: ProjectStatus
}

export default function ProjectStatusForm({ projectId, currentStatus }: Props) {
  const router = useRouter()
  const [status, setStatus] = useState<ProjectStatus>(currentStatus)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setSaved(false)

    try {
      const res = await fetch(`/api/admin/projects/${projectId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error ?? "Failed to update project")
      }

      setSaved(true)
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="project-status" className="text-sm font-medium text-foreground">
          Status
        </label>
        <select
          id="project-status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as ProjectStatus)
            setSaved(false)
          }}
          className="px-4 py-2.5 rounded-xl border border-border bg-white dark:bg-gray-800 text-foreground focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition-colors text-sm"
        >
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="complete">Complete</option>
        </select>
      </div>
      <Button type="submit" disabled={submitting || status === currentStatus}>
        {submitting ? "Saving..." : "Save"}
      </Button>
      {saved && (
        <span className="text-sm text-green-600 dark:text-green-400">Saved</span>
      )}
      {error && (
        <span className="text-sm text-red-600 dark:text-red-400">{error}</span>
      )}
    </form>
  )
}
