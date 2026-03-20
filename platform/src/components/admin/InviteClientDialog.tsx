"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

export default function InviteClientDialog() {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState("")
  const [companyName, setCompanyName] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [sent, setSent] = useState(false)

  function reset() {
    setEmail("")
    setCompanyName("")
    setError("")
    setSent(false)
    setOpen(false)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim() || !companyName.trim()) return

    setLoading(true)
    setError("")

    const res = await fetch("/api/admin/invite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), companyName: companyName.trim() }),
    })

    setLoading(false)

    if (res.ok) {
      setSent(true)
      router.refresh()
    } else {
      const data = await res.json()
      setError(data.error ?? "Failed to send invite")
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
      >
        Invite Client
      </button>
    )
  }

  if (sent) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-green-600 dark:text-green-400 font-medium">
          Invite sent to {email}
        </span>
        <button
          onClick={reset}
          className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          Done
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 flex-wrap">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Client email"
        required
        autoFocus
        className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      <input
        type="text"
        value={companyName}
        onChange={(e) => setCompanyName(e.target.value)}
        placeholder="Company name"
        required
        className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      <button
        type="submit"
        disabled={loading || !email.trim() || !companyName.trim()}
        className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {loading ? "Sending..." : "Send Invite"}
      </button>
      <button
        type="button"
        onClick={reset}
        className="px-2 py-1.5 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
      >
        Cancel
      </button>
      {error && <span className="text-xs text-red-500">{error}</span>}
    </form>
  )
}
