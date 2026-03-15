import PageHeader from "@/components/ui/PageHeader"
import EmptyState from "@/components/ui/EmptyState"

export const metadata = { title: "Automations" }

export default function AutomationsPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader
        title="Automations"
        subtitle="Monitor your active automations, run history, and status."
      />
      <EmptyState
        title="No automations yet"
        description="Your automation runs, statuses, and history will appear here once your workflows are live."
      />
    </div>
  )
}
