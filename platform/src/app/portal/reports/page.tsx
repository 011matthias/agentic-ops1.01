import PageHeader from "@/components/ui/PageHeader"
import EmptyState from "@/components/ui/EmptyState"

export const metadata = { title: "Reports" }

export default function ReportsPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader
        title="Reports"
        subtitle="Usage summaries, performance metrics, and monthly digests."
      />
      <EmptyState
        title="No reports yet"
        description="Monthly performance summaries, automation metrics, and usage digests will appear here once your automations are running."
      />
    </div>
  )
}
