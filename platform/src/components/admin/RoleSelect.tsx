"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

interface RoleSelectProps {
  userId: string
  currentRole: string
  isSelf: boolean
}

export default function RoleSelect({ userId, currentRole, isSelf }: RoleSelectProps) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleChange(newRole: string) {
    if (newRole === currentRole) return

    setLoading(true)
    setError("")

    const res = await fetch(`/api/admin/users/${userId}/role`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: newRole }),
    })

    setLoading(false)

    if (res.ok) {
      router.refresh()
    } else {
      const data = await res.json()
      setError(data.error ?? "Failed to update role")
    }
  }

  // Admin can't change their own role; prospects need the promote flow for client
  if (isSelf) {
    return <span className="text-xs text-gray-500">(you)</span>
  }

  return (
    <div className="flex items-center gap-2">
      <select
        value={currentRole}
        onChange={(e) => handleChange(e.target.value)}
        disabled={loading}
        className="text-xs px-2 py-1 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white disabled:opacity-50"
      >
        <option value="prospect">Prospect</option>
        <option value="client">Client</option>
        <option value="admin">Admin</option>
      </select>
      {loading && <span className="text-xs text-gray-400">Saving...</span>}
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  )
}
