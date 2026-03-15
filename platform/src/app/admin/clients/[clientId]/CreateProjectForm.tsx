"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Button from "@/components/ui/Button"

interface Props {
  clientId: string
}

export default function CreateProjectForm({ clientId }: Props) {
  const router = useRouter()
  const [name, setName] = useState("")
  const [orchestrator, setOrchestrator] = useState<string>("")
  const [targetDate, setTargetDate] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return

    setSubmitting(true)
    setError(null)

    try {
      const res = await fetch("/api/admin/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          clientId,
          name: name.trim(),
          orchestrator: orchestrator || null,
          targetDate: targetDate || null,
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error ?? "Failed to create project")
      }

      // Reset form and refresh server data
      setName("")
      setOrchestrator("")
      setTargetDate("")
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      <div className="flex flex-col gap-1.5">
        <label htmlFor="project-name" className="text-sm font-medium text-foreground">
          Name <span className="text-red-500">*</span>
        </label>
        <input
          id="project-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. CRM Automation v2"
          required
          className="w-full px-4 py-2.5 rounded-xl border border-border bg-white dark:bg-gray-800 text-foreground placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition-colors text-sm"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="project-orchestrator" className="text-sm font-medium text-foreground">
          Orchestrator
        </label>
        <select
          id="project-orchestrator"
          value={orchestrator}
          onChange={(e) => setOrchestrator(e.target.value)}
          className="w-full px-4 py-2.5 rounded-xl border border-border bg-white dark:bg-gray-800 text-foreground focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition-colors text-sm"
        >
          <option value="">Select orchestrator (optional)</option>
          <option value="make">Make.com</option>
          <option value="n8n">n8n</option>
          <option value="trigger-dev">Trigger.dev</option>
          <option value="fastapi">FastAPI</option>
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="project-target-date" className="text-sm font-medium text-foreground">
          Target date
        </label>
        <input
          id="project-target-date"
          type="date"
          value={targetDate}
          onChange={(e) => setTargetDate(e.target.value)}
          className="w-full px-4 py-2.5 rounded-xl border border-border bg-white dark:bg-gray-800 text-foreground focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition-colors text-sm"
        />
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={submitting || !name.trim()}>
          {submitting ? "Creating..." : "Create project"}
        </Button>
      </div>
    </form>
  )
}
