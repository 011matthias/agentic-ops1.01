"use client"

import { useState } from "react"
import Badge from "@/components/ui/Badge"

type MilestoneStatus = "pending" | "in-progress" | "done"

interface Props {
  id: string
  initialStatus: MilestoneStatus
  title: string
}

export default function MilestoneToggle({ id, initialStatus, title }: Props) {
  const [status, setStatus] = useState<MilestoneStatus>(initialStatus)
  const [loading, setLoading] = useState(false)

  async function handleToggle() {
    const nextStatus: MilestoneStatus = status === "done" ? "pending" : "done"
    setLoading(true)
    try {
      const res = await fetch(`/api/admin/milestones/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      })
      if (!res.ok) {
        throw new Error("Failed to update milestone")
      }
      setStatus(nextStatus)
    } catch {
      // revert on error — status stays unchanged because we haven't set it yet
    } finally {
      setLoading(false)
    }
  }

  const badgeVariant =
    status === "done"
      ? "success"
      : status === "in-progress"
        ? "warning"
        : "default"

  return (
    <div className="flex items-center gap-3 py-2.5">
      <input
        type="checkbox"
        checked={status === "done"}
        onChange={handleToggle}
        disabled={loading}
        className="h-4 w-4 rounded border-border text-accent focus:ring-accent cursor-pointer disabled:cursor-not-allowed"
        aria-label={`Mark "${title}" as ${status === "done" ? "pending" : "done"}`}
      />
      <span
        className={`flex-1 text-sm ${status === "done" ? "line-through text-muted" : "text-foreground"}`}
      >
        {title}
      </span>
      <Badge variant={badgeVariant}>{status}</Badge>
    </div>
  )
}
