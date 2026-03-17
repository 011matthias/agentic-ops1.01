"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

interface PromoteDialogProps {
  userId: string
  userName: string | null
}

export default function PromoteDialog({ userId, userName }: PromoteDialogProps) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [companyName, setCompanyName] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handlePromote(e: React.FormEvent) {
    e.preventDefault()
    if (!companyName.trim()) return

    setLoading(true)
    setError("")

    const res = await fetch(`/api/admin/users/${userId}/role`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: "client", companyName: companyName.trim() }),
    })

    setLoading(false)

    if (res.ok) {
      setOpen(false)
      setCompanyName("")
      router.refresh()
    } else {
      const data = await res.json()
      setError(data.error ?? "Failed to promote user")
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
      >
        Promote to Client
      </button>
    )
  }

  return (
    <form onSubmit={handlePromote} className="flex items-center gap-2">
      <input
        type="text"
        value={companyName}
        onChange={(e) => setCompanyName(e.target.value)}
        placeholder="Company name"
        required
        autoFocus
        className="px-2 py-1 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      <button
        type="submit"
        disabled={loading || !companyName.trim()}
        className="px-2.5 py-1 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {loading ? "..." : "Confirm"}
      </button>
      <button
        type="button"
        onClick={() => { setOpen(false); setError("") }}
        className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
      >
        Cancel
      </button>
      {error && <span className="text-xs text-red-500">{error}</span>}
    </form>
  )
}
