import PageHeader from "@/components/ui/PageHeader"
import EmptyState from "@/components/ui/EmptyState"

export const metadata = { title: "Messages" }

export default function MessagesPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader
        title="Messages"
        subtitle="Communicate with the UnpauseAI team about your project."
      />
      <EmptyState
        title="No messages yet"
        description="Your conversations with the UnpauseAI team will appear here. Replies, project updates, and support threads all in one place."
      />
    </div>
  )
}
