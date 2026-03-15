"use client"

import { useState, useRef, useEffect } from "react"
import Button from "@/components/ui/Button"

type MessageRow = {
  id: string
  authorRole: "admin" | "client"
  body: string
  createdAt: Date | string
}

interface MessageThreadProps {
  initialMessages: MessageRow[]
  /** Override the POST endpoint (default: /api/portal/messages) */
  apiEndpoint?: string
  /** clientId to include in the POST body (used by admin endpoint) */
  clientId?: string
}

function formatRelativeTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - new Date(date).getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffSec < 60) return "just now"
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHour < 24) return `${diffHour}h ago`
  if (diffDay === 1) return "yesterday"
  if (diffDay < 7) return `${diffDay}d ago`

  return new Date(date).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  })
}

function getDateLabel(date: Date): string {
  const now = new Date()
  const d = new Date(date)
  const todayStr = now.toDateString()
  const yesterdayDate = new Date(now)
  yesterdayDate.setDate(now.getDate() - 1)

  if (d.toDateString() === todayStr) return "Today"
  if (d.toDateString() === yesterdayDate.toDateString()) return "Yesterday"

  return d.toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  })
}

function groupByDate(
  messages: MessageRow[]
): Array<{ label: string; messages: MessageRow[] }> {
  const groups: Map<string, MessageRow[]> = new Map()

  for (const msg of messages) {
    const label = getDateLabel(new Date(msg.createdAt))
    if (!groups.has(label)) groups.set(label, [])
    groups.get(label)!.push(msg)
  }

  return Array.from(groups.entries()).map(([label, messages]) => ({
    label,
    messages,
  }))
}

export default function MessageThread({
  initialMessages,
  apiEndpoint = "/api/portal/messages",
  clientId,
}: MessageThreadProps) {
  const [messages, setMessages] = useState<MessageRow[]>(initialMessages)
  const [body, setBody] = useState("")
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function handleSend() {
    if (!body.trim()) return
    setSending(true)
    setError(null)

    try {
      const payload: Record<string, string> = { body: body.trim() }
      if (clientId) payload.clientId = clientId

      const res = await fetch(apiEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error ?? "Failed to send message")
      }

      const newMessage = await res.json()
      // Normalize: dates come back as strings from JSON
      setMessages((prev) => [
        ...prev,
        { ...newMessage, createdAt: new Date(newMessage.createdAt) },
      ])
      setBody("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong")
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  const groups = groupByDate(messages)

  return (
    <div className="flex flex-col gap-6">
      {/* Message list */}
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center rounded-2xl border border-dashed border-border p-12">
          <h3 className="text-lg font-semibold text-foreground mb-2">
            No messages yet
          </h3>
          <p className="text-sm text-muted max-w-sm">
            Your team will reach out here. Use the form below to send a message.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {groups.map(({ label, messages: groupMessages }) => (
            <div key={label}>
              <div className="flex items-center gap-3 mb-4">
                <div className="flex-1 h-px bg-border" />
                <span className="text-xs text-muted font-medium px-2">
                  {label}
                </span>
                <div className="flex-1 h-px bg-border" />
              </div>

              <div className="flex flex-col gap-3">
                {groupMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-3 ${
                      msg.authorRole === "client" ? "flex-row-reverse" : ""
                    }`}
                  >
                    {/* Author dot */}
                    <div className="mt-1 flex-shrink-0">
                      <div
                        className={`w-2.5 h-2.5 rounded-full mt-1.5 ${
                          msg.authorRole === "admin"
                            ? "bg-blue-500"
                            : "bg-gray-400"
                        }`}
                      />
                    </div>

                    {/* Bubble */}
                    <div
                      className={`max-w-[75%] ${
                        msg.authorRole === "client" ? "items-end" : "items-start"
                      } flex flex-col gap-1`}
                    >
                      <div
                        className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                          msg.authorRole === "client"
                            ? "bg-accent text-white rounded-tr-sm"
                            : "bg-gray-100 dark:bg-gray-800 text-foreground rounded-tl-sm"
                        }`}
                      >
                        {msg.body}
                      </div>
                      <span className="text-xs text-muted px-1">
                        {msg.authorRole === "admin" ? "UnpauseAI" : "You"} ·{" "}
                        {formatRelativeTime(new Date(msg.createdAt))}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Reply form */}
      <div className="border-t border-border pt-6">
        <div className="flex flex-col gap-3">
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Write a message... (Ctrl+Enter to send)"
            rows={3}
            className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-foreground placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition-colors resize-vertical text-sm"
          />
          <div className="flex justify-end">
            <Button
              onClick={handleSend}
              disabled={sending || !body.trim()}
              size="md"
            >
              {sending ? "Sending..." : "Send message"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
