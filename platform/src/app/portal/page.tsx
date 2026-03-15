import { auth } from "@/lib/auth"
import StatCard from "@/components/portal/StatCard"
import PortalCard from "@/components/portal/PortalCard"

export default async function PortalPage() {
  const session = await auth()

  const firstName = session?.user?.name?.split(" ")[0] ?? "there"

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <div className="mb-10">
        <h1 className="text-3xl font-bold">Welcome back, {firstName}</h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Here&apos;s an overview of your automations and activity.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-12">
        <StatCard label="Active Automations" value="—" />
        <StatCard label="Runs This Month" value="—" />
        <StatCard label="Open Messages" value="—" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <PortalCard
          title="Automations"
          description="View and monitor your active automations, run history, and status."
          href="/portal/automations"
          icon="⚡"
          empty
        />
        <PortalCard
          title="Messages"
          description="Communicate with the UnpauseAI team about your project."
          href="/portal/messages"
          icon="💬"
          empty
        />
        <PortalCard
          title="Reports"
          description="Usage summaries, performance metrics, and monthly digests."
          href="/portal/reports"
          icon="📊"
          empty
        />
        <PortalCard
          title="Settings"
          description="Manage your account, notification preferences, and integrations."
          href="/portal/settings"
          icon="⚙️"
          empty
        />
      </div>
    </div>
  )
}
