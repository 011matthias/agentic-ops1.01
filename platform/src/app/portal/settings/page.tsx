import PageHeader from "@/components/ui/PageHeader"
import EmptyState from "@/components/ui/EmptyState"

export const metadata = { title: "Settings" }

export default function SettingsPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader
        title="Settings"
        subtitle="Manage your account, notification preferences, and integrations."
      />
      <EmptyState
        title="Settings coming soon"
        description="Account settings, notification preferences, and integration management will be available here."
      />
    </div>
  )
}
